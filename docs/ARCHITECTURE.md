# Architecture

How Overtake is put together, and why. This describes the system as built; the
product specification it implements is in `documentation/`.

---

## Shape

```
        fantasy.premierleague.com/api  (public, unauthenticated, read-only)
                        │
                        │  ≤2 req/s · ETag · backoff · circuit breaker
                        ▼
        ┌───────────────────────────────┐
        │  WORKER  (jobs table poller)  │
        │  ingest · projections ·       │
        │  simulation · profiling ·     │
        │  email · retention sweep      │
        └───────────────┬───────────────┘
                        │ upsert
        ┌───────────────▼───────────────┐
        │          POSTGRES             │
        │  normalised FPL state ·       │
        │  cached simulations ·         │
        │  league memory · identity     │
        └───────────────┬───────────────┘
                        │ read
        ┌───────────────▼───────────────┐          ┌──────────────┐
        │      API  (FastAPI)           │◀────────▶│  LLM (leaf)  │
        │  auth · entitlements · reads  │          └──────────────┘
        └───────────────┬───────────────┘
                        │  same-origin /api/v1 proxy
        ┌───────────────▼───────────────┐
        │      WEB  (Next.js 15)        │
        └───────────────────────────────┘
```

**Three principles hold this together.**

1. **Ingest, simulate and serve are separate.** The web app never calls the FPL
   API on a user request — always the cache. Anything expensive happens in the
   worker.
2. **Everything expensive is cached at the league × gameweek grain**, never per
   user. One simulation serves every member of a league, so cost scales with
   leagues rather than users, and it *improves* as the product grows.
3. **The LLM is a leaf node.** If it is down, the product still works.

---

## Why these choices

| Decision | Reason | What it costs |
|---|---|---|
| FastAPI + NumPy in one process | The simulation *is* NumPy. Keeping the API in the same language avoids a service boundary between the engine and the thing that serves it. | Two languages in the repo. |
| Postgres as the queue | One fewer moving part in a small system. `SELECT … FOR UPDATE SKIP LOCKED` makes multiple workers safe. | Will not scale past a few thousand jobs/hour. Redis when it backs up, not before. |
| Magic links, no passwords | Removes password storage, reset flows, credential stuffing and breach exposure entirely. Suits the audience. | Email deliverability becomes critical-path. |
| Opaque server-side sessions | Revocation matters more than statelessness at this scale. | One database read per request. |
| Dialect-portable models | The whole suite runs on SQLite with zero setup, while production is PostgreSQL with JSONB, CITEXT, INET and partial indexes. | Custom column types, and one drift test to keep them honest. |
| Season pass as a one-time payment | No surprise auto-charge for a young audience, and it avoids Stripe Billing's recurring fee. | Entitlement is a stored date rather than a subscription row. |

---

## Data flow: a league page

1. Visitor pastes a league ID. The web app server-renders `/l/{id}`.
2. `read_simulation` fetches the newest cached run for that league and returns
   it. If the run is older than 30 minutes it also enqueues a background
   refresh — but it serves the cached numbers first and never waits.
3. Only the **first ever** view of a league has nothing to serve. That one
   computes inline, because the product promises real odds within five seconds
   of pasting a league ID and a run takes about two.
4. The worker's `recompute_league` is the write path. It calls
   `run_and_cache_simulation`, which re-checks `SimulationInput.input_hash()` —
   a hash over squads, totals, chips, behavioural priors, projections, seed and
   model version — so unchanged inputs never re-simulate.

**Read and write are deliberately separate functions.** They were briefly the
same one, which meant every page view assembled a full simulation input —
loading every squad, every projection and every rival profile — just to compute
a cache key. That was 376 ms of work on a request that already had its answer.
The read path is now ~6 ms.

The freshness block is rendered, not just logged. Data is **never** silently
stale.

---

## The simulator

`api/overtake/engine/simulator.py`.

For each remaining gameweek:

1. Sample an `(n_sims × n_players)` matrix of gameweek scores.
2. Build a weight matrix `(n_players × n_managers)`: 1.0 per starting slot, an
   extra 1.0 on the captain.
3. One matrix multiply scores every manager at once.

**Sampling** is two-stage, because that is how the real thing works: a player
either features or does not (Bernoulli on `p_start`), and conditional on
featuring the score is right-skewed (Gamma matched to the conditional mean and
variance). A Normal would put mass below zero and understate hauls.

Three corrections that each changed the answer materially:

- **A shared per-club shock** each gameweek. Teammates rise and fall together —
  a clean sheet pays several defenders at once — and ignoring it put the
  gameweek standard deviation at 13 against a real ~19.
- **A per-player season-long quality multiplier**, drawn once per simulated
  season. Without it the simulator treats projections as known truth and becomes
  95% certain about things its own published error does not support.
- **Automatic substitutions.** A starter who blanks is not a zero; FPL brings a
  bench player on. Omitting this charged every squad twice for rotation risk.

**Squad convergence** models the fact that squads drift toward the league's own
template as everyone transfers. The rate is driven by each rival's observed
transfer volume and template overlap — this is where behavioural profiling
actually changes the odds rather than decorating the dossier.

**Candidate moves** are extra columns of the same weight matrix, scored against
the identical sampled points. That is what makes a half-percentage-point delta a
real difference rather than sampling noise.

---

## The anti-hallucination stack

`api/overtake/llm/validation.py`. In order:

1. **The model receives only computed values.** No raw API responses. If a
   number is not in the payload, it does not exist.
2. **Structured output**, validated against a Pydantic schema.
3. **Numeric grounding.** Every number in the prose must appear in the input
   payload within rounding tolerance.
4. **Named-entity check.** Every player and rival name must appear in the
   payload's entity list. This catches the classic failure of inventing a
   transfer target.
5. **Banned phrases.** No forward-looking certainty, and no gambling language —
   the latter is a product constraint, not a style note.
6. **Confidence is computed** from measured projection error and rotation risk,
   never self-reported. A model asked to rate its own confidence rates it high.

One failure triggers a retry. Two trigger the deterministic template, which
renders the same numbers with no prose and passes the same checks itself.

**Known limitation, recorded deliberately:** the grounding check verifies that a
number is *present* in the payload, not that it was used *correctly*. It is an
anti-fabrication guard; the fixed output contract is what constrains usage.

---

## Prompt injection

FPL team names are free text typed by strangers, and they reach both the page
and the prompt. They are:

- normalised (NFKC), stripped of control characters and bidirectional overrides,
  collapsed and truncated to 60 characters **at ingest**;
- wrapped in `<untrusted_data>` delimiters in every prompt, with each prompt
  instructing the model to treat delimited content as data only;
- rendered through React's escaping, under a CSP with no external script origins.

The LLM has no tools with side effects. The worst case for a successful
injection is prose that fails the grounding check and falls back to a template.

---

## Cost control

Two mechanisms, both enforced in code rather than by an alert.

- **Sharing.** Simulations are cached per league × gameweek, so the marginal
  cost of a new user in an existing league is zero.
- **A hard daily LLM spend cap**, checked *before* each call. When it is hit,
  generation degrades to the deterministic template and an error is logged. A
  runaway AI bill is the most plausible way this business loses money on a small
  budget, so the cap is not advisory.

Per-user metering (dossiers, Gaffer messages, scenarios, regenerations) is
separate, lives in `usage_counters`, and is enforced through the same
entitlement service as the plan gates.

---

## Failure behaviour

| Failure | What the user sees |
|---|---|
| FPL API down | The last cached snapshot with an amber banner and an exact timestamp |
| Simulation not yet run | The previous gameweek's odds, labelled, or a real progress narrative |
| LLM down or over budget | The deterministic template: same numbers, no prose |
| Grounding check fails twice | The deterministic template, and the failure is logged with the prompt version |
| Payment fails | Seven days of full access with a dismissible banner, then downgrade. Data is never deleted. |
| Subscription cancelled | "Pro until 14 May. Nothing changes until then." |

---

## Testing strategy

Everything runs offline. `tests/fpl_stub.py` is an `httpx` transport serving
anonymised responses recorded from the live API, reproducing its routes, its
404s and its ETag/304 behaviour.

The fixtures carry **real squads and real response shapes** with **fictional
manager identities** — the repository holds no third-party personal data, which
is the same rule the product applies to its own users.

Calibration tests deserve special mention: they assert that simulated scoring
lands in a realistic points-per-gameweek band and a realistic variance. Three
separate modelling bugs were caught by those and by nothing else, each of which
produced perfectly plausible-looking output.

---

## What would need to change at scale

Honest about the limits of these choices:

| At roughly | Problem | Fix |
|---|---|---|
| 2,000 tracked leagues | Job table polling becomes contention | Redis + a real queue |
| 10,000 leagues | Simulation CPU dominates | Dedicated sim workers, sharded by league |
| 50,000 users | `analytics_events` grows unhelpfully | Move the funnel to PostHog properly, keep only aggregates |
| Any real load | Rate limiting via database round-trip | Redis token buckets |
| Multi-region | Session reads cross regions | Read replicas, or accept the latency |

None of these are worth doing before the GO/NO-GO question is answered.

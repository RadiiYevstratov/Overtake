# AI system specification

## 1. Division of labour — what is AI and what is not

The single most important architectural decision in this product: **the LLM never
computes a number.** It reads numbers produced by a deterministic engine and
turns them into an argument.

| Layer | Technology | Responsibility | Deterministic? |
|---|---|---|---|
| L0 Ingest | Python + httpx | Pull and normalise FPL state | Yes |
| L1 Projection | Statistical model (see §2) | Expected points per player per gameweek, with variance | Yes (seeded) |
| L2 Simulation | Monte Carlo, NumPy | P(finish above rival X), gap distributions, move deltas | Yes (seeded) |
| L3 Rival profiling | Feature extraction + rules, LLM for labelling only | Behavioural priors per rival | Mostly |
| **L4 Narration** | **LLM** | **Turn L2 output into a named, specific argument** | No |
| **L5 Conversation** | **LLM + tools** | **Answer follow-ups against live state** | No |

If the LLM is ever asked "what are my odds", the architecture is wrong. It is
asked "here are the odds; explain what to do."

## 2. L1 — projection model (the input, not the product)

Overtake does **not** compete on projection accuracy; incumbents have Opta
licences and we do not. The projection layer must be adequate and honest.

**MVP approach.** For each player, expected points per gameweek from:

- minutes probability — from `element_summary` recent starts + FPL's own
  `chance_of_playing_next_round`
- per-90 attacking returns over a decayed window (last 6 / season / prior season,
  exponentially weighted)
- fixture adjustment from the official Fixture Difficulty Rating and each team's
  goals-for/against rate
- set-piece status from the public `team/set-piece-notes/` endpoint
- defensive-contribution points (2025/26 onward) from recent DC rates
- bonus-point expectation from historical BPS rate per 90

Output per player per gameweek: `mu` (expected points) and `sigma` (standard
deviation), plus an explicit `p_start`.

**Honesty requirement.** The projections page must display measured backtest error
(MAE per player-gameweek) and say plainly that projections are the weakest part of
the stack. Overselling accuracy is how this product loses trust in week three.

**Do not** train a model on scraped Understat/FBref data at MVP stage. Public
endpoints only.

## 3. L2 — the Monte Carlo simulator (the actual differentiator)

For a league of *n* managers over *k* remaining gameweeks:

```
for sim in 1..N (N = 20,000):
    for gw in 1..k:
        sample each player's points ~ f(mu, sigma, p_start)
        for each manager m:
            apply their squad, captain, bench rules, chip state
            apply behavioural prior: will they transfer? take a hit?
            accumulate points
    record final totals
=> P(user finishes above manager m) for every m
=> distribution of final gap
=> for a candidate move: rerun with the move applied, take the delta
```

**Key outputs**
- `p_above[rival_id]` — the headline number
- `gap_distribution` — 10th/50th/90th percentile final gap
- `move_delta` — Δ P(above rival) for each candidate transfer/captain choice
- `variance_recommendation` — whether the user should be seeking or suppressing
  variance against this specific rival (behind → seek, ahead → suppress)

**Cost control.** This is CPU, not tokens. Simulation runs **once per league per
gameweek** and is cached and shared across every member of that league, so cost
scales with *leagues*, not with *users*. A 20-manager league over 20 remaining
gameweeks at N=20,000 is roughly 8M player-gameweek samples — sub-second in
vectorised NumPy. Candidate-move deltas use common random numbers (the same seed
across scenarios) so differences are stable and far cheaper than independent runs.

**Determinism.** Every simulation stores its seed and input snapshot hash. The
same inputs must always produce the same output — otherwise users will notice
their odds "flickering" and lose trust immediately.

## 4. L3 — rival behavioural profiling

Extracted from each rival's public transfer and picks history:

| Feature | Computed from | Used as |
|---|---|---|
| `hit_rate` | −4 hits taken per gameweek | probability of extra transfers in sim |
| `template_score` | overlap with global top-100 ownership | how likely to converge on the field |
| `reactivity` | correlation between last GW's top scorers and this GW's transfers in | chase behaviour |
| `chip_timing` | historical gameweeks of chip usage | prior on remaining chip deployment |
| `bench_accuracy` | points left on bench per GW | noise term |
| `activity` | gameweeks with zero transfers | probability of going inactive |

The LLM's only role here is naming the archetype in human language
("the hit-taker", "the template loyalist", "the set-and-forget"). It must never
invent a feature that was not computed. Archetypes are chosen from a **fixed
enum**, not generated freely.

## 5. L4/L5 — LLM layer

### Model selection

Model names and prices change constantly, so this spec fixes **tiers**, not names,
and the exact model is a config value re-verified at build time.

| Job | Tier | Why |
|---|---|---|
| Deadline Brief narration | Small-to-mid reasoning model (~$0.30–2.00 / 1M in) | Structured input, structured output, moderate reasoning |
| Ask-the-Gaffer | Same tier, streaming | Latency matters more than depth |
| Rival archetype labelling | Cheapest available tier | Classification into a fixed enum |
| Recap generation | Cheapest tier, batch API (50% discount) | Not latency sensitive; runs overnight |

Use one provider plus one fallback provider behind a thin interface. Never hard-code
a model name outside config.

### Prompt architecture

Four prompts, all versioned in the repo, all with golden-file tests.

```
prompts/
  deadline_brief.v3.md
  ask_gaffer.v2.md
  rival_archetype.v1.md
  gameweek_recap.v2.md
```

**Standard structure of every prompt:**

1. **Role** — "You are a fantasy football analyst writing for one specific
   manager. You never invent numbers."
2. **Hard constraints** — the list in §6 below.
3. **Context block** — a compact JSON payload from L2/L3 (never raw API dumps).
4. **Output contract** — a JSON schema; the model returns structured data, and the
   UI renders it. The model never writes HTML or free-form pages.

**Example context payload (Deadline Brief):**

```json
{
  "gameweek": 7,
  "deadline_utc": "2026-10-03T17:30:00Z",
  "manager": {"name": "Marcus", "rank_in_league": 6, "points": 312, "free_transfers": 2, "budget": 1.4,
              "chips_left": ["WC","TC","BB","FH"]},
  "league": {"name": "The Lads", "size": 9},
  "targets": [
    {"rival": "Dan", "points_ahead": 44, "p_above_now": 0.18, "p_above_if_move": 0.26,
     "their_differentials": [{"name":"Wirtz","ep_remaining":41.2}],
     "my_differentials": [{"name":"Mbeumo","ep_remaining":28.4}],
     "archetype": "template_loyalist"}
  ],
  "candidate_moves": [
    {"type":"captain","player":"Wirtz","delta_p_above":{"Dan":0.08},"cost":0,
     "downside_p10": -3.1}
  ],
  "projection_quality": {"mae_last_5_gw": 1.9}
}
```

**Output contract (Deadline Brief):**

```json
{
  "headline": "string, <=90 chars, must name a rival",
  "primary_move": {"summary": "string", "reasoning": "string, <=120 words",
                   "cited_numbers": ["p_above_if_move", "delta_p_above.Dan"]},
  "risk": "string, <=60 words, states the downside explicitly",
  "do_nothing_case": "string, <=60 words",
  "confidence": "high|medium|low"
}
```

`cited_numbers` is the anti-hallucination hook: every number in the prose must
correspond to a key present in the input payload, and a post-generation validator
checks it (see §6).

### Context and memory

Three memory scopes:

| Scope | Contents | Storage | Lifetime |
|---|---|---|---|
| **Simulation snapshot** | The L2 output for this league/gameweek | Postgres, `simulations` | Season |
| **League memory** | Rival archetypes, chip usage, notable events ("Dan wildcarded GW8 and gained 31") | Postgres, `league_memory` | Season, appended weekly |
| **Conversation** | Last 10 turns of Ask-the-Gaffer | Postgres, `conversations` | 30 days |

League memory is what makes month 6 better than month 1, and it is the reason a
competitor cannot clone the product by copying the UI. It is also why the product
gets *cheaper* over time: archetypes are recomputed weekly, not per request.

## 6. Hallucination prevention and validation

Non-negotiable, in order:

1. **The model receives only computed values.** No raw API responses, no
   unstructured stat dumps. If a number is not in the payload, it does not exist.
2. **Structured output only**, validated against a Pydantic schema. A parse
   failure triggers one retry at temperature 0, then a **deterministic template
   fallback** that renders the numbers without prose. The product degrades to
   plainness, never to fiction.
3. **Numeric grounding check.** A post-generation validator extracts every number
   from the prose with a regex and asserts each one appears in the input payload
   (within rounding tolerance). Any unmatched number = regenerate once, then fall
   back. Log every failure with the prompt version.
4. **Named-entity check.** Every player and rival name in the output must appear
   in the payload's entity list. This catches the classic failure of inventing a
   transfer target.
5. **No forward-looking certainty.** The prompt forbids "will score", "guaranteed",
   "nailed on". A banned-phrase list is checked post-generation.
6. **Explicit confidence.** Every brief carries `confidence`, driven by
   `projection_quality` and rotation risk — not by the model's self-assessment.
7. **Visible provenance.** The UI shows "simulated 20,000 seasons · data as of
   {timestamp} · projections MAE 1.9". Users trust a number they can audit.

## 7. Prompt-injection and abuse prevention

The attack surface is small but real, because rival data is user-controlled: **FPL
team names are free text set by other people.**

- Treat every team name, league name and manager name as untrusted. Wrap them in
  delimiters in the prompt, and instruct the model to treat delimited content as
  data. Strip control characters and truncate to 60 chars.
- Never let model output trigger an action. There are no tools with side effects
  in the LLM's reach; L5's tools are read-only lookups against our own database.
- Ask-the-Gaffer input: 500-char cap, rate limited (§8), and scoped by a system
  prompt that refuses off-topic requests rather than answering them.
- Log the full prompt and completion for 30 days for abuse review, then delete.

## 8. Rate limits and cost optimisation

| Control | Free | Pro |
|---|---|---|
| Rival dossiers | 1 per season | Unlimited (cached per league/GW) |
| Deadline Brief | — | 1 per gameweek, regenerable 3× |
| Ask-the-Gaffer | — | 20 messages/day, 200/month |
| Simulation runs | Shared cache only | Shared cache + 10 custom scenarios/GW |

Cost optimisations, in order of impact:

1. **Share the simulation across the league.** One run serves every member. This
   is the biggest single lever and it improves as the product grows.
2. **Cache the brief per (league, manager, gameweek, input-hash).** A user
   refreshing the page must not regenerate anything.
3. **Prompt caching** on the static portions of the system prompt (~10% of input
   rate on major providers).
4. **Batch API** (~50% discount) for everything not latency-bound: Monday recaps,
   archetype recomputation, SEO page generation.
5. **Template fallback** for low-value surfaces — not every string needs an LLM.

## 9. AI unit economics

Bottom-up, per paid user per gameweek (reproduce with `python3 finance.py`):

| Job | Input tokens | Output tokens | Calls/GW |
|---|---|---|---|
| Deadline Brief | 8,000 | 1,200 | 1 |
| Ask-the-Gaffer | 5,000 | 500 | 4 |
| Gameweek Recap | 6,000 | 800 | 1 |
| Rival dossier refresh | 4,000 | 600 | 2 |
| **Total** | **42,000** | **5,200** | — |

| Price band (USD /1M in / out) | Cost per gameweek | Cost per month (~4 GW) |
|---|---|---|
| Small (~$0.30 / $2.50) | $0.0256 | **$0.10** |
| Mid (~$2.00 / $12.00) | $0.1464 | **$0.59** |

Against a blended net ARPU of **€3.56/paid user/month**:

- At the small-model band, AI is **~3%** of net revenue.
- At the mid-model band, AI is **~16%** of net revenue.
- The financial scenarios in `07-business-model.md` budget **€0.25–0.60** per paid
  user per month — 5–15× the bottom-up figure — as headroom for power users,
  retries, cache misses and a heavier model on the Deadline Brief.

**Conclusion: AI is not the cost problem in this business.** Simulation CPU and
customer acquisition are. That is a healthy place to be, and it is a direct
consequence of choosing a product where AI narrates a computation instead of
being the computation.

## 10. Fallback behaviour

| Failure | Behaviour |
|---|---|
| LLM provider down | Switch to fallback provider; if both down, render the deterministic template brief (numbers, no prose) with a banner |
| Schema validation fails twice | Deterministic template brief |
| Numeric grounding check fails twice | Deterministic template brief + alert to the founder |
| FPL API down | Serve the last cached snapshot with a visible "data as of" timestamp; never show stale data silently |
| Simulation worker down | Serve the previous gameweek's odds, clearly labelled; queue a re-run |

The rule behind all of these: **the product is allowed to be less impressive. It
is never allowed to be wrong.**

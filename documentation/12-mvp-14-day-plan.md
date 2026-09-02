# The 14-day MVP

## What the MVP is for

It is **not** for building the product. It is for answering one question:

> **Will a mini-league player pay for rival-relative advice?**

Everything that does not help answer that is cut. The plan below is written on the
assumption of a solo builder working focused days, with the season already
underway — which is the correct time to launch this and the reason the calendar is
tight.

**Scope frozen at:** ingest → simulate → league board → rival dossier → paywall →
Deadline Brief → Stripe. No simulator, no chip planner, no Ask-the-Gaffer, no
Discord bot, no programmatic SEO. Those are V1.

## Timing — this matters more than it looks

A live check of the FPL API on **31 August 2026** shows the 2026/27 season at
**gameweek 2**. **[verified]** That is very close to the ideal launch window and
it is the reason this plan is written to start now rather than "soon":

- Mini-leagues have just been created and are socially hot; nobody has given up yet.
- The gap between managers is small, so *everyone* is still catchable — which is
  precisely when a rival-relative product is most persuasive.
- Building through September puts a launch in mid-September, around GW5–6, when
  the first real separation appears in leagues and the "I'm falling behind"
  feeling arrives.
- The alternative is waiting for August 2027. There is no third option. The cost
  of a two-month delay in this business is not two months; it is a year.

---

## Days 1–3 — Data foundation

### Day 1 — Ingest skeleton

- Repo, monorepo layout (`/web` Next.js, `/api` FastAPI, `/worker`), CI running
  lint + typecheck on push.
- Postgres provisioned; Alembic set up; migrations for `gameweeks`, `teams`,
  `players`, `fixtures`, `raw_snapshots`.
- Shared HTTP client with the global rate limiter, ETag support, backoff, and a
  descriptive User-Agent.
- Ingest `bootstrap-static/` and `fixtures/`; store raw + normalised.
- **Done when:** `SELECT count(*) FROM players` returns ~700 and re-running the
  ingest produces zero duplicate rows.

### Day 2 — Manager, league and picks ingest

- Migrations for `managers`, `leagues`, `league_members`, `manager_picks`,
  `manager_transfers`.
- Ingest `leagues-classic/{id}/standings` with pagination; `entry/{id}/`;
  `entry/{id}/history/`; `entry/{id}/event/{gw}/picks/`; `entry/{id}/transfers/`.
- Guard: refuse leagues over 200 members; never re-fetch immutable picks.
- **Done when:** given one real league ID, the database holds every member's full
  squad for every completed gameweek.

### Day 3 — Projection model v0

- `projections` table; a decayed per-90 model with minutes probability, fixture
  adjustment, set-piece flag and defensive-contribution rate.
- Backtest harness over completed gameweeks; record MAE.
- **Done when:** MAE is computed, printed, and stored — and it is *good enough to
  be honest about*, not good. This is deliberately timeboxed to one day, because
  projections are not the product.

---

## Days 4–5 — The engine

### Day 4 — Monte Carlo simulator

- Vectorised NumPy simulation of remaining gameweeks across all league members.
- Outputs: `p_above[rival]`, gap percentiles, per-rival differential lists.
- Seeded and deterministic; `simulations` table with `input_hash` caching.
- Tests: determinism, known answers, monotonicity.
- **Done when:** a 10-manager league simulates 20,000 seasons in under 2 seconds
  and produces identical output on a repeat run.

### Day 5 — Move deltas and rival profiling

- Candidate-move evaluation with common random numbers: captain changes, single
  transfers from an affordable shortlist. Output `delta_p_above` per rival.
- `rival_profiles`: hit rate, template score, reactivity, chip timing, archetype
  from a fixed enum.
- **Done when:** for a real league, the system names the single move that most
  improves P(above) for the nearest catchable rival — as a number, with no LLM
  involved yet.

*(End of day 5 is the technical point of no return: if the engine does not produce
a believable answer here, stop and reconsider before building UI.)*

---

## Days 6–8 — The product surface

### Day 6 — Public league board

- Next.js app shell, design tokens, dark theme.
- `/l/{league_id}`: server-rendered board with the odds column, "you can still
  catch N of M", three rival cards.
- Landing page with the single league-ID input and the copy from `09-ux-ui-spec.md`.
- **Done when:** a stranger can paste a league ID on a phone and see real
  probabilities in under 5 seconds, with no account.

### Day 7 — Rival dossier (the aha moment)

- `/l/{id}/vs/{entry_id}` with all sections from `09-ux-ui-spec.md` §3.3 except
  "THE MOVE".
- Share image generation (OG PNG) for both league and head-to-head cards.
- **Done when:** the founder shows it to three FPL-playing friends and at least
  two of them immediately share it into a group chat unprompted. *That reaction,
  or its absence, is the first real signal in this whole plan.*

### Day 8 — Auth and accounts

- Magic-link auth end to end; sessions; `/app` dashboard with the deadline
  countdown; league tracking; age-band capture per `11-legal-security-risk.md`.
- Account page: export, delete, plan status.
- **Done when:** signup → email → logged in → league saved works on a real device,
  and deletion actually deletes.

---

## Days 9–11 — Monetisation and the AI layer

### Day 9 — LLM narration

- Prompt v1 for the Deadline Brief with the structured payload and output contract
  from `06-ai-spec.md`.
- Schema validation, numeric grounding check, banned-phrase check, template
  fallback, cost logging per generation.
- **Done when:** ten briefs generate across ten different leagues, all pass the
  grounding check, and deliberately corrupted fixtures reliably trigger the
  fallback.

### Day 10 — Paywall and Stripe

- Stripe products: monthly €4.99 recurring, season pass €29.99 one-time with
  `season_ends_at` entitlement.
- Checkout, Customer Portal, webhooks with signature verification and idempotency.
- `require_plan` entitlement dependency applied to every Pro route; exhaustive
  tests that a free user is blocked everywhere.
- Paywall UI on the second dossier and on "THE MOVE", naming the specific rival.
- **Done when:** a real card in test mode buys both plans, unlocks instantly, and
  cancels cleanly — and a free account cannot reach a single Pro byte.

### Day 11 — Email and the return loop

- Resend integration; Deadline Brief email 36h before the deadline; Monday recap.
- Scheduler jobs: ingest cadence, simulation refresh, email dispatch.
- Unsubscribe, marketing-consent handling, no email to under-16 accounts.
- **Done when:** a scheduled brief lands in a real inbox at the right time, renders
  on mobile, and the unsubscribe link works.

---

## Days 12–14 — Ship

### Day 12 — Analytics, legal, hardening

- PostHog with the full event taxonomy from `10-growth-and-seo.md` §5, behind
  consent; the funnel and `aha_reached` event wired.
- Privacy policy, terms, cookie banner, the plain-language "what we collect"
  summary, the Premier League disclaimer.
- Rate limits on every route; CSP; Sentry; uptime monitor; the hard LLM daily spend
  cap; backup restore tested once, for real.

### Day 13 — Private beta and the GO/NO-GO

- Deploy to production. Seed 30–50 real users: the founder's own leagues, one
  FPL Discord (with moderator permission), and direct outreach.
- Watch the funnel live for a full deadline cycle.
- **Run the GO/NO-GO below.**

### Day 14 — Public launch or pivot

**If GO:** the r/FantasyPL post, the Discord posts, the share loop switched on,
and a fix list drawn from beta feedback.
**If NO-GO:** stop. Do not build V1. Run the diagnosis in the table below.

---

## GO / NO-GO thresholds

Measured over the beta cohort during one full gameweek cycle. These are
**[assumption]**-based targets set deliberately low enough to be reachable and
high enough to be meaningful.

| # | Metric | GO | Investigate | NO-GO |
|---|---|---|---|---|
| 1 | **Aha rate** — visitors who open a rival dossier and scroll past the differentials | ≥ 45% | 25–45% | < 25% |
| 2 | **Share rate** — dossier viewers who click share | ≥ 15% | 8–15% | < 8% |
| 3 | **Return rate** — beta users returning before the *next* deadline unprompted | ≥ 40% | 25–40% | < 25% |
| 4 | **Paywall click-through** — users hitting the paywall who start checkout | ≥ 8% | 4–8% | < 4% |
| 5 | **Paid conversion** — registered beta users who actually pay | ≥ 3% (≥ 2 of 50) | 1–3% | 0 |
| 6 | **Qualitative** — unprompted messages asking for a feature, not reporting a bug | ≥ 5 | 2–4 | 0 |
| 7 | **Grounding failures** in generated briefs | 0 | — | any user-visible one |

**The decision rule.** Metric 5 with a cohort of 50 is statistically almost
meaningless on its own — two payers could be luck. So: **GO requires metrics 1, 3
and 5 all in the GO band.** Value delivered (1), habit formed (3), and money
changing hands (5). Any one of them failing is a different diagnosis:

| Failing | Diagnosis | Next move |
|---|---|---|
| 1 only | The dossier isn't landing | Rework the aha screen, re-test in one week. Cheap. |
| 3 only | Value is real but not habitual | Fix the email loop and the countdown before anything else |
| 5 only | It's good, it's habitual, it's not worth money | Move the paywall, test €29.99 vs €39.99, test the League Pass. If still zero after two attempts, this is a free tool with an ads/sponsorship model, not a subscription business. |
| 1 and 3 | The premise is wrong | **Stop.** Return to `03-scoring-and-elimination.md` and reopen finalist #3. |

**The thing to protect against:** a founder who has spent two weeks building will
want to reinterpret a NO-GO as an "investigate". Write the thresholds down before
launch, show them to someone else, and let that person hold you to them.

---

## Explicitly out of scope for the 14 days

Overtake Simulator · chip planner · Ask-the-Gaffer · Monday recap beyond a basic
version · head-to-head leagues · multi-league dashboard · programmatic SEO ·
Discord bot · light mode · native app · League Pass · regional pricing · Google
OAuth · Redis · any second sport.

Every one of these is a good idea. None of them changes the answer to the one
question the MVP exists to ask.

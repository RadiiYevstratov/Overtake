# Overtake

**Overtake tells you exactly what it takes to finish above the specific people in
your Fantasy Premier League mini-league.**

Every other FPL tool maximises expected points against thirteen million
strangers. Nobody has a global rank framed on their wall. Overtake maximises a
different number — the probability that you finish above a *named person* — and
those two objectives give different answers, most sharply when you are behind.

> Not affiliated with, endorsed by, or associated with the Premier League or
> Fantasy Premier League. Overtake reads only data that is already public, and
> never asks for an FPL password.

---

## How it actually works

Four layers. Only the last one is an AI, and it never produces a number.

| Layer | What it does | Deterministic? |
|---|---|---|
| **L0 Ingest** | Pulls and normalises public FPL state — squads, transfers, chips, standings | yes |
| **L1 Projection** | Expected points and start probability per player per gameweek | yes |
| **L2 Simulation** | 20,000 Monte Carlo seasons → `P(you finish above rival X)`, gap distributions, move deltas | yes, seeded |
| **L3 Profiling** | Behavioural priors per rival from their public transfer history | yes |
| **L4 Narration** | Turns the distribution into one named, specific argument | no |

The simulation is the product. If the LLM is unavailable, over budget, or fails
a grounding check twice, the product renders the same numbers with no prose at
all. **It is allowed to be less impressive. It is never allowed to be wrong.**

### Things worth knowing about the engine

- **Determinism is a feature.** Every run stores its seed and an input hash. The
  same inputs always produce the same odds — otherwise users watch their
  probability flicker between refreshes and stop believing any of it.
- **Common random numbers.** Candidate moves are extra columns of the same
  weight matrix, so every scenario is scored against byte-identical sampled
  points. Ten candidate moves cost barely more than one.
- **Teammate correlation.** Player scores are correlated within a club — a clean
  sheet pays four defenders at once. Sampling independently put the gameweek
  standard deviation at 13 against a real ~19, which made every rival comparison
  over-confident.
- **Parameter uncertainty.** Each simulated season draws a per-player quality
  multiplier held for the whole season, so the projection layer's own error
  reaches the odds instead of being treated as truth.
- **Shrinkage everywhere.** Two gameweeks of scoring is noise, not signal. The
  projection model shrinks hard toward a price-and-position prior and Winsorises
  observed scoring; rival profiles shrink toward population priors and report
  "not enough history yet" rather than inventing a personality from one
  transfer.

---

## Repository layout

```
api/                 FastAPI service, simulation engine, worker
  overtake/
    core/            config, logging, errors, security, rate limiting
    db/              engine, session, dialect-portable column types
    models/          SQLAlchemy models (the full schema)
    fpl/             polite FPL API client + normalising ingest
    engine/          projections (L1), simulator (L2), profiling (L3)
    llm/             provider interface, prompts, anti-hallucination stack
    routes/          the REST surface
    services/        auth, entitlements, billing, email, dossiers
    workers/         job queue, scheduled tasks, worker process
  alembic/           migrations
  prompts/           versioned prompt files
  tests/             unit + integration, all offline
web/                 Next.js 15 app (App Router)
  app/               routes
  components/        UI
  lib/               API client, types, formatting
  e2e/               Playwright journeys
scripts/             seeding and migration tooling
documentation/       the product and engineering specification
```

---

## Running it locally

**Requirements:** Python 3.12+, Node 20+.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY
```

### 1. The API

```bash
cd api
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev]"
alembic upgrade head
python ../scripts/seed_local.py   # pulls real FPL data and builds a demo league
uvicorn overtake.main:app --reload --port 8000
```

`seed_local.py` assembles a nine-manager demo league from real FPL entries
sampled across the rankings, because public FPL leagues are either private or
enormous. Pass `--league 12345` to seed a real classic league instead.

For a fully offline database (no network at all), use `scripts/seed_e2e.py`,
which builds the same thing from the recorded fixtures in `api/tests/fixtures/`.

### 2. The web app

```bash
cd web
npm install
npm run dev            # http://localhost:3000
```

The API is proxied under `/api/v1` on the same origin, so the session cookie is
first-party and the CSRF double-submit works with no cross-site exemption.

### 3. The worker (optional locally)

```bash
cd api
python -m overtake.workers.runner
```

It ingests on a schedule, refreshes simulations, sends the Deadline Brief 36
hours before each deadline, and runs the nightly retention sweep. The cadence
tightens inside the six hours before a deadline and stops entirely in June and
July, when there is no product to poll.

---

## Testing

```bash
cd api  && pytest -q                 # 225 unit + integration tests, all offline
cd api  && ruff check . && mypy overtake
cd web  && npm run typecheck && npm run build
cd web  && npm run test:e2e          # 52 Playwright journeys, desktop + mobile
```

Nothing in the suite touches the network: the FPL API is replaced by a stub that
serves anonymised responses recorded from the real thing, reproducing its
routes, its 404s and its ETag behaviour.

**What the tests actually protect:**

- **Determinism, monotonicity and known answers** in the simulator — a manager
  100 points ahead with one gameweek left must be a near-certainty, and more
  points must never lower your odds.
- **Calibration bands.** Simulated scoring must land in a realistic
  points-per-gameweek range and a realistic variance. Three separate modelling
  bugs were caught by these and nothing else.
- **The anti-hallucination stack**, fed deliberately corrupted completions:
  invented numbers, invented players, and certainty language must all fall back
  to the deterministic template rather than reaching a user.
- **Entitlements, exhaustively.** A free user must be blocked from every Pro
  route, and a signed-out user must get 401 before 402.
- **Every retention promise** in the privacy policy, as executable assertions.

---

## Environment

Every variable is documented in [`.env.example`](.env.example). The ones that
matter most:

| Variable | Why it matters |
|---|---|
| `SECRET_KEY` | Signs unsubscribe and share tokens. Production refuses to boot without a real one. |
| `DATABASE_URL` | PostgreSQL in production; SQLite locally and in CI. Production refuses to boot on SQLite. |
| `ANTHROPIC_API_KEY` | Optional. Without it, briefs render from the deterministic template. |
| `ANTHROPIC_MODEL` | Never hard-coded outside config: model names and prices change, and the unit economics depend on being able to change tier without a deploy. |
| `LLM_DAILY_SPEND_CAP_USD` | A hard, in-code cap. When it is hit, generation degrades to templates. A runaway AI bill is the most plausible way this business loses money. |
| `STRIPE_*` | Checkout, portal and webhook verification. Production refuses to boot with billing enabled and these unset. |
| `FPL_CONTACT_EMAIL` | Goes in the User-Agent on every FPL request. Use an address you monitor. |

Production boot validates its own configuration and **refuses to start** on a
misconfiguration rather than running half-configured — a broken session secret
or billing setup is worse than downtime.

---

## Deployment

| Piece | Where | Notes |
|---|---|---|
| API + worker | Fly.io (`fly.toml`) | One image, two processes. The API never scales to zero: a cold start two hours before a deadline is an outage. |
| Web | Vercel (`vercel.json`) | SSR everywhere; ISR on the public SEO pages. |
| Database | Managed PostgreSQL | Daily backups with PITR. **Test a restore before launch — an untested backup is not a backup.** |

Migrations run with Alembic as a **separate, manually approved step**, never
automatically on deploy.

### The deadline-day runbook

The two hours before a gameweek deadline are the highest-traffic and
highest-stakes window of the week.

1. Check `/api/v1/health` — `fpl_api` must read `ok`, not `stale`.
2. Confirm simulations are fresh for the most-tracked leagues.
3. **Never deploy within six hours of a deadline.**

---

## Security posture

- **No passwords exist.** Magic links only; both link and session tokens are
  stored as SHA-256 hashes, so a database dump cannot be used to sign in.
- **Sessions are opaque and server-side**, so they can actually be revoked.
- **CSRF** by double-submit on every mutating route; webhooks are exempt because
  they authenticate by signature and carry no cookie.
- **Authorisation has two dimensions** — ownership and entitlement — both
  enforced server-side by one shared dependency. Frontend plan state is a
  rendering hint, never a gate.
- **Rate limits on every route**, written in one place so a new route cannot
  ship without one, and recorded in their own transaction so a handler error
  cannot roll an increment back.
- **All rival free text is treated as hostile.** Team names are typed by
  strangers and reach both the page and the LLM prompt; they are normalised,
  stripped of control and bidirectional-override characters, truncated, and
  delimited as untrusted data inside prompts.
- **The LLM has no side-effecting tools**, receives only computed values, and
  everything it writes is checked back against that input.
- **Stripe handles all card data.** Webhooks are signature-verified and
  idempotent through a recorded event ledger.

Run `pip-audit` and `npm audit` in CI on every push.

---

## Deliberate non-goals

Named here because they are decisions, not omissions:

- **No points-projection arms race.** Incumbents hold Opta licences; we publish
  our measured error instead of pretending to compete.
- **Nothing touching odds-as-prices, stakes or bookmakers.** Ever. It would put
  a skill-analysis product inside gambling regulation and make it inappropriate
  for the 15–17 users it serves on the free tier.
- **No write access to FPL accounts**, and no FPL password is ever requested.
- **No native app in year one.** A PWA covers a deadline check on a phone.
- **No social feed.** Users already have a group chat; feeding it beats
  competing with it.
- **No chatbot as the front door.** The simulation is the product; leading with
  a chat box would say "wrapper".

---

## Licence and attribution

Player names and statistics are facts and are used as such. No club crests and
no player photography appear anywhere in the product — partly a licensing
decision, and partly because the design is better without them.

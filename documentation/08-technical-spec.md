# Technical specification

Written to be buildable by another developer or a coding agent without further
product input.

---

## 1. Architecture

```
                    ┌──────────────────────────────────────┐
                    │  fantasy.premierleague.com/api/      │
                    │  (public, unauthenticated, read-only)│
                    └──────────────┬───────────────────────┘
                                   │ polite polling, ETag, backoff
                    ┌──────────────▼───────────────────────┐
                    │  INGEST WORKER  (Python, APScheduler) │
                    │  bootstrap · fixtures · live · picks  │
                    │  · league standings · set-piece notes │
                    └──────────────┬───────────────────────┘
                                   │ upsert
        ┌──────────────────────────▼──────────────────────────┐
        │            POSTGRES  (Supabase or Neon)             │
        │  raw snapshots · normalised entities · simulations  │
        │  · league memory · users · subscriptions            │
        └───────┬─────────────────────────────┬───────────────┘
                │                             │
   ┌────────────▼─────────────┐   ┌───────────▼──────────────┐
   │  SIM WORKER              │   │  API  (FastAPI)          │
   │  projections + Monte     │   │  REST + SSE              │
   │  Carlo, NumPy, seeded    │   │  auth · billing · reads  │
   │  cached per league/GW    │   └───────────┬──────────────┘
   └──────────────────────────┘               │
                                   ┌──────────▼──────────────┐
                                   │  WEB  (Next.js, Vercel) │
                                   │  SSR marketing + SEO,   │
                                   │  client app shell       │
                                   └──────────┬──────────────┘
                                              │
                        ┌─────────────────────┼─────────────────┐
                     Stripe                Resend           LLM provider
                   (billing)              (email)          (+ fallback)
```

**Design principles**

1. Ingest, simulate and serve are separate processes. The web app never calls the
   FPL API on a user request — always the cache.
2. Everything expensive is cached at the **league × gameweek** grain, not the user
   grain.
3. The LLM is a leaf node. If it is down, the product still works.

---

## 2. Stack

| Layer | Choice | Alternatives considered | Cost | Why | Downside |
|---|---|---|---|---|---|
| Frontend | **Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui** | SvelteKit, Remix, Astro | Vercel Hobby €0, Pro $20/mo | SSR/ISR is essential for programmatic SEO; largest ecosystem; one deploy target | Heavier than the app needs; vendor pull toward Vercel |
| Backend | **FastAPI (Python 3.12)** | Node/Express, Django | Fly.io / Railway ~€5–10/mo | The simulation is NumPy; keeping the API in the same language as the model avoids a service boundary | Two languages in the repo |
| Simulation | **NumPy, vectorised, seeded** | pandas loops, Rust, C ext. | CPU only | 8M samples/run in well under a second; no dependency risk | Memory spikes on very large leagues — cap at 200 managers |
| Database | **Postgres** (Supabase free → Neon/Supabase paid) | SQLite+Litestream, MySQL | €0 → €25/mo | JSONB for raw snapshots, relational for everything else; both providers have a real free tier | Free tiers pause on inactivity — a paid tier is required before launch day |
| Cache/queue | **Postgres** (`LISTEN/NOTIFY` + a jobs table) at MVP; **Redis** at V1 | Redis from day 1, Celery, SQS | €0 → €10/mo | One fewer moving part in a 14-day build. Do not add Redis until a queue actually backs up. | Won't scale past a few thousand jobs/hour |
| Auth | **Magic link (email) via a signed token**, plus optional Google OAuth | Supabase Auth, Clerk, Auth.js | €0 | No passwords means no password breach, no reset flow, no hashing decisions. Suits the audience. | Email deliverability becomes critical-path |
| Payments | **Stripe Checkout + Customer Portal + Stripe Tax** | Paddle, LemonSqueezy | EEA 1.5% / UK 2.5% / intl 3.15%, each + €0.25; Stripe Tax 0.5%; Billing 0.7% on recurring only | Available to a Slovak seller; Checkout removes all card handling from scope; Tax handles EU VAT OSS and UK VAT | Not a merchant of record — VAT registration is on the founder (see `11-`). Paddle/LemonSqueezy *are* merchants of record and remove the VAT burden entirely at ~5% — worth reconsidering if VAT filing proves onerous. |
| Email | **Resend** | Postmark, SES, Loops | Free to 3k/mo, then ~$20 | Transactional + broadcast in one API; React Email templates | Another vendor |
| Storage | **Cloudflare R2** for generated share images | S3, Vercel Blob | ~€0 at this scale | No egress fees, which matters for share images | — |
| Analytics | **PostHog Cloud (EU)** | Plausible + custom, Mixpanel | Free to 1M events/mo | Funnels, retention cohorts and session replay in one tool; EU hosting simplifies GDPR | Heavier script than Plausible |
| Errors/logs | **Sentry** (free tier) + structured JSON logs | Better Stack, Axiom | €0 | Standard | — |
| Uptime | **Better Stack** or UptimeRobot free | — | €0 | Deadline-critical: an outage 2h before a deadline is the worst possible outage | — |
| Hosting (workers) | **Fly.io** or **Railway** | Render, Hetzner VPS | €5–15/mo | Persistent processes with cron; a Hetzner VPS at ~€4/mo is the cheapest fallback if PaaS pricing bites | PaaS free tiers have been repeatedly cut |
| LLM | Provider A + provider B behind one interface | — | See `06-ai-spec.md` | Never hard-code a model name | Provider pricing changes monthly |

**Total fixed monthly cost at launch: €0–15.** Comfortably inside the €50–200
budget, with the first year's domain (~€12) as the largest one-off.

---

## 3. Data ingest

### Endpoints used (all public, all unauthenticated)

| Endpoint | Cadence | Purpose |
|---|---|---|
| `bootstrap-static/` | Hourly; every 10 min in the 6h before a deadline | Players, teams, prices, gameweek metadata |
| `fixtures/` | Daily; hourly on matchdays | Schedule and FDR |
| `fixtures/?event={gw}` | Per gameweek | Gameweek fixtures |
| `element-summary/{id}/` | Daily, only for players owned in a tracked league | Per-player history |
| `event/{gw}/live/` | Every 2 min during matches | Live points |
| `entry/{id}/` | On league refresh | Manager metadata |
| `entry/{id}/history/` | Weekly | Season history + chips |
| `entry/{id}/event/{gw}/picks/` | Once per manager per gameweek, after lockdown | **Rival squads — the core asset** |
| `leagues-classic/{id}/standings/` | Hourly during a gameweek | Standings, member list (paginate) |
| `team/set-piece-notes/` | Weekly | Set-piece takers |
| `event-status/` | Every 5 min post-match | Whether points are final |

### Ingest rules (non-negotiable)

- **One shared HTTP client** with a global token-bucket limiter. Target ≤ 2
  requests/second sustained, never bursting.
- Honour `ETag`/`If-None-Match` and `Last-Modified`. A 304 costs nothing.
- Exponential backoff with jitter on 429/5xx; circuit-break after 5 consecutive
  failures and serve cache.
- Descriptive `User-Agent` including a contact email. Be a good citizen — this API
  is a gift, not a right.
- Store raw JSON in `raw_snapshots` (JSONB) before normalising, so a parser bug
  never costs data.
- Never poll a manager's picks more than once per gameweek; picks are immutable
  after lockdown.

### Fallback if the API is restricted

A CSV/JSON import path where a user pastes their league's public standings page
content. Degraded, but the product survives. Build the ingest layer behind an
interface so a second source can be swapped in.

---

## 4. Database schema (PostgreSQL)

```sql
-- ============ identity & billing ============

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT UNIQUE NOT NULL,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    fpl_entry_id    INTEGER,                         -- their FPL manager id
    display_name    TEXT,
    age_band        TEXT NOT NULL DEFAULT 'unknown'  -- 'under16','16_17','adult','unknown'
                      CHECK (age_band IN ('under16','16_17','adult','unknown')),
    marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ                      -- soft delete, purged after 30d
);
CREATE INDEX ON users (fpl_entry_id);
CREATE INDEX ON users (deleted_at) WHERE deleted_at IS NOT NULL;

CREATE TABLE auth_tokens (              -- magic links
    token_hash  BYTEA PRIMARY KEY,      -- sha256 of the token; never store raw
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose     TEXT NOT NULL CHECK (purpose IN ('login','email_change')),
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_ip  INET
);
CREATE INDEX ON auth_tokens (user_id);

CREATE TABLE sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash    BYTEA UNIQUE NOT NULL,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ
);
CREATE INDEX ON sessions (user_id);

CREATE TABLE subscriptions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_customer_id     TEXT NOT NULL,
    stripe_subscription_id TEXT UNIQUE,
    plan                   TEXT NOT NULL CHECK (plan IN ('monthly','season')),
    status                 TEXT NOT NULL,          -- mirrors Stripe status
    current_period_end     TIMESTAMPTZ,
    cancel_at_period_end   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX one_active_sub_per_user ON subscriptions (user_id)
    WHERE status IN ('active','trialing','past_due');

CREATE TABLE stripe_events (            -- webhook idempotency
    id           TEXT PRIMARY KEY,      -- Stripe event id
    type         TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ FPL domain ============

CREATE TABLE gameweeks (
    id                  SMALLINT PRIMARY KEY,       -- 1..38
    season              TEXT NOT NULL,              -- '2026/27'
    name                TEXT NOT NULL,
    deadline_utc        TIMESTAMPTZ NOT NULL,
    is_current          BOOLEAN NOT NULL DEFAULT FALSE,
    is_finished         BOOLEAN NOT NULL DEFAULT FALSE,
    data_checked        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (season, id)
);

CREATE TABLE teams (
    id            SMALLINT PRIMARY KEY,
    season        TEXT NOT NULL,
    name          TEXT NOT NULL,
    short_name    TEXT NOT NULL,
    strength_home SMALLINT,
    strength_away SMALLINT
);

CREATE TABLE players (
    id                      INTEGER PRIMARY KEY,     -- FPL element id
    season                  TEXT NOT NULL,
    team_id                 SMALLINT NOT NULL REFERENCES teams(id),
    web_name                TEXT NOT NULL,
    first_name              TEXT,
    second_name             TEXT,
    position                SMALLINT NOT NULL,       -- 1 GK 2 DEF 3 MID 4 FWD
    now_cost                SMALLINT NOT NULL,       -- tenths of a million
    status                  CHAR(1) NOT NULL,        -- a/d/i/s/u
    chance_of_playing_next  SMALLINT,
    selected_by_percent     NUMERIC(5,2),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON players (team_id);
CREATE INDEX ON players (season, position);

CREATE TABLE player_gameweek_stats (
    player_id   INTEGER NOT NULL REFERENCES players(id),
    gameweek_id SMALLINT NOT NULL REFERENCES gameweeks(id),
    minutes     SMALLINT NOT NULL DEFAULT 0,
    total_points SMALLINT NOT NULL DEFAULT 0,
    goals       SMALLINT NOT NULL DEFAULT 0,
    assists     SMALLINT NOT NULL DEFAULT 0,
    bonus       SMALLINT NOT NULL DEFAULT 0,
    bps         SMALLINT NOT NULL DEFAULT 0,
    def_contrib SMALLINT NOT NULL DEFAULT 0,
    was_home    BOOLEAN,
    opponent_team SMALLINT,
    PRIMARY KEY (player_id, gameweek_id)
);

CREATE TABLE fixtures (
    id             INTEGER PRIMARY KEY,
    gameweek_id    SMALLINT REFERENCES gameweeks(id),   -- NULL = postponed
    kickoff_utc    TIMESTAMPTZ,
    team_h         SMALLINT NOT NULL REFERENCES teams(id),
    team_a         SMALLINT NOT NULL REFERENCES teams(id),
    team_h_difficulty SMALLINT,
    team_a_difficulty SMALLINT,
    finished       BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ON fixtures (gameweek_id);

CREATE TABLE managers (                 -- any FPL entry we have seen
    entry_id     INTEGER PRIMARY KEY,
    player_name  TEXT,
    team_name    TEXT,
    region       TEXT,
    started_event SMALLINT,
    last_synced_at TIMESTAMPTZ
);

CREATE TABLE leagues (
    id             INTEGER PRIMARY KEY,     -- FPL league id
    name           TEXT NOT NULL,
    league_type    TEXT NOT NULL DEFAULT 'classic'
                     CHECK (league_type IN ('classic','h2h')),
    size           INTEGER,
    first_tracked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_synced_at TIMESTAMPTZ,
    is_public_global BOOLEAN NOT NULL DEFAULT FALSE   -- exclude the global league
);

CREATE TABLE league_members (
    league_id   INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    entry_id    INTEGER NOT NULL REFERENCES managers(entry_id),
    rank        INTEGER,
    total       INTEGER,
    last_rank   INTEGER,
    PRIMARY KEY (league_id, entry_id)
);
CREATE INDEX ON league_members (entry_id);

CREATE TABLE user_leagues (             -- which leagues a user tracks
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    league_id  INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, league_id)
);

CREATE TABLE manager_picks (            -- the core asset
    entry_id       INTEGER NOT NULL REFERENCES managers(entry_id),
    gameweek_id    SMALLINT NOT NULL REFERENCES gameweeks(id),
    picks          JSONB NOT NULL,      -- [{element,position,multiplier,is_captain}]
    active_chip    TEXT,
    bank           SMALLINT,
    team_value     SMALLINT,
    event_transfers SMALLINT,
    event_transfers_cost SMALLINT,
    points         SMALLINT,
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entry_id, gameweek_id)
);

CREATE TABLE manager_transfers (
    id          BIGSERIAL PRIMARY KEY,
    entry_id    INTEGER NOT NULL REFERENCES managers(entry_id),
    gameweek_id SMALLINT NOT NULL REFERENCES gameweeks(id),
    element_in  INTEGER NOT NULL,
    element_out INTEGER NOT NULL,
    cost_in     SMALLINT,
    cost_out    SMALLINT,
    UNIQUE (entry_id, gameweek_id, element_in, element_out)
);

-- ============ model outputs ============

CREATE TABLE projections (
    player_id   INTEGER NOT NULL REFERENCES players(id),
    gameweek_id SMALLINT NOT NULL REFERENCES gameweeks(id),
    model_version TEXT NOT NULL,
    mu          NUMERIC(6,3) NOT NULL,
    sigma       NUMERIC(6,3) NOT NULL,
    p_start     NUMERIC(4,3) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, gameweek_id, model_version)
);

CREATE TABLE simulations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    gameweek_id     SMALLINT NOT NULL REFERENCES gameweeks(id),
    input_hash      TEXT NOT NULL,      -- hash of all inputs; the cache key
    seed            BIGINT NOT NULL,
    n_sims          INTEGER NOT NULL,
    model_version   TEXT NOT NULL,
    results         JSONB NOT NULL,     -- {entry_id: {p_above:{}, gap_p10/50/90}}
    duration_ms     INTEGER,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (league_id, gameweek_id, input_hash)
);
CREATE INDEX ON simulations (league_id, gameweek_id DESC);

CREATE TABLE rival_profiles (
    entry_id      INTEGER NOT NULL REFERENCES managers(entry_id),
    season        TEXT NOT NULL,
    archetype     TEXT NOT NULL,        -- fixed enum, see 06-ai-spec.md
    hit_rate      NUMERIC(5,3),
    template_score NUMERIC(4,3),
    reactivity    NUMERIC(4,3),
    bench_waste   NUMERIC(6,2),
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entry_id, season)
);

CREATE TABLE league_memory (            -- the compounding asset
    id          BIGSERIAL PRIMARY KEY,
    league_id   INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    gameweek_id SMALLINT NOT NULL REFERENCES gameweeks(id),
    kind        TEXT NOT NULL,          -- 'chip_used','big_swing','lead_change',...
    entry_id    INTEGER REFERENCES managers(entry_id),
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON league_memory (league_id, gameweek_id DESC);

CREATE TABLE briefs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    league_id     INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    gameweek_id   SMALLINT NOT NULL REFERENCES gameweeks(id),
    simulation_id UUID REFERENCES simulations(id),
    prompt_version TEXT NOT NULL,
    model         TEXT NOT NULL,
    content       JSONB NOT NULL,       -- validated against the output contract
    tokens_in     INTEGER,
    tokens_out    INTEGER,
    cost_usd      NUMERIC(8,5),
    validation    JSONB,                -- grounding-check results
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, league_id, gameweek_id)
);

CREATE TABLE conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    league_id  INTEGER REFERENCES leagues(id) ON DELETE SET NULL,
    messages   JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
);

CREATE TABLE usage_counters (           -- rate limiting & entitlements
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period     DATE NOT NULL,
    metric     TEXT NOT NULL,           -- 'dossier','gaffer_msg','sim_scenario'
    count      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, period, metric)
);

CREATE TABLE raw_snapshots (            -- audit / replay
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    etag        TEXT,
    body        JSONB NOT NULL
);
CREATE INDEX ON raw_snapshots (source, fetched_at DESC);

CREATE TABLE jobs (                     -- MVP queue; replace with Redis at V1
    id          BIGSERIAL PRIMARY KEY,
    kind        TEXT NOT NULL,
    payload     JSONB NOT NULL,
    run_after   TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts    SMALLINT NOT NULL DEFAULT 0,
    locked_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_error  TEXT
);
CREATE INDEX ON jobs (run_after) WHERE completed_at IS NULL;
```

**Retention policy** (enforced by a nightly job): `raw_snapshots` 30 days ·
`conversations` 30 days · `auth_tokens` 7 days after expiry · soft-deleted users
purged after 30 days · `jobs` completed rows 14 days.

---

## 5. API design

Base: `/api/v1`. JSON only. Auth via `HttpOnly; Secure; SameSite=Lax` session
cookie. All mutating routes require a CSRF token (double-submit).

Standard error body:
```json
{"error": {"code": "RATE_LIMITED", "message": "…", "retry_after": 42}}
```

| Method | Route | Auth | Purpose | Request | Response | Errors | Rate limit |
|---|---|---|---|---|---|---|---|
| POST | `/auth/magic-link` | none | Send login email | `{email}` | `202 {}` | 400 invalid email | 5/h per IP + 3/h per email |
| GET | `/auth/callback?token=` | none | Consume link, set cookie | — | `302 /app` | 400 expired/used | 20/h per IP |
| POST | `/auth/logout` | session | Revoke session | — | `204` | — | — |
| GET | `/me` | session | Profile + entitlements | — | `{user, plan, limits, usage}` | 401 | 120/min |
| PATCH | `/me` | session | Set fpl_entry_id, display name, marketing opt-in | `{fpl_entry_id?, display_name?, marketing_opt_in?}` | `{user}` | 400, 409 entry in use | 30/min |
| DELETE | `/me` | session | Account deletion (soft, then purge) | `{confirm:true}` | `202` | 400 | 3/day |
| GET | `/me/export` | session | GDPR data export (JSON) | — | `200` file | 401 | 3/day |
| GET | `/fpl/manager/{entry_id}` | none | Public manager lookup | — | `{entry_id, team_name, leagues[]}` | 404, 502 upstream | 30/min per IP |
| GET | `/leagues/{id}` | none | League board **(the free hook)** | — | `{league, members[], odds[], computed_at}` | 404, 422 too large (>200), 425 not yet simulated | 30/min per IP |
| POST | `/leagues/{id}/track` | session | Add league to my account | — | `201` | 402 free-tier limit (1 league), 404 | 20/h |
| DELETE | `/leagues/{id}/track` | session | Stop tracking | — | `204` | — | 20/h |
| GET | `/leagues/{id}/rivals/{entry_id}/dossier` | session | **The aha moment.** Full rival dossier | — | `{p_above, gap, their_diffs[], my_diffs[], archetype, narrative}` | 402 free limit reached, 404 | 60/h |
| GET | `/leagues/{id}/brief` | session + Pro | Deadline Brief for current GW | `?gw=` | `{content, simulation_id, generated_at}` | 402, 425 | 10/h |
| POST | `/leagues/{id}/brief/regenerate` | session + Pro | Force regeneration | — | `{content}` | 402, 429 (max 3/GW) | 3/GW |
| POST | `/leagues/{id}/simulate` | session + Pro | Custom scenario | `{moves:[{type,player_in,player_out,captain}]}` | `{deltas, p_above_before, p_above_after}` | 400 invalid squad, 402, 429 | 10/GW |
| POST | `/leagues/{id}/ask` | session + Pro | Ask-the-Gaffer (SSE stream) | `{message<=500}` | SSE tokens | 402, 429 (20/day) | 20/day |
| GET | `/leagues/{id}/share-image` | none | OG/share PNG | `?entry=` | `image/png` | 404 | 60/h per IP |
| GET | `/players/{id}` | none | Public player page (SEO) | — | `{player, projections, ownership}` | 404 | 120/min |
| POST | `/billing/checkout` | session | Create Stripe Checkout session | `{plan:'monthly'\|'season'}` | `{url}` | 400, 409 already subscribed | 10/h |
| POST | `/billing/portal` | session | Customer Portal link | — | `{url}` | 404 no customer | 10/h |
| POST | `/webhooks/stripe` | signature | Billing events | Stripe event | `200` | 400 bad signature | — |
| GET | `/health` | none | Liveness + upstream status | — | `{ok, fpl_api, db, last_ingest}` | — | — |

**Validation rules**: `entry_id` and `league_id` are positive integers; league
size capped at 200 members (larger leagues return 422 with an explanation);
`gw` in 1..38; scenario moves validated against real squad legality (budget,
3-per-club, formation) before simulating.

**Entitlement enforcement lives in one place** — a `require_plan(...)` dependency
in FastAPI. Never check the plan in a route handler ad hoc.

---

## 6. Authentication and authorisation

- **Magic link.** 32 bytes of `secrets.token_urlsafe`, stored as SHA-256, 15-minute
  expiry, single use, invalidated on consumption. The email states the requesting
  IP and asks the user to ignore it if unexpected.
- **Sessions.** Opaque random token in an `HttpOnly; Secure; SameSite=Lax` cookie,
  30-day rolling expiry, revocable server-side. No JWTs — server-side revocation
  matters more than statelessness at this scale.
- **Optional Google OAuth** as a second path (reduces email-deliverability risk).
- **Authorisation.** Two dimensions: ownership (does this user track this league?)
  and entitlement (does their plan allow this?). Both are enforced server-side on
  every request. The frontend's plan state is a hint for rendering, never a gate.
- **No FPL credentials are ever requested or accepted.** The product only reads
  public endpoints. This is stated on the login page, because users have been
  trained by other tools to expect otherwise.

---

## 7. Payments

Flow:

1. `POST /billing/checkout` → create a Stripe Customer (if none) → Checkout
   Session with the chosen price, `client_reference_id = user.id`, Stripe Tax on,
   automatic tax ID collection for the EU.
2. Stripe hosts the payment. **No card data ever touches our servers.**
3. Webhooks handled: `checkout.session.completed`,
   `customer.subscription.created|updated|deleted`,
   `invoice.paid`, `invoice.payment_failed`.
4. Every webhook is verified by signature, recorded in `stripe_events` for
   idempotency, and processed inside a transaction.
5. `subscriptions` is a **mirror** of Stripe, never the source of truth. On any
   ambiguity, re-fetch from Stripe.
6. The Customer Portal handles upgrade, downgrade, payment-method update and
   cancellation. We build no billing UI.

Season pass implementation: a Stripe **subscription with a 10-month interval** is
not offered, so use a **one-time price** that grants entitlement until a stored
`season_ends_at`, with a renewal email in July. Simpler and avoids a surprise
auto-charge, which matters for a young audience.

---

## 8. Infrastructure and deployment

| Environment | Purpose | Data |
|---|---|---|
| `local` | Development | Seeded fixture data from recorded API snapshots |
| `preview` | Per-PR Vercel preview + shared staging DB | Anonymised subset |
| `production` | — | Real |

**CI/CD** (GitHub Actions):
`lint (ruff + eslint) → typecheck (mypy + tsc) → unit tests → migration dry-run →
build → deploy`. Migrations run with Alembic as a separate, manually-approved
step — never automatically on deploy.

**Secrets** live in the platform's secret store (Vercel/Fly), never in the repo.
One rotation runbook, documented.

**Backups**: managed daily Postgres backups with 7-day point-in-time recovery, plus
a weekly `pg_dump` to R2. **Restore must be tested once before launch** — an
untested backup is not a backup.

**The deadline-day runbook**: the two hours before a gameweek deadline are the
highest-traffic and highest-stakes window of the week. Before each deadline:
verify last ingest timestamp, verify simulation freshness for the top 100 leagues,
and have the degradation banner ready. Never deploy within 6 hours of a deadline.

---

## 9. Testing

| Layer | What | Tool |
|---|---|---|
| Ingest | Parse recorded API fixtures; assert schema stability; assert a changed upstream shape fails loudly | pytest + recorded JSON |
| Projections | Backtest against completed gameweeks; assert MAE below a threshold; **fail CI if MAE regresses** | pytest |
| Simulation | Determinism (same seed → same output); known-answer tests (a manager 100 points ahead with 1 GW left must be >99.9%); monotonicity (more points ahead never lowers p_above) | pytest + hypothesis |
| LLM | Golden-file tests per prompt version; grounding-check unit tests with deliberately hallucinated fixtures | pytest |
| API | Contract tests per endpoint incl. 401/402/429 paths | pytest + httpx |
| Entitlements | A free user must be blocked from every Pro route | pytest, exhaustive |
| Billing | Stripe test-mode fixtures for the full lifecycle incl. failed payment | pytest |
| E2E | Landing → league board → dossier → paywall → checkout (test mode) → brief | Playwright |
| Load | 500 concurrent league-board reads (the deadline spike) | k6 |

---

## 10. Monitoring

**Alerts that page the founder**: FPL ingest stale >30 min within 6h of a
deadline · simulation queue depth >100 · Stripe webhook failures · error rate >2%
· p95 latency >2s on `/leagues/{id}` · LLM grounding-check failure rate >5%.

**Dashboards**: ingest freshness per endpoint · simulations/hour and duration ·
LLM cost per day and per user · funnel (visit → league board → dossier → signup →
paywall → checkout) · MRR and plan mix.

**Cost guardrails**: a hard daily LLM spend cap enforced in code (not just an
alert). If exceeded, briefs fall back to the deterministic template and the
founder is notified. A runaway AI bill is the most plausible way this business
loses money on a €200 budget.

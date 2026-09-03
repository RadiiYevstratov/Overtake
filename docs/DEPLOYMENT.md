# Deployment runbook

Everything needed to take Overtake from a clean repository to a live product,
in dependency order. Each step names the exact command and the thing to verify
before moving on. Nothing here auto-runs; every external step is deliberate.

The topology is fixed:

| Piece | Host | Config file |
|---|---|---|
| API + worker | Fly.io | [`fly.toml`](../fly.toml), [`api/Dockerfile`](../api/Dockerfile) |
| Web | Vercel | [`vercel.json`](../vercel.json) |
| Database | Managed PostgreSQL (Fly Postgres, Neon, Supabase, RDS…) | — |

---

## 0. Prerequisites (accounts you must own)

You cannot deploy without these. Create them first; they gate everything below.

1. **Fly.io** account + `flyctl` installed and authenticated (`fly auth login`).
2. **Vercel** account + the repository imported, or `vercel` CLI authenticated.
3. **Managed PostgreSQL** 16+ with daily backups and point-in-time recovery.
4. **Stripe** account (live mode) with two prices created: a monthly
   subscription and a one-time season pass.
5. **Anthropic** API key (optional — without it, briefs render from the
   deterministic template, which is a supported mode, not a failure).
6. **Resend** (or another provider wired into `email_service`) + a verified
   sending domain.
7. A **registered domain** you control DNS for.

---

## 1. Dependency order

```text
1. Provision PostgreSQL ─────────┐
2. Create Stripe prices          │  (independent — do in parallel)
3. Get Anthropic + Resend keys   │
   ↓                             │
4. Set API secrets on Fly ◄──────┘
   ↓
5. Deploy API image to Fly (do NOT run migrations yet)
   ↓
6. Run `alembic upgrade head` against production (manual, approved)
   ↓
7. Register the Stripe webhook → save STRIPE_WEBHOOK_SECRET → redeploy API
   ↓
8. Deploy Web to Vercel with API_INTERNAL_URL + NEXT_PUBLIC_SITE_URL
   ↓
9. Point DNS at Fly (api.) and Vercel (apex + www)
   ↓
10. Seed at least one real league, then run the smoke checklist (§6)
```

Steps 1–3 are independent and can be done in any order. Everything from 4 on is
strictly sequential: the webhook secret (7) is only known after the API exists
(5), and the web app (8) needs the API reachable.

---

## 2. Environment variables

The authoritative list with inline notes is [`.env.example`](../.env.example).
Production **refuses to boot** on a misconfiguration — see
`Settings.validate_production()` in [`api/overtake/core/config.py`](../api/overtake/core/config.py).
The boot check fails if any of these is wrong:

- `SECRET_KEY` shorter than 32 chars
- `DATABASE_URL` still pointing at SQLite
- `DEBUG` true
- `WEB_BASE_URL` not `https://`
- billing enabled but Stripe keys/prices/webhook secret unset
- `TRUSTED_HOSTS` left as `*`

### API secrets (Fly)

```bash
fly secrets set \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5432/overtake" \
  WEB_BASE_URL="https://overtake.app" \
  API_BASE_URL="https://api.overtake.app" \
  CORS_ORIGINS="https://overtake.app" \
  TRUSTED_HOSTS="api.overtake.app,overtake.app" \
  ANTHROPIC_API_KEY="sk-ant-…" \
  STRIPE_SECRET_KEY="sk_live_…" \
  STRIPE_PRICE_MONTHLY="price_…" \
  STRIPE_PRICE_SEASON="price_…" \
  RESEND_API_KEY="re_…" \
  SENTRY_DSN="https://…"
```

`ENVIRONMENT=production`, `LOG_JSON=true` and `PORT` are already set in
[`fly.toml`](../fly.toml) `[env]`. `STRIPE_WEBHOOK_SECRET` is set in step 7,
once the webhook exists.

### Web env (Vercel)

Set in the Vercel project (Production scope):

| Variable | Value |
|---|---|
| `API_INTERNAL_URL` | `https://api.overtake.app` (server-side only; never exposed to the browser) |
| `NEXT_PUBLIC_SITE_URL` | `https://overtake.app` |

---

## 3. Database

```bash
# From api/, with the PRODUCTION DATABASE_URL exported.
alembic upgrade head
```

Migrations are a **separate, manually approved step** and are deliberately not
in the container `CMD` — an automatic migration on deploy is how a bad migration
takes the site down at the worst moment. Confirm the schema, then start traffic.

A drift test (`tests/unit/test_migrations.py`) already guarantees the single
baseline migration reproduces the models exactly, on both SQLite and PostgreSQL.

---

## 4. API + worker (Fly)

```bash
fly deploy            # builds api/Dockerfile, starts the app + worker processes
fly status            # both processes healthy; API min_machines_running = 1
fly logs              # confirm no boot-validation errors
```

`fly.toml` runs two processes from one image: the API (never scaled to zero) and
a single worker (the jobs table uses `SELECT … FOR UPDATE SKIP LOCKED`, so more
than one would be safe, but one is enough at this scale).

---

## 5. Stripe webhook

1. Stripe Dashboard → Developers → Webhooks → **Add endpoint**.
2. URL: `https://api.overtake.app/api/v1/webhooks/stripe`.
3. Events: `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`.
4. Copy the signing secret (`whsec_…`) → `fly secrets set STRIPE_WEBHOOK_SECRET=…`
   → `fly deploy` (or `fly machines restart`) so the API picks it up.
5. Send a test event and confirm a `200` and one row in `stripe_events`.

Webhooks are signature-verified and idempotent through the `stripe_events`
ledger, so a replayed event is a no-op.

---

## 6. Smoke checklist (run after every production deploy)

- [ ] `curl https://api.overtake.app/api/v1/health` → `200`, `fpl_api: ok`.
- [ ] Landing page loads over HTTPS; `Content-Security-Policy` and
      `X-Frame-Options` headers present; `Server` header absent.
- [ ] Paste a real league ID → board renders with odds.
- [ ] Request a magic link → email arrives → the link **resolves and signs you
      in** (this is the exact flow that once 404'd; verify it every time).
- [ ] Upgrade with a Stripe **test card** in live-mode test, or a real card you
      refund → Pro features unlock → webhook row recorded.
- [ ] Deadline Brief renders (template or AI) with a provenance footer.
- [ ] `robots.txt` disallows `/l/`; the sitemap lists the public SEO pages.

---

## 7. The deadline-day rule

The two hours before a gameweek deadline are peak traffic and peak stakes.

1. Check `/api/v1/health` — `fpl_api` must read `ok`, not `stale`.
2. Confirm simulations are fresh for the most-tracked leagues.
3. **Never deploy within six hours of a deadline.**

---

## 8. Post-launch, before you rely on it

- **Test a restore.** Restore the production backup into a scratch database and
  boot the API against it. An untested backup is not a backup. This is the one
  launch item that cannot be verified from inside the repository.
- Enable Dependabot security updates (the config is committed at
  [`.github/dependabot.yml`](../.github/dependabot.yml); version updates start
  on push, security updates need the repo setting toggled on).
- Confirm the retention sweep worker is running (`fly logs -a overtake` →
  `retention_sweep` entries).

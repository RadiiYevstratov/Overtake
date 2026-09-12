# Deployment runbook

Everything needed to take Overtake from a clean repository to a live product,
in dependency order. Each step names the exact command and the thing to verify
before moving on. Nothing here auto-runs; every external step is deliberate.

This describes the production deployment as it actually runs:

| Piece | Host | Config |
|---|---|---|
| API + worker | Fly.io app `overtake` (London) | [`fly.toml`](../fly.toml), [`api/Dockerfile`](../api/Dockerfile) |
| Web | Fly.io app `overtake-web` (London) | [`web/fly.toml`](../web/fly.toml), [`web/Dockerfile`](../web/Dockerfile) |
| Database | Neon PostgreSQL, `eu-west-2` | [`neon.ts`](../neon.ts) |
| Domain + DNS | `overtakefpl.com`, GoDaddy DNS | — |

Both apps sit in the same region as the database, so a request never crosses
the Channel twice.

---

## 0. Prerequisites (accounts you must own)

1. **Fly.io** account + `flyctl`. For CLI work, put an **org-scoped** token in
   `FLY_API_TOKEN` (Fly dashboard → Tokens). An app-scoped token can deploy but
   cannot add certificates or create tokens, and a login token can be silently
   replaced by one — which is how the CLI lost access repeatedly during setup.
2. **Managed PostgreSQL** 16+ with backups and point-in-time recovery.
3. **Stripe** account (live mode) with two prices: a monthly subscription and a
   one-time season pass.
4. **Anthropic** API key (optional — without it, briefs render from the
   deterministic template, which is a supported mode, not a failure).
5. **Resend** account + a verified sending domain.
6. A **registered domain** you control DNS for.

---

## 1. Dependency order

```text
1. Provision PostgreSQL ─────────┐
2. Create Stripe prices          │  (independent — do in parallel)
3. Get Anthropic + Resend keys   │
   ↓                             │
4. Set API secrets on Fly ◄──────┘
   ↓
5. Deploy the API (do NOT run migrations yet)
   ↓
6. Run `alembic upgrade head` against production (manual, approved)
   ↓
7. Deploy the web app
   ↓
8. Add certificates + DNS for apex, www and api; wait for the certs to issue
   ↓
9. Register the Stripe webhook → set STRIPE_WEBHOOK_SECRET
   ↓
10. Seed at least one league, then run the smoke checklist (§8)
```

Steps 1–3 are independent. From 4 on it is strictly sequential: the web app (7)
needs the API reachable, and the webhook (9) needs `api.<domain>` resolving
with a valid certificate before Stripe will call it.

---

## 2. Configuration

Production **refuses to boot** on a misconfiguration — see
`Settings.validate_production()` in [`api/overtake/core/config.py`](../api/overtake/core/config.py).
It fails if `SECRET_KEY` is under 32 characters, `DATABASE_URL` is SQLite,
`DEBUG` is true, `WEB_BASE_URL` is not `https://`, billing is enabled without
Stripe keys and a webhook secret, or `TRUSTED_HOSTS` is `*`.

### API: runtime secrets

```bash
fly secrets set -a overtake \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  DATABASE_URL="<the provider's DIRECT connection string, pasted as-is>" \
  WEB_BASE_URL="https://overtakefpl.com" \
  API_BASE_URL="https://api.overtakefpl.com" \
  CORS_ORIGINS="https://overtakefpl.com" \
  TRUSTED_HOSTS="overtake.fly.dev,overtake.internal,api.overtakefpl.com" \
  RESEND_API_KEY="re_…" \
  EMAIL_FROM="Overtake <no-reply@overtakefpl.com>" \
  ANTHROPIC_API_KEY="sk-ant-…" \
  STRIPE_SECRET_KEY="sk_live_…" \
  STRIPE_PRICE_MONTHLY="price_…" \
  STRIPE_PRICE_SEASON="price_…" \
  SENTRY_DSN="https://…"
```

`ENVIRONMENT`, `LOG_JSON` and `PORT` are already set in `fly.toml` `[env]`.

Three of those are easy to get subtly wrong:

- **`DATABASE_URL`** — use the provider's *direct* (unpooled) string. Neon's
  pooled endpoint is PgBouncer in transaction mode, and asyncpg's prepared
  statements fail through it under load. Paste the string exactly as the
  provider gives it: surrounding quotes, `sslmode` and `channel_binding` are all
  normalised by the config.
- **`TRUSTED_HOSTS`** — every `Host` header the API legitimately receives:
  `overtake.fly.dev` (the web app's proxy and Fly's health checks),
  `overtake.internal` (Fly's private network) and `api.overtakefpl.com` (Stripe
  webhooks). A missing one makes the API answer `400`, and a health check reads
  that as a dead machine.
- **`EMAIL_FROM`** — must be on a domain verified in Resend. Until it is,
  `Overtake <onboarding@resend.dev>` works but delivers **only** to the Resend
  account owner's own address.

### Web app: build arguments, not secrets

Both values live in [`web/fly.toml`](../web/fly.toml) under `[build.args]` and
are **baked in at build time**:

| Build arg | Value | Why it cannot be a runtime secret |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://overtakefpl.com` | Inlined into the bundle. Canonical URLs, OG tags, `robots.txt`, the sitemap and the host redirects all derive from it. |
| `API_INTERNAL_URL` | `https://overtake.fly.dev` | Next resolves `rewrites()` during the build. A `fly secrets set` value is never read — the proxy silently keeps its localhost default. |

Changing either one means rebuilding (`cd web && fly deploy`), not setting a secret.

---

## 3. Database

```bash
# From api/, with the production DIRECT connection string exported.
alembic upgrade head
```

Migrations are a **separate, manually approved step** and are deliberately not
in the container `CMD` — an automatic migration on deploy is how a bad migration
takes the site down at the worst moment. The drift test
(`tests/unit/test_migrations.py`) guarantees the baseline migration reproduces
the models exactly.

---

## 4. API + worker

```bash
fly deploy -a overtake      # from the repo root; builds api/Dockerfile
fly status -a overtake      # app + worker healthy, all in lhr, one version
fly logs -a overtake        # no boot-validation errors
```

Two processes from one image: the API (never scaled to zero — a cold start two
hours before a deadline is an outage) and a single worker. The Docker build
context is the repository root, which is why `.dockerignore` sits there and
excludes `.env`.

---

## 5. Web app

```bash
cd web
fly deploy                  # builds web/Dockerfile with the args from web/fly.toml
```

- The health check probes `/healthz` with `Host: overtakefpl.com`. Not `/` — the
  landing page renders and calls the API — and not the platform hostname, which
  now answers with a redirect.
- The container `WORKDIR` is `/srv/overtake`, never `/app`: the app has a route
  named `/app`, and rooting the project there made every page inherit the
  signed-in layout and redirect to `/signin`.

---

## 6. Domain and TLS

```bash
fly certs add overtakefpl.com     -a overtake-web
fly certs add www.overtakefpl.com -a overtake-web
fly certs add api.overtakefpl.com -a overtake
fly certs check overtakefpl.com   -a overtake-web   # repeat until "Issued"
```

DNS records at the registrar. Values come from `fly ips list -a <app>`; these
are the current ones:

| Type | Name | Value |
|---|---|---|
| A | `@` | `66.241.125.98` |
| AAAA | `@` | `2a09:8280:1::184:1861:0` |
| CNAME | `www` | `@` |
| A | `api` | `66.241.124.124` |
| AAAA | `api` | `2a09:8280:1::183:3b53:0` |

Remove any parking A records the registrar added, and turn off domain
forwarding — either one overrides these. If the DNS sits behind Cloudflare, set
these records to *DNS only*; its proxy breaks Fly's certificate validation.

Once issued, `www.overtakefpl.com` and `overtake-web.fly.dev` answer `308` to the
apex with the path and query string intact (`redirects()` in
[`web/next.config.ts`](../web/next.config.ts)). One indexed host, and old sign-in
links still resolve.

---

## 7. Stripe webhook

Three things in the dashboard have to exist before checkout works at all, and
each one fails at the moment a user tries to pay rather than at deploy time:

- **Two prices.** Monthly is created with `mode="subscription"` and the season
  pass with `mode="payment"`, so the first must be a **recurring** price and the
  second a **one-time** one. A recurring season price makes checkout fail.
- **Stripe Tax**, enabled with an origin address. Every session is created with
  `automatic_tax={"enabled": True}`.
- **The Customer Portal**, configured. It is the entire billing UI — upgrade,
  card, cancellation — so that none of it is built here and no dark pattern is
  possible in it.

Then the webhook:

1. Stripe Dashboard → Developers → Webhooks → **Add endpoint**.
2. URL: `https://api.overtakefpl.com/api/v1/webhooks/stripe`.
3. Events — all six in `HANDLED_EVENTS`: `checkout.session.completed`,
   `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`.
4. Copy the signing secret (`whsec_…`).
5. Set every billing value in **one** command. `validate_production()` refuses
   to boot when billing is enabled without the keys, so setting
   `BILLING_ENABLED=true` on its own takes the API down:

```bash
fly secrets set -a overtake \
  BILLING_ENABLED="true" \
  STRIPE_SECRET_KEY="sk_live_…" \
  STRIPE_PRICE_MONTHLY="price_…" \
  STRIPE_PRICE_SEASON="price_…" \
  STRIPE_WEBHOOK_SECRET="whsec_…"
```

6. Send a test event and confirm a `200` and one row in `stripe_events`.

Webhooks are signature-verified and idempotent through the `stripe_events`
ledger, so a replayed event is a no-op.

---

## 8. Smoke checklist (after every production deploy)

- [ ] `curl https://api.overtakefpl.com/api/v1/health` → `200`, `database: true`, `fpl_api: ok`.
- [ ] `https://overtakefpl.com` loads; `Content-Security-Policy` and
      `X-Frame-Options` present; no `X-Powered-By`.
- [ ] `https://www.overtakefpl.com` and `https://overtake-web.fly.dev` → `308` to the apex.
- [ ] Paste a league ID → board renders with odds; picking yourself shows rival cards.
- [ ] Request a magic link → email arrives → the link **signs you in**. This flow
      has broken three different ways in production; verify it every time.
- [ ] Upgrade with a real card you refund → Pro unlocks → webhook row recorded.
- [ ] Deadline Brief renders with a provenance footer.
- [ ] `robots.txt` shows `Host: https://overtakefpl.com` and disallows `/l/`.

---

## 9. The deadline-day rule

The two hours before a gameweek deadline are peak traffic and peak stakes.

1. Check `/api/v1/health` — `fpl_api` must read `ok`, not `stale`.
2. Confirm simulations are fresh for the most-tracked leagues.
3. **Never deploy within six hours of a deadline.**

---

## 10. Post-launch, before you rely on it

- **Test a restore.** Restore the production backup into a scratch database and
  boot the API against it. An untested backup is not a backup.
- Enable Dependabot security updates (config committed at
  [`.github/dependabot.yml`](../.github/dependabot.yml)).
- Confirm the retention sweep is running (`fly logs -a overtake` →
  `retention_sweep` entries).
- Rotate `FLY_API_TOKEN` before it expires.

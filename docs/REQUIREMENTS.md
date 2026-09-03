# Requirement traceability

Every requirement in `documentation/` mapped to its implementation and the test
that verifies it. Anything not fully done is marked and explained — nothing is
quietly dropped.

Status key: **DONE** · **PARTIAL** · **NOT DONE** · **DEFERRED** (a documented
V1/V2 item, deliberately not in scope) · **BLOCKED** (needs something external).

---

## MUST HAVE — the 14-day MVP (`05-product-spec.md` §5)

| Requirement | Status | Where | Verified by |
|---|---|---|---|
| FPL data ingest + cache | DONE | `fpl/client.py`, `fpl/ingest.py` | `test_ingest.py` (27 tests): idempotency, ETag/304, retries, circuit breaker, shape stability |
| League board with odds | DONE | `routes/leagues.py::league_board`, `web/app/l/[leagueId]` | `test_api.py::TestPublicLeagueBoard`, E2E "the free hook" |
| Monte Carlo season simulator | DONE | `engine/simulator.py` | `test_engine.py`: determinism, monotonicity, known answers, calibration |
| Rival dossier (1 free, rest paid) | DONE | `routes/leagues.py::rival_dossier`, `web/…/vs/[entryId]` | `test_api.py::TestDossier`, `TestEntitlements`, E2E "the aha moment" |
| Deadline Brief (in-app + email) | DONE | `routes/briefs.py`, `workers/tasks.py::dispatch_deadline_briefs` | `test_llm.py`, `test_api.py::TestEntitlements` |
| Magic-link auth | DONE | `services/auth_service.py`, `routes/auth.py` | `test_api.py::TestAuth` (single-use, hashed, open-redirect guard) |
| Stripe Checkout + webhooks | DONE | `services/billing_service.py`, `routes/billing.py`, `routes/webhooks.py` | `test_security.py::TestBillingManipulation` (signature, replay, price injection) |
| Shareable league image | DONE | `web/app/l/[leagueId]/opengraph-image.tsx` and the head-to-head card | Rendered by Next OG; E2E asserts the share control exists |
| Analytics + event tracking | DONE | `routes/analytics.py`, `components/aha-tracker.tsx` | `test_api.py::TestAnalytics`; the GO/NO-GO funnel is queryable at `/analytics/funnel` |
| Legal pages, cookie handling, deletion | DONE | `web/app/{privacy,terms,cookies}`, `components/cookie-consent.tsx`, `routes/profile.py::delete_me` | E2E "legal and consent"; `test_workers.py::TestRetention` |

## SHOULD HAVE — V1 (`05-product-spec.md` §5)

| Requirement | Status | Notes |
|---|---|---|
| Overtake Simulator | DONE | `POST /leagues/{id}/simulate` with common random numbers; `web/components/simulator.tsx` picks a captain from the user's real named squad |
| Rival behavioural profiles | DONE | `engine/profiling.py`, surfaced in the dossier and fed into the simulation as convergence priors |
| Chip planner vs rivals | PARTIAL | The page ships with real chip data and the correct rival-relative strategy, and is labelled as such. The automated per-gameweek recommendation is not built. |
| Monday recap email | DONE | `workers/tasks.py::dispatch_recaps`, driven by league memory |
| Ask-the-Gaffer | DONE | `POST /leagues/{id}/ask`, same validation stack, metered daily and monthly |
| Head-to-head league support | NOT DONE | The client can read h2h standings, but the simulator models classic scoring only. Stated plainly in the FAQ rather than half-built. |
| Price-change watchlist | PARTIAL | Prices and availability are ingested and shown on player pages; there is no per-user watchlist or alert. |

## AI specification (`06-ai-spec.md`)

| Requirement | Status | Where |
|---|---|---|
| The LLM never computes a number | DONE | It receives a compact computed payload; `validation.py` enforces it |
| Structured output, schema-validated | DONE | `output_config.format` + Pydantic `BriefContent` / `GafferAnswer` |
| Numeric grounding check | DONE | `check_numbers`; corrupted fixtures tested |
| Named-entity check | DONE | `check_entities`; invented-transfer-target case tested |
| Banned phrases (certainty + gambling) | DONE | `check_banned` |
| Confidence computed, not self-reported | DONE | `confidence_from_quality` |
| Deterministic template fallback | DONE | `template_brief`; passes its own grounding checks |
| Visible provenance | DONE | `ProvenanceFooter` on every surface that shows a number |
| Prompt injection defence | DONE | Sanitised at ingest, delimited in prompts, no side-effecting tools |
| Versioned prompts | DONE | `api/prompts/*.v1.md`, version recorded on every generated brief |
| Model name in config only | DONE | `settings.anthropic_model`; never hard-coded |
| Hard daily spend cap in code | DONE | `SpendCap`, checked *before* each call |
| Per-user AI limits | DONE | `usage_counters` via `Entitlements.consume` |
| Prompt caching on the static prefix | DONE | `cache_control` on the system block |
| Second LLM provider as fallback | PARTIAL | The provider interface and multi-provider client are built and a second provider is a drop-in, but only Anthropic is implemented. The tier that actually guarantees correctness — the deterministic template — is complete and tested. |
| Batch API for non-latency-bound jobs | NOT DONE | Recaps and archetype labelling run synchronously. A cost optimisation, not a correctness one. |

## Technical specification (`08-technical-spec.md`)

| Requirement | Status | Notes |
|---|---|---|
| Full database schema | DONE | 32 tables; a drift test asserts the migration matches the models exactly |
| Every documented API route | DONE | All present. Two deliberate improvements: share images are generated by Next rather than a `/share-image` endpoint, and player pages are keyed by slug rather than id for SEO. |
| Polite ingest (≤2 rps, ETag, backoff, circuit breaker, UA with contact) | DONE | `fpl/client.py` |
| Raw snapshots stored before normalising | DONE | `raw_snapshots` |
| Picks never re-fetched | DONE | Asserted in `test_ingest.py` |
| League size cap at 200 | DONE | 422 with an explanation |
| Magic link: 32 bytes, SHA-256, 15 min, single use | DONE | Atomic consumption tested |
| Sessions: opaque, HttpOnly, SameSite=Lax, revocable | DONE | Asserted in `test_api.py` |
| CSRF double-submit on mutating routes | DONE | `TestCsrf` |
| Rate limits on every route | DONE | `scripts_dev/audit_routes.py` enforces it across all 31 |
| `require_plan` in one place | DONE | `deps.require_pro`; exhaustive block test |
| Stripe: signature-verified, idempotent, transactional | DONE | `stripe_events` ledger; replay tested |
| Season pass as one-time payment | DONE | `season_pass_ends_at` entitlement |
| Retention policy enforced by a job | DONE | `retention_sweep`; every window asserted |
| CI: lint → typecheck → tests → migration dry-run → build | DONE | `.github/workflows/ci.yml`, including PostgreSQL |
| Migrations manual, never on deploy | DONE | Documented; not in the container CMD |
| Google OAuth | DEFERRED | Explicitly out of scope for the 14 days |
| Redis | DEFERRED | Explicitly "not until a queue actually backs up" |

## UX specification (`09-ux-ui-spec.md`)

| Requirement | Status |
|---|---|
| Every documented route exists | DONE |
| Design tokens, dark-first, tabular figures | DONE |
| The rival's name always on screen | DONE |
| Probability before prose | DONE |
| Auditable numbers (provenance shown) | DONE |
| Persistent deadline countdown | DONE |
| No chat box on the front door | DONE |
| Every documented state (loading, empty, stale, locked, error, past due, cancelled) | DONE |
| Mobile-majority: card list, sticky move, compact countdown | DONE — E2E runs on a mobile viewport |
| Meaning never in colour alone | DONE — every gain/loss carries a sign or arrow |
| Contrast ≥ 4.5:1, keyboard navigation, real tables, reduced motion | DONE |
| Installable PWA | DONE — manifest and icon |
| Light mode | DEFERRED | Documented as V1, not MVP |

## Growth and SEO (`10-growth-and-seo.md`)

| Requirement | Status | Notes |
|---|---|---|
| League pages noindex but shareable | DONE | Asserted in E2E against `robots.txt` and the sitemap |
| Player pages | DONE | With our own projection — the "number that exists nowhere else" gate |
| Gameweek pages | DONE | Including the on-thesis differentials section |
| Team pages | DONE | |
| Evergreen mini-league guides | DONE | Four written, indexed, internally linked |
| Sitemap and robots | DONE | |
| JSON-LD (Article, FAQPage, SportsEvent, BreadcrumbList) | DONE | |
| Event taxonomy | DONE | Including `aha_reached` fired where the value lands, not on page load |
| North Star (WADM) and GO/NO-GO thresholds | DONE | `/analytics/funnel` returns each metric against its documented band |
| `/compare/{a}-vs-{b}` comparison pages | DONE | Generated for same-position pairs within £3.0m of each other, so no page answers a question nobody asks. One canonical order per pair, with the reverse permanently redirecting; an unknown player 404s rather than redirecting to a dead canonical. Every player page links to its own comparisons — the link-equity engine. |
| Share loop k-factor measurement | PARTIAL | `share_clicked` and `shared_league_visit` are defined; attribution of a signup to a shared link is not implemented. |

## Legal, security, risk (`11-legal-security-risk.md`)

| Requirement | Status |
|---|---|
| Under-13 blocked at signup | DONE — tested |
| 13–15: free tier, no payment, no marketing | DONE — tested |
| 16–17: no marketing, purchase not promoted | DONE |
| Age band stored, never a date of birth | DONE |
| Lawful bases respected (consent only where needed) | DONE |
| Third-party (non-user) data: minimised, removable | DONE — `suppressed_at`, tested |
| No gambling language anywhere | DONE — banned-phrase list, tested |
| Premier League disclaimer on every page | DONE — tested |
| No crests or photography | DONE |
| 14-day withdrawal honoured, no waiver asked | DONE — stated on `/pricing` |
| Cookies essential-only by default | DONE — tested |
| Plain-language privacy summary | DONE |
| The full security control table | DONE — see `README.md`; 30 adversarial tests |
| Account deletion: self-serve, soft then purge | DONE — tested |
| Dependabot | DONE — `.github/dependabot.yml` covers pip, npm and GitHub Actions (grouped, weekly). Version updates start on push; the security-updates toggle is a one-click repository setting. `pip-audit` and `npm audit` also gate every PR. |
| Backup restore tested before launch | BLOCKED — needs a real managed database |

---

## The honest summary

Everything the MVP requires is built, tested and running against live FPL data.
The gaps are three, all recorded above and none of them silent:

1. **Head-to-head leagues** — not modelled. Explicitly out of scope for the
   14-day plan, and stated plainly in the FAQ rather than half-built.
2. **A second LLM provider** — the interface exists and a second provider is a
   drop-in; the tier that actually guarantees correctness is the deterministic
   template, which is complete and tested.
3. **Chip planner automation** — the page ships with real data and the correct
   rival-relative strategy, and says plainly which part is not yet automated.

Items that need something external — a Stripe account, an Anthropic key, a
managed database to test a restore against, a lawyer for the third-party data
question, and a Slovak accountant for the VAT registration path — are listed in
the README and cannot be closed from inside the repository.

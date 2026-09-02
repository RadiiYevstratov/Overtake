# Legal, security, failure analysis and moat

---

## 1. Legal

### 1.1 The age question — decided, not guessed

The brief's audience starts at 15, so this must be resolved explicitly.

**The rule.** Under GDPR Art. 8, an information-society service offered directly
to a child and relying on **consent** as its lawful basis needs parental
authorisation below the "age of digital consent". The GDPR default is 16, and
member states may lower it to as low as 13. The result is a genuine patchwork —
Germany, the Netherlands and Ireland at **16**; France at **15**; Spain and Italy
at **14**; Belgium and Sweden at **13**. **[verified]** Additional obligations
apply regardless of age: verify age with effort proportionate to risk, avoid
profiling and automated decision-making on children's data, no marketing without
parental consent, and privacy information written in language a child can
actually read. **[verified]**

Separately, the UK's Age Appropriate Design Code (Children's Code) applies to
services likely to be accessed by under-18s in the UK — and a school FPL league is
squarely that. It requires high-privacy defaults, data minimisation, no nudge
techniques toward weaker privacy settings, and a Child Rights Impact Assessment.

**The decision for Overtake:**

| Group | Access | Why |
|---|---|---|
| **Under 13** | Not permitted. Declared age under 13 blocks account creation. | Below every member state's floor; no viable consent path for a solo operator. |
| **13–15** | **Free tier only. No payment. No marketing email. No behavioural profiling of them as a subject.** Full product features that operate on public FPL data are available. | Avoids relying on consent for a minor by (a) not doing the things that need consent and (b) not taking their money. |
| **16–17** | Free tier plus, where permitted, paid — **but paid access is deliberately not promoted to this group**, and no marketing email regardless. | 16 clears the digital-consent bar everywhere in the EEA. Payment by a minor still raises contract-capacity questions country by country, so we do not chase it. |
| **18+** | Everything. | — |

**Mechanism.** A neutral date-of-birth entry at signup (not "are you over 18?",
which invites a lie), stored only as an `age_band` enum — never the date itself.
The user's own age is not retained as a value. This is deliberate: it is the
minimum data that satisfies the obligation.

**Lawful bases used.** Contract (Art. 6(1)(b)) for delivering the service to a
signed-up user; legitimate interests (Art. 6(1)(f)) for security, abuse prevention
and aggregate product analytics, with a documented balancing test; consent
(Art. 6(1)(a)) only for marketing email and non-essential analytics cookies —
which is precisely why the under-16 tier is built to need neither.

**Third-party data.** The product processes public data about **rivals who are not
users** (team names, squads, standings). This is personal data where a person is
identifiable. Handling: legitimate interests, minimised to what the FPL site
already displays publicly, never enriched, never used for marketing, never sold,
deleted on request, and covered by a clear notice in the privacy policy explaining
how a non-user gets their data removed. **This is the sharpest legal edge in the
product and it should be reviewed by a lawyer before launch.**

### 1.2 Gambling — the bright line

FPL is a free-to-enter game of skill with no stake. Overtake sells analysis of it.
That keeps it outside gambling regulation — **provided it stays there**. Hard
rules, treated as product constraints, not guidelines:

- No odds in betting formats. Probabilities are expressed as percentages against
  named rivals, never as prices.
- No stakes, pots, prize pools, or facilitation of league buy-ins.
- No bookmaker affiliate links, no betting-adjacent sponsorship, no "value bet"
  language, ever.
- No integration with, or promotion of, DFS or betting products.

Crossing this line would trigger UK Gambling Commission scope, destroy the ability
to advertise, and make the product inappropriate for the 15–17 users it serves.

### 1.3 Platform and intellectual property

- **The FPL API** is public and unauthenticated but **undocumented and
  unlicensed**. There is no grant. Mitigation: aggressive caching, polite rate
  limiting, a descriptive User-Agent with contact details, no account
  authentication, no write operations, and a documented willingness to comply
  immediately with any request from the Premier League. Build the ingest behind an
  interface so a manual-import fallback can be swapped in. **Risk rating: serious,
  not critical** — a decade-old third-party ecosystem exists, but nothing is
  promised.
- **Trademarks.** "Fantasy Premier League", "Premier League" and club marks are
  owned. Use them descriptively only ("for Fantasy Premier League"), never in the
  brand, logo, domain, or app name. Carry a prominent "not affiliated with or
  endorsed by the Premier League" disclaimer in the footer and on the landing page.
- **Player names and stats** are facts, freely usable. **Player images and club
  crests are not** — the product uses no photography and no crests, only text and
  generated abstract marks. This also happens to suit the design direction.

### 1.4 Consumer and tax

- **Withdrawal right.** EU/UK distance selling grants 14 days for digital
  services. We do not ask users to waive it; refunds are honoured on request.
- **Terms and Privacy** must be plain-language, with a separate one-page "what we
  collect and why" summary written for a 15-year-old to understand.
- **Cookies.** Essential-only by default. PostHog is loaded **only after consent**;
  without consent, server-side aggregate counting is used instead.
- **VAT.** B2C digital services to EU consumers are taxed where the customer is.
  Register for the **EU VAT One-Stop-Shop** (or the non-Union scheme as applicable
  to the trading entity), and register for **UK VAT** for UK B2C digital supplies —
  the UK has no registration threshold for non-established suppliers of digital
  services. Stripe Tax handles calculation and evidence collection; filing is the
  founder's obligation. **Confirm the exact registration path with a Slovak
  accountant before the first sale** — this is the one legal item that cannot be
  deferred.
- **AI disclosure.** State plainly, in-product, that briefs are AI-generated from
  simulation output, that projections are estimates, and that this is not advice
  of any regulated kind.

---

## 2. Security

| Area | Control |
|---|---|
| **Authentication** | Magic links only; 32-byte tokens hashed with SHA-256 at rest; 15-min expiry; single use; consumed atomically. No passwords exist, so no password can leak. |
| **Sessions** | Opaque tokens, `HttpOnly; Secure; SameSite=Lax`, 30-day rolling, server-side revocable, invalidated on email change |
| **Authorisation** | Every request re-checks ownership *and* entitlement server-side via one shared dependency. Frontend state is never a gate. |
| **Rate limiting** | Per-IP and per-user token buckets on every route (limits in `08-technical-spec.md` §5); stricter on auth and LLM routes; 429 with `Retry-After` |
| **API security** | Strict Pydantic validation on every input; integer IDs range-checked; no user-supplied SQL, ORM parameters only; CORS locked to our own origins |
| **XSS** | React auto-escaping; no `dangerouslySetInnerHTML`; a strict CSP with nonces; **all rival team names treated as hostile input** — they are free text set by strangers |
| **CSRF** | `SameSite=Lax` plus double-submit token on all mutating routes |
| **SQL injection** | Parameterised queries only; zero string-built SQL |
| **Prompt injection** | Team/league names delimited and labelled as untrusted data in prompts; LLM has no side-effecting tools; output validated against a schema and a grounding check before display (`06-ai-spec.md` §6–7) |
| **AI abuse** | Per-user daily caps; a **hard global daily spend cap enforced in code**; abusive-input logging; automatic fallback to deterministic templates when caps are hit |
| **Payments** | Stripe Checkout — no card data touches our infrastructure. Webhooks signature-verified and idempotent via `stripe_events`. |
| **Secrets** | Platform secret store only; never in the repo; documented rotation runbook; `.env.example` with no real values |
| **Data protection** | TLS everywhere; encryption at rest via the managed DB; PII limited to email + optional display name + age band; no birth dates, no addresses, no phone numbers |
| **Backups** | Daily managed backups, 7-day PITR, weekly off-platform dump to R2, **restore tested before launch** |
| **Logging** | Structured JSON; emails and tokens redacted at the logger; 30-day retention; access logged |
| **Account deletion** | Self-serve, immediate soft delete, hard purge within 30 days, including LLM logs. A one-click export accompanies it. |
| **Dependencies** | Dependabot; `pip-audit` and `npm audit` in CI; lockfiles committed |
| **Incident response** | A written one-page plan: contain, assess, notify the supervisory authority within 72 hours if personal data is affected, notify users, post-mortem |

---

## 3. Failure analysis — how this dies

Ranked. Each with the honest probability judgement and the mitigation.

### CRITICAL

**1. Nobody pays, because the analysis is entertainment rather than a purchase.**
The most likely way this fails. FPL managers enjoy *arguing about* decisions; a
tool that hands them the answer may remove the pleasure rather than deliver value.
The free mini-league analysers all being free is a warning sign, not just an
opening. *Mitigation:* the entire 14-day plan is built to test this and nothing
else, with a hard NO-GO at day 13. Do not build V1 before this is answered.

**2. Acquisition never gets past the first 200.** With no budget, if the Reddit
post lands flat and the share loop has a k-factor near zero, there is no plan B
that a solo founder can afford. *Mitigation:* validate the share loop before
building anything paid; measure k-factor from week one; treat SEO as the fallback
plan with an honest 6–9 month lag.

### SERIOUS

**3. The FPL API is restricted or breaks.** No licence, no promise, no notice
period. *Mitigation:* caching, politeness, degradation mode, manual-import
fallback, and an ingest interface that permits a second source.

**4. Seasonality kills momentum.** Ten weeks of near-zero revenue and engagement
each summer, in a business too young to have reserves. *Mitigation:* season-pass
pricing as the default; treat June–July as the build window; V2 adds Champions
League Fantasy to fill the calendar.

**5. Projection quality is visibly worse than incumbents'.** Without Opta data,
our expected-points numbers will be beaten by Fantasy Football Scout's, and users
will notice. *Mitigation:* never compete on that axis; publish measured error
openly; make it explicit that projections are an input and rival-relative
simulation is the product. Honesty here is a differentiator, not a weakness.

**6. An incumbent ships a rival module.** Fantasy Football Scout already bundles a
mini-league product; adding simulation is a quarter of work for them. *Mitigation:*
speed, focus, and the fact that a rival-first product cannot be a feature inside a
global-rank product without confusing their core offer. This buys time, not safety.

### MANAGEABLE

**7. AI hallucinates a number and a user acts on it.** Reputationally severe in a
numerate community. *Mitigation:* the grounding check, structured output, and
template fallback in `06-ai-spec.md` — the model is architecturally unable to
originate a number.

**8. Runaway LLM costs.** *Mitigation:* hard in-code daily spend cap; per-user
limits; caching at the league grain.

**9. Third-party (non-user) personal data complaint.** *Mitigation:* minimisation,
a documented removal path, legal review before launch.

**10. Trademark contact from the Premier League.** *Mitigation:* descriptive use
only, disclaimers, no crests or photography, immediate compliance if contacted.

### LOW

**11. Technical complexity.** The stack is deliberately small; the hardest
component is 200 lines of NumPy.
**12. Market size.** 13.1M managers is more than sufficient at these price points.
**13. Legal/gambling.** Fully avoidable by following §1.2, which costs nothing.

---

## 4. Competitive moat — an honest assessment

**What is not a moat:** the simulation maths (any competent developer can build a
Monte Carlo engine in a week), the FPL API (public to everyone), the LLM layer
(commodity), and the UI (copyable in a fortnight).

**What could become a moat, in descending order of credibility:**

1. **Accumulated league memory.** Every gameweek, the product records what each
   rival did. After one season, Overtake holds behavioural histories for every
   manager in every tracked league — data that cannot be back-filled by a
   competitor arriving later, because the FPL API exposes current-season detail but
   the *derived behavioural model* is ours. This is a genuine, time-based asset.
   Strength: **medium-high, and it compounds.**
2. **The league graph.** Products anchored to a group of named friends are sticky
   in a way single-player products are not: switching costs the whole group's
   shared reference point. Strength: **medium.**
3. **Category positioning.** Being *the* mini-league product, in a market where
   everyone else is the global-rank product, is a brand position that gets harder
   to take the longer it is held. Strength: **medium, entirely execution-dependent.**
4. **Programmatic SEO.** ~2,900 pages accruing authority. Slow, real, and copyable
   — but with a lead time a follower must also pay. Strength: **low-medium.**
5. **Discord/group-chat distribution.** Once the bot is posting into a league's own
   server, the product is embedded in the group's ritual. Strength: **medium, but
   unbuilt.**

**The honest summary:** on day one there is **no moat**. There is a wedge — a
different objective function — and roughly a 6–12 month head start before anyone
who cares could copy it. The moat, if it exists, is built by shipping for a full
season and accumulating league memory that a fast follower cannot retroactively
acquire. Anyone who tells this founder there is a defensible moat at launch is
selling something.

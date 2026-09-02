# Market research

## 1. The macro picture: what 15–35-year-olds actually pay for

Three findings shaped every decision downstream.

**a) The paying behaviour is real, but it is fickle.**
Gen Z is now the strongest cohort in the subscription economy by spend growth,
and reporting on Visa's subscription data credits them with tripling the
subscription spend of older generations. **[verified — see sources]** Separately,
eMarketer reports Gen Z has the highest willingness to pay for websites, apps and
online services of any generation. But Recurly's work on the same cohort frames
their habits as "a double-edged sword": high acquisition, high cancellation.
The strategic reading: *this audience will start a subscription easily and end it
just as easily. The product must be defended by something structural, not by
novelty.*

**b) AI apps monetise better and retain worse.**
RevenueCat's 2026 State of Subscription Apps (115,000+ apps, ~$16bn combined
revenue) reports:

- AI apps: **$30.16 median Year-1 realised LTV** vs **$21.37** for non-AI — a 41%
  revenue premium.
- **AI monthly plans retain 36% worse over 12 months** than traditional apps.
- **72% of annual subscribers cancel within Year 1**, worsened from 56% the prior
  year.
- Hard paywalls convert ~5x better than freemium at Day 35 (10.7% vs 2.1%) and
  produce ~8x the revenue per install, yet 12-month retention is statistically
  identical (27% vs 28%).
  **[verified]**

This is the single most important number in this document. It says: *the
generation-novelty business model is already burning out.* A product whose only
mechanism is "AI makes a thing" gets a price premium and then churns. The
defensible shape is a product where (i) an external clock forces return, and
(ii) the user's accumulated data makes the product better over time.

**c) The consumer AI market is consolidating upward.**
a16z's Top 100 Gen AI Consumer Apps (March 2026) shows ChatGPT at ~900M weekly
actives and standalone image generation collapsing from 7 of 9 creative tools in
2023 to 3, as bundling into ChatGPT and Gemini compressed standalone traffic.
**[verified]** The lesson for a solo founder: *anything a general assistant can
absorb, it will absorb.* Survivors on that list are products the general models
cannot bundle — because they own data (Notion), a specialised model (Suno,
ElevenLabs), or a workflow.

### What this implies for opportunity selection

A winning opportunity must have **all** of:

1. An **external clock** that forces return on a schedule the founder does not
   control (a fixture list, a posting schedule, a market open).
2. **Accumulating personal data** so month 6 is better than month 1.
3. A **legal, free or cheap live data source** — because the budget is €50–200.
4. An objective a general chatbot **cannot compute**, not merely one it answers badly.
5. A **paid market that already exists** at a higher price point, so pricing is a
   known quantity rather than a hope.

---

## 2. Where the 11 value mechanisms are actually underserved

Mapping the current consumer AI landscape against the eleven mechanisms:

| Mechanism | State of the market | Opportunity |
|---|---|---|
| Entertainment | Saturated; general models + short-form video own it | Low |
| Curiosity | Strong but shallow — one-shot novelty, no return | Medium, only if paired with a clock |
| Convenience | Being absorbed by assistants and OS-level agents | Low |
| **Status** | **Thinly served by AI. Almost every AI product sells private utility, not public standing.** | **High** |
| Personalisation | Claimed everywhere, real rarely (most is a system prompt) | High where real data backs it |
| **Social interaction** | AI products are overwhelmingly single-player | **High** |
| Self-expression | Well served (creator tools, image/video gen) | Low |
| Anxiety reduction | Served in health/finance; underserved in "did I just make a mistake" | Medium–High |
| **Better decisions** | Served with *information*, rarely with *a computed recommendation under your specific constraints* | **High** |
| Saved time | Commoditised | Low |
| Reason to return | **The weakest link in the whole category** — see the RevenueCat retention data | **Highest leverage** |

The three columns marked high — status, social, better decisions — plus a hard
external clock, define the shape of the winner before any specific idea is chosen.

---

## 3. Candidate market probes and what the evidence said

### 3.1 Fantasy football (selected)

- **Scale:** FPL grew from 76,200 managers (2002/03) to **11.45M (2022/23)** and
  **13.10M (2025/26)**. **[verified]**
- **Structure:** ~38 gameweeks, one free transfer per week (rollable to five),
  −4 point hits for extra transfers, eight chips across the season in two sets of
  four, and private mini-leagues in classic or head-to-head format. **[verified]**
- **2026/27 changes:** chip allocation unchanged (two sets, first expiring at the
  GW19 deadline, 2 January 13:30 GMT); defensive-contribution scoring retained;
  Bonus Points System retuned; gameweek lockdown moved to 09:00 UK the day after
  the final match; and the Premier League shipped its **own official Price Change
  Predictor**, plus a Rookie League and squad-view toggles. **[verified]**
- **Proven willingness to pay:** Fantasy Football Scout — £10/month, **£50/year**,
  or a £100/year Mega Bundle; free "Assistant Scout" tier. Fantasy Football Hub —
  Starter/Pro/Ultra tiers with a **"win your mini-league or get your money back"
  guarantee**, AI team rating, Opta statistics, predicted-points models, and an
  Ultra tier with WhatsApp access to the founder and monthly Zoom reviews.
  **[verified]**
- **The gap:** mini-league tooling exists but is almost entirely free and
  descriptive — Premier Fantasy Tools' Mini League Analyzer, FPL Core, Fantasy
  Football Pundit's mini-league stats tool, FPL Toolbox, and Mini League Mate
  (a Patreon-funded newsletter). **[verified]** None of them simulate outcomes;
  they report ownership, differentials and standings. The paid tools, meanwhile,
  sell projections against the global field. **The intersection — a paid,
  rival-relative decision engine — is empty.**
- **Data access:** the official FPL API is public and unauthenticated for
  everything required: `bootstrap-static/`, `fixtures/`,
  `element-summary/{id}/`, `event/{id}/live/`, `entry/{id}/`,
  `entry/{id}/history/`, `entry/{id}/event/{gw}/picks/`, and
  `leagues-classic/{id}/standings`. Only `my-team/{id}/` requires auth.
  **[verified]** This means every rival's squad is legally readable for free.
  **Live check, 31 August 2026:** `GET /api/event-status/` returned valid JSON with
  no authentication and no block, showing the season currently at gameweek 2 —
  the API is up, open, and the season has just started. **[verified directly]**
- **Note on the PL's own Price Change Predictor:** this is the clearest possible
  signal that *descriptive* features get commoditised by the platform. It
  strengthens rather than weakens the thesis, because the platform will never
  build a tool that helps one manager beat another — that would be seen as
  favouritism.

### 3.2 Second-hand marketplace seller tools (rejected, ranked #2)

- **Scale:** Vinted grew from 30M registered users (2019) to **105M (2023)**, with
  **€596M revenue in 2023** (+60.9%) and a first annual profit of €17.8M; 20
  markets; 800M+ items listed. **[verified]**
- **Demand and willingness to pay are the strongest in the entire longlist** —
  income-motivated users pay for tools that make them money.
- **Why it was rejected:** no public API, comparables require scraping, and
  Vinted actively restricts and bans accounts for automation — an entire content
  genre exists around "Vinted account blocked for automation". **[verified]** The
  business would sit one enforcement decision away from zero, and at least five
  competing tools already occupy the space. Platform risk is **critical**, not
  manageable.

### 3.3 Short-form creator tooling (rejected, ranked #4)

- Real and proven WTP: 1of10 sells Free / **$29** / **$69** monthly tiers; vidIQ
  runs Free / Boost / Max plans in a comparable band. **[verified]**
- The YouTube Data API is free and legal, which solves data access.
- **Why it was rejected:** this is textbook *undifferentiated* competition —
  vidIQ, 1of10, Spikes, OutlierKit, TubeLab and others already do outlier
  detection and AI ideation, several with far more capital. A solo founder's
  wedge would have to be brand or niche, neither of which is a moat.

### 3.4 Chess and esports improvement (rejected)

- The chess-improvement niche is now crowded with near-identical small products
  (Chessy, CheckmateX, ChessDNA, ChessDock, CircleChess, Improve My Chess), and
  Chess.com acquired Aimchess and bundles improvement analytics into its own
  membership. When the platform owns the category, a third party is a feature.
- League/Valorant coaching is dominated by free incumbents (op.gg, Blitz,
  Mobalytics, Porofessor) with entrenched habits and overlays. Differentiation
  score: 3/10.

### 3.5 Fitness and study (rejected)

- Fitness is a price war fought in SEO: Fitbod, Hevy, Strong and a long tail of
  clones publishing comparison pages against each other. **[verified from the
  shape of the search results themselves]**
- Edtech for this age group is capitalised: Knowunity raised **€27M** to scale an
  AI tutor. **[verified]** A solo founder is not the right vehicle.

---

## 4. Workaround evidence (Section 12 of the brief)

Evidence that FPL managers already do this work manually, badly:

- **Spreadsheets.** Manual transfer planners and fixture tickers are a genre; the
  paid tools' headline features are literally "transfer planner" and "fixture
  ticker with rotation planning", which exist because people were doing it in
  Excel. **[verified]**
- **Screenshotting rivals' teams.** The FPL site lets you view any rival's squad
  after the deadline; comparing it against your own is a manual click-and-compare
  loop repeated for every rival, every week.
- **Group chats.** Mini-league banter, chip announcements and bluffing happen in
  WhatsApp/Discord, entirely outside any tool.
- **ChatGPT.** Managers paste squads into general assistants and get answers that
  are confidently wrong, because the model has no live prices, no injury news,
  and no knowledge of the rival's team.
- **Free mini-league analysers.** The existence of at least five free tools doing
  descriptive mini-league stats is proof the need is felt — and proof that nobody
  has yet made it worth paying for.

## 5. Competitor complaint patterns

Searching the space surfaces recurring shapes of complaint rather than a single
loud one. The honest summary:

- "Too expensive" — £50–100/year is a real barrier for a student audience; the
  Mega Bundle at £100/year is priced for enthusiasts, not for a 19-year-old in a
  university league.
- "Everyone gets the same advice" — projection-led tools converge on the same
  template team, which is *actively counterproductive* in a mini-league where
  copying the field guarantees you cannot gain ground.
- "I don't care about my global rank" — the paid market's core metric is not the
  metric most users emotionally track.

**[insufficient evidence]** on quantified churn, subscriber counts or revenue for
Fantasy Football Scout, Fantasy Football Hub, Fantasy Football Fix or LiveFPL.
None of these companies publish it and no credible third-party estimate was
found. Every business-size claim about them in this document is therefore absent
rather than estimated.

## 6. Geographic market decision

**Chosen: United Kingdom first, then English-language international
(Ireland, Nordics, Netherlands, Gulf, India, Singapore, Australia, North America).**

Rationale:

- **Demand:** FPL's centre of gravity is the UK, and it is where mini-league
  culture (office leagues, pub leagues, school leagues) is densest.
- **Purchasing power and payment rails:** high card penetration, and Stripe
  supports both the UK market and a Slovak-registered seller, so the founder's
  own jurisdiction is not a blocker. VAT on B2C digital services is handled
  through the EU One-Stop-Shop and a UK registration once thresholds apply
  (see `11-legal-security-risk.md`).
- **Language:** English only at launch — zero localisation cost, and FPL's
  international player base already plays in English.
- **Competition:** the incumbents are UK-based, but they are competing on a
  different axis (projections), so co-location is not a disadvantage.
- **Regulatory:** FPL is a free-to-enter skill game with no stake. Overtake sells
  analysis of it. **It is not gambling and must never drift toward it** — no odds,
  no stake, no cash prizes, no affiliate links to bookmakers. That single rule
  keeps the product out of UK Gambling Commission scope and out of the
  advertising restrictions that come with it.

---

## Sources

- [Fantasy Premier League — Wikipedia (registered managers by season, game structure)](https://en.wikipedia.org/wiki/Fantasy_Premier_League)
- [Premier League — All you need to know about changes to FPL for 2026/27](https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627)
- [Fantasy Football Scout — Pricing](https://www.fantasyfootballscout.co.uk/pricing)
- [All About FPL — Complete & detailed review of Fantasy Football Hub](https://allaboutfpl.com/2026/08/complete-detailed-review-of-fantasy-football-hub/)
- [Fantasy Premier League API endpoints: a detailed guide](https://medium.com/@frenzelts/fantasy-premier-league-api-endpoints-a-detailed-guide-acbd5598eb19)
- [Premier Fantasy Tools — FPL Mini League Analyzer](https://www.premierfantasytools.com/fpl-mini-league-analyzer/)
- [Mini League Mate](https://www.minileaguemate.com/)
- [RevenueCat — State of Subscription Apps 2026](https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026)
- [a16z — Top 100 Gen AI Consumer Apps, March 2026](https://www.a16z.news/p/top-100-gen-ai-consumer-apps-march)
- [Visa — Gen Z boosts subscription economy, tripling spend from older generations](https://corporate.visa.com/en/sites/visa-perspectives/trends-insights/gen-z-boosts-subscription-economy-tripling-spend-from-older-generations.html)
- [eMarketer — Gen Z is willing to pay more than any other generation for websites and apps](https://www.emarketer.com/content/gen-z-will-pay-most-for-websites-apps-online-services)
- [Recurly — Gen Z's subscription habits: a double-edged sword](https://recurly.com/press/gen-z-fickle-subscription-habits-a-double-edged-sword-for-subscription-services/)
- [Business of Apps — Vinted revenue and usage statistics](https://www.businessofapps.com/data/vinted-statistics/)
- [Redrip — Vinted account blocked for automation](https://www.redrip.app/en/blog/vinted-automation-restriction-2026/)
- [1of10 — Pricing explained: Free, Basic $29, Pro $69](https://1of10.com/blog/1of10-pricing/)
- [Tech.eu — Knowunity raises €27M to scale its personalized AI tutor globally](https://tech.eu/2025/06/13/knowunity-raises-eur27m-to-bring-ai-tutor-to-1-billion-students/)
- [GDPRWise — GDPR and children: extra rules for minors' personal data](https://gdprwise.eu/en/kennisbank/verplichtingen/gdpr-children-data/)
- [Stripe — How to accept payments in Slovakia](https://stripe.com/resources/more/payments-in-slovakia)

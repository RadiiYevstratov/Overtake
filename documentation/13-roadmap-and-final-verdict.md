# Roadmap and final verdict

## 1. Validation plan

Sequenced so the cheapest, most falsifying experiment runs first.

| # | Experiment | Cost | Duration | Measures | GO threshold |
|---|---|---|---|---|---|
| 0 | **Concierge test — before writing code.** Manually analyse 10 strangers' mini-leagues in a Reddit thread and write the dossier by hand. | €0 | 2 days | Does anyone care? | ≥ 10 people post their league ID unprompted |
| 1 | **Fake-door pricing.** The landing page with a real price and a "Notify me" capture behind the checkout button. | €12 (domain) | 1 week | Price acceptance | ≥ 5% of visitors click through to the price |
| 2 | **The 14-day MVP beta.** | €0–15/mo | 2 weeks | The full funnel | See `12-mvp-14-day-plan.md` |
| 3 | **The r/FantasyPL launch.** | €0 | 1 day | Channel viability | ≥ 500 unique visitors, ≥ 100 league IDs pasted |
| 4 | **Share-loop measurement.** | €0 | 4 weeks | k-factor | ≥ 0.2 by week 4 |
| 5 | **Season-pass vs monthly split test.** | €0 | 4 weeks | Plan mix, revenue per visitor | Season pass ≥ 40% of purchases |
| 6 | **Retention cohort over 6 gameweeks.** | €0 | 6 weeks | Habit formation | ≥ 35% of paid users active in ≥ 5 of 6 gameweeks |

Experiment 0 is the one most likely to be skipped and the one most worth doing.
It costs two days and can kill the idea before a line of code exists.

---

## 2. Roadmap

### MVP — 2 weeks
Ingest · projections v0 · Monte Carlo simulator · public league board · rival
dossier · magic-link auth · Stripe · Deadline Brief · share images · analytics ·
legal. **Goal: answer the payment question.**

### V1 — months 1–2 (after a GO)
Prioritised by business impact ÷ effort:

| Feature | Impact | Effort | Ratio | Why |
|---|---|---|---|---|
| Overtake Simulator | High | Medium | **High** | The single most requested follow-up to the dossier; converts curiosity into engagement |
| Monday recap email | Medium | Low | **High** | A second weekly re-entry point for almost no work |
| Programmatic SEO (players + comparisons) | High | Medium | **High** | The only compounding free channel; 8–12 week lead time means starting late costs a season |
| Rival behavioural profiles surfaced in-product | Medium | Low | **High** | The moat, made visible |
| Ask-the-Gaffer | Medium | Medium | Medium | Handles the long tail; also the biggest cost centre — gate it |
| Chip planner vs rivals | High | High | Medium | The highest-stakes decision of the season, but complex |
| Head-to-head league support | Medium | Medium | Medium | An entire format currently unserved by anyone |
| Google OAuth | Low | Low | Medium | Removes email-deliverability risk |

### V2 — months 3–6
- **UEFA Champions League Fantasy** — the seasonality fix, and it reuses the whole
  engine.
- **Discord bot** posting weekly odds into a league's own server. Highest-leverage
  distribution build in the entire roadmap.
- **League Pass** SKU (one admin pays for the league).
- Multi-league dashboard for the 4+ league power users.
- Public data study for backlinks.
- Regional pricing.
- Light mode, PWA polish.

### Long term — months 6–24
- **Other fantasy formats with public state and private leagues**: World Cup 2026
  aftermath and Euro 2028 fantasy, NFL, cricket. The rival-relative simulation is
  the asset; FPL is only the first market for it.
- **Draft-league support** — a structurally different and harder problem, and
  almost completely unserved.
- **A published accuracy record.** Two seasons of public, auditable calibration
  ("when we said 26%, it happened 25% of the time") would be the most credible
  marketing asset in the category and something no incumbent currently offers.
- Only then: a native app, and only if PWA data proves it is needed.

**What is deliberately never on this roadmap:** betting integration, a social
feed, automated transfers, and a general-purpose FPL chatbot.

---

## 3. Final verdict — the twelve answers

### 1. Should this product be built?
**Yes — as the 14-day MVP defined in `12-mvp-14-day-plan.md`, and not one day
more before the GO/NO-GO is run.** The commitment being recommended is two weeks
and roughly €30, not a company.

### 2. Why?
Because it is the only opportunity of thirty that combines a proven paying market,
free legal live data, an objective function no competitor optimises, retention
supplied by an external calendar, an intrinsic viral loop, and a two-week build —
inside a €50–200 budget. Its weighted score (7.72) leads the field by a margin
larger than the gap between second and sixth place.

### 3. Why would someone pay?
Because £50/year is the going rate in this market and this product is €29.99, and
because it answers the question the expensive tools do not: not "what maximises my
points" but "what does it take to finish above Dan". People do not frame a global
rank; they argue with their friends for ten months.

### 4. Why would someone return?
Because the Premier League publishes ~38 deadlines a year, and every one of them
changes the answer. Daily: price changes and injury news on rival-owned players.
Weekly: the deadline. Monthly: chip windows. Seasonally: the story ends and
another begins. The retention mechanism is not a feature that can wear off.

### 5. What is the primary human motivation?
Status inside a small, named, permanent peer group. Not achievement, not
self-improvement — social standing among people whose opinion is unavoidable.

### 6. Which of the 11 value mechanisms is strongest?
**Status**, with **reason to return** as the structural enabler. Better decisions,
anxiety reduction and curiosity are supporting mechanisms, not the engine.

### 7. What is the biggest risk?
That the analysis turns out to be *entertainment* rather than a *purchase* — that
mini-league players enjoy arguing about the decision more than being handed it.
Every free mini-league tool on the market being free is evidence that should be
taken seriously, not explained away.

### 8. What is the biggest opportunity?
The engine generalises. Rival-relative simulation works for any fantasy format
with public state and private leagues. FPL is the beachhead, and expansion is also
the fix for the product's worst structural flaw, seasonality.

### 9. What must be validated first?
That a mini-league player will pay for rival-relative advice — and, before even
that, the two-day concierge test: will strangers hand over their league ID at all?

### 10. What should NOT be built?
A competing points-projection model. Anything touching odds, stakes or bookmakers.
Automated transfers or any write access to FPL accounts. A native app in year one.
A social feed. A chatbot as the front door. Unlimited free simulation.

### 11. What would make you abandon the idea?
Any of these, individually:
- The concierge test produces fewer than 10 volunteered league IDs.
- Aha rate below 25% **and** return rate below 25% in beta — the premise is wrong.
- Zero paid conversions after two distinct paywall/pricing attempts — this is a
  free tool with an ad model, not a subscription business, and that is not the
  business being proposed here.
- The Premier League restricts API access with no workable fallback.
- Any incumbent ships a genuine rival-relative simulator before launch. Being
  second with the same idea and 1% of the distribution is not a business.

### 12. What evidence would prove the product is working?
In order of increasing weight:
1. Strangers pasting league IDs without being asked.
2. Share rate ≥ 15% on rival dossiers, with shares arriving from leagues that
   contain no existing user — the loop closing on its own.
3. **Weekly Active Deciding Managers** (the North Star) growing gameweek over
   gameweek, with ≥ 35% of paid users active in 5 of any 6 gameweeks.
4. Free→paid conversion holding at ≥ 3% across three separate acquisition cohorts,
   not just the founder's friends.
5. Season-pass share above 40%, which proves users are buying a *season*, not
   trying a novelty.
6. And the one that matters most, arriving in August 2027: **season-over-season
   renewal above 50%.** Everything before that is a promising start. That number
   is the business.

# Top 3 and the winner

Scores: **Overtake 7.72 · Seller copilot 6.99 · Co-DM 6.98** (creator engine 6.95,
a fourth-place miss narrow enough to be noise — it is eliminated on judgement,
not on arithmetic: see the elimination log).

---

## Finalist 1 — Overtake (FPL rival-aware decision engine) · 7.72

**Market.** Fantasy Premier League: 13.10M registered managers in 2025/26, up
from 11.45M in 2022/23. A paid tooling market already exists at £50–100/year.

**Audience.** 18–30, male-skewing, in a mini-league of 5–30 named people. FPL's
social unit is not the individual — it is the league.

**Human motivation.** Status inside a permanent peer group. The scoreboard runs
for ten months and the group chat never forgets.

**Core value mechanism.** Status. Secondary: better decisions, anxiety reduction,
curiosity, reason to return.

**Problem/desire.** Every tool on the market optimises expected points against
the global field. That answer is *actively wrong* for a mini-league player who is
behind: copying the template team locks in your deficit. What they need is
P(finish above rival X), and the variance strategy that maximises it.

**Existing solutions.** Paid: Fantasy Football Scout (£10/mo, £50/yr, £100/yr
bundle), Fantasy Football Hub (tiered, sells a "win your mini-league or money
back" guarantee), Fantasy Football Fix. Free: Premier Fantasy Tools' Mini League
Analyzer, FPL Core, FPL Toolbox, Fantasy Football Pundit, Mini League Mate
(Patreon newsletter). Plus the official FPL site, which just shipped its own
Price Change Predictor.

**Market gap.** Paid tools = global-rank projections. Free tools = descriptive
mini-league statistics. The paid × rival-relative quadrant is empty. Fantasy
Football Hub's own money-back guarantee is framed around the mini-league — proof
the incumbents know that is the emotional purchase driver, and that they are
selling a global-rank tool against a mini-league desire.

**Product.** Enter your FPL manager ID → the app ingests your league, every
rival's squad, transfer history and chip usage from the public API → a Monte
Carlo engine simulates the remaining season → the app answers, in order:
who can I realistically catch, what single move most improves my odds against
them, when does the gap close, and what does it cost me if it fails.

**AI advantage.** Three layers, only one of which is an LLM.
1. Simulation (numeric, deterministic given a seed): P(finish above rival X).
2. Rival behavioural modelling: from transfer history — does this manager take
   hits? chase last week's top scorer? wildcard early? — used as simulation priors.
3. LLM narration: turning a probability distribution into an argument that names
   the rival, the differential, the gameweek and the downside.
A general assistant fails at layer 1 and layer 2 and only imitates layer 3.

**Subscription model.** Free (1 league, 1 rival dossier per season) → Pro
€4.99/month or €29.99/season pass.

**Pricing rationale.** Undercuts Fantasy Football Scout's £50/year by roughly
half in a market where a large share of users are students. The season pass is
the natural unit of the product and eliminates the mid-season renewal decision.

**Acquisition.** A genuinely useful free public league-analysis page as the top
of funnel (paste any league ID, get a real answer), seeded into r/FantasyPL, FPL
X/Twitter and FPL Discords, plus programmatic SEO on players and gameweeks.

**Retention.** The Premier League schedules it: ~38 hard deadlines, plus daily
price changes and injury news. Retention is not a feature here; it is the fixture list.

**Economics.** Blended net ARPU €3.60/paid/month. AI cost bottom-up
$0.10–0.59/paid/month. Gross margin 69–86%. Break-even at 8 paying users.

**Risks.** Seasonality (June–July has no product); the FPL API is public but
undocumented and unilaterally changeable; incumbents could bundle a rival module;
projection quality is capped without an Opta licence.

**Why it could win.** It optimises an objective nobody else optimises, on free
data nobody has to pay for, for an audience that already subscribes, with a viral
loop built into the product's subject matter.

**Why it could fail.** Because mini-league players turn out to enjoy *arguing*
about the decision more than *being told* the decision — i.e. the analysis is
entertainment, and entertainment is worth €0/month when a free tier exists.

---

## Finalist 2 — Second-hand seller copilot · 6.99

**Market.** Vinted: 105M registered users by 2023, €596M revenue, 20 markets,
800M+ items listed. The strongest raw demand on the entire longlist.

**Audience.** 16–30 casual and semi-pro resellers across the EU.

**Human motivation.** Money. The purest possible purchase justification: pay €7,
earn €300.

**Core value mechanism.** Saved time + better decisions.

**Problem/desire.** Listing is slow and pricing is guesswork. Twenty items is an
evening's work and half of them are mispriced.

**Existing solutions.** Vinta.app, Margeo, Nichify, VintiePlus, Telvin, Redrip —
a fragmented field of mostly grey-market automation tools.

**Gap.** No clean, above-board pricing-intelligence layer. Real.

**Product.** Photo in → brand, model and condition detected → title, description
and tags generated → a price band derived from live comparable listings.

**AI advantage.** Vision identification plus a price model over comparables. Real,
not cosmetic.

**Subscription and pricing.** €7–15/month; income-linked WTP means pricing power
is high.

**Economics.** Best revenue ceiling of the three.

**Risks.** This is where it dies. Vinted publishes no API, comparables can only be
obtained by scraping, and Vinted actively restricts and bans accounts associated
with automation — there is an entire content genre about it. The product would be
one enforcement decision from zero, and it would be competing with five
incumbents already inside that blast radius.

**Why it could win.** Money-motivated users are the easiest people in the world to
sell software to.

**Why it could fail.** A platform that does not want you to exist can end you on a
Tuesday, and this one has demonstrated that it will.

---

## Finalist 3 — Co-DM (TTRPG campaign assistant) · 6.98

**Market.** Weekly tabletop RPG groups. **[insufficient evidence]** — no reliable
current figure was found for the number of active D&D tables or paying DMs, and
publisher-issued "player" numbers are marketing, not a market size. This gap is
itself a reason it did not win.

**Audience.** 20–35 Dungeon Masters. Note the ratio: roughly one DM per five
players, so the addressable market is a fifth of the apparent one.

**Human motivation.** Not wanting to let your friends down on Saturday.

**Core value mechanism.** Saved time + self-expression + reason to return.

**Problem/desire.** Prep is hours of work, and the campaign's own history becomes
unmanageable after ten sessions.

**Existing solutions.** World Anvil, LegendKeeper, Obsidian/Notion vaults,
ChatGPT, plus a young field of AI DM tools.

**Gap.** Real. Existing AI tools generate content with no persistent structured
campaign state, so they contradict what happened last week — which is exactly the
failure a DM cannot tolerate.

**Product.** A campaign graph (NPCs, factions, locations, open promises, secrets)
that every generation reads from and writes back to, plus automatic session
recaps from an uploaded transcript.

**AI advantage.** The highest on the whole longlist (9/10): retrieval-constrained
generation plus consistency checking against accumulated state.

**Subscription.** €6–9/month, DM pays for the table.

**Retention.** The best structural retention of the three finalists — after 15
sessions the campaign *is* the switching cost.

**Risks.** Vocal anti-AI sentiment in TTRPG communities is a genuine acquisition
risk, not a manageable one — this is an audience that has publicly punished AI
content. Smaller market. And 5e content licensing must be handled carefully
(SRD 5.1 under CC-BY is fine; published adventures are not).

**Why it could win.** Compounding switching cost and a weekly clock, in a market
where the incumbent tools are databases rather than assistants.

**Why it could fail.** The core audience may reject the category on principle
before evaluating the product.

---

# The winner: Overtake

## Why it won

1. **It has the only objective function nobody else computes.** Every competitor
   maximises expected points. Overtake maximises P(finish above a named person).
   Those produce different answers, and the difference is largest exactly when the
   user cares most — when they are behind. This is differentiation by mathematics,
   not by branding, which is the only kind a solo founder can hold.
2. **Retention is outsourced to the Premier League.** ~38 hard deadlines a season.
   The single biggest failure mode in consumer AI right now is churn after novelty
   (AI monthly plans retain 36% worse over 12 months), and this product's return
   mechanism is not a feature that can wear off.
3. **The data is free, live, legal to read, and rich.** The public FPL API exposes
   every rival's squad, transfers, chips and standings without authentication.
   Compare with finalist 2, whose data requires scraping a hostile platform. Data
   cost: €0.
4. **The paid market is already proven and priced above us.** £50/year is the
   going rate; Overtake enters at €29.99/season. We are not creating a category,
   we are attacking an existing one from below with a better-aimed product.
5. **Virality is intrinsic, not bolted on.** The product's subject is a group of
   named friends. "You are 71% to finish above me" is a message someone sends into
   a group chat unprompted, and every recipient is a qualified lead.
6. **Highest MVP feasibility of the three (9/10) at the lowest running cost
   (9/10).** Free data, no video, no vision, no scraping, no licensing. The entire
   MVP fits inside the €50–200 budget with room to spare.

## Why #2 lost

Platform risk, and it is not survivable rather than merely serious. Vinted offers
no API, the comparables that make the product valuable can only be scraped, and
the platform has an enforcement record against automation-adjacent tools. A
business whose core data supply can be cut off by a company that has already
shown willingness to cut it off is not a business a solo founder with €200 should
start. Demand was the highest on the list; that was not enough.

## Why #3 lost

Two reasons. First, the market could not be sized from evidence — the honest
answer was "insufficient evidence", and starting a business on an unsizable market
is a choice, not a plan. Second, the audience carries an active, organised
hostility to AI in this specific domain, which turns the cheapest acquisition
channel (community posting) into the riskiest one. Its product mechanics were
excellent — the best AI leverage and best switching cost of all three — and it is
the right idea for a founder who is already a member of that community and can
launch with credibility. That founder is not assumed here.

## Biggest advantage

The objective function. "Beat the field" and "beat Dave" are different
optimisation problems, and the entire paid market has spent a decade solving the
first one.

## Biggest weakness

Seasonality. There is no product from late May to early August. Mitigated by
selling a season pass rather than a monthly subscription (which is already the
market norm — Fantasy Football Scout sells an annual), but it means the business
has one shot at acquisition per year, in August, and a mistimed launch costs
twelve months.

## Biggest risk

The FPL API is public but undocumented and unilaterally changeable. The Premier
League has tolerated an ecosystem on it for a decade, but has granted nothing.
See `11-legal-security-risk.md` for the mitigation (aggressive caching, a
degradation mode, and a manual-import fallback that keeps the product alive
without the API).

## Biggest opportunity

The same engine generalises to any fantasy format with a public state and a
private league: UEFA Champions League Fantasy, Euro/World Cup fantasy, NFL, and
eventually draft leagues. The rival-relative simulation is the asset; FPL is the
first market for it, and it is the one that fixes the seasonality problem in V2.

## What must be proven first

Not "can this be built" — it plainly can. The hypothesis under test is:

> **A mini-league player will pay money for rival-relative advice.**

Everything in the 14-day plan exists to test that one sentence, and the GO/NO-GO
thresholds in `12-mvp-14-day-plan.md` are written against it.

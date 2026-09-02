# Scoring model, full table, and elimination

## The weighted model

Seventeen criteria, each scored 1–10, weighted to 100. Two criteria are
**inverted for readability**: `Competition` scores the *ease* of the competitive
landscape (10 = wide open, 1 = brutal) and `Cost` scores the ability to run
cheaply (10 = near-zero marginal cost).

Reproduce with `python3 score.py`.

| Criterion | Weight | Why this weight |
|---|---|---|
| Willingness to pay | 10 | The brief's own warning: never confuse attention with willingness to pay. Tied for the heaviest weight. |
| Demand | 10 | Nothing else matters if the underlying desire is weak. |
| Retention | 9 | RevenueCat's data shows AI apps retain 36% worse over 12 months. In this category retention *is* the business. |
| Differentiation | 8 | The brief says fear undifferentiated competition, not competition. |
| Value intensity | 7 | How hard the product hits one or more of the 11 mechanisms. |
| Frequency | 7 | Drives both retention and subscription logic. |
| Subscription fit | 7 | A product can be valuable and still be a bad recurring purchase. |
| AI leverage | 6 | Required by the brief, but weighted below demand — AI is the how, not the why. |
| Acquisition | 6 | With €50–200 there is no paid-acquisition escape hatch. |
| Competition (ease) | 5 | Deliberately *not* heavy: a hard market with a real wedge beats an easy market with none. |
| Market size | 5 | A solo founder needs a reachable market, not a huge one. |
| MVP feasibility | 5 | Hard constraint: two weeks. |
| Viral potential | 4 | Free distribution is the only distribution available. |
| SEO potential | 4 | The only compounding free channel. |
| Audience fit (15–35) | 3 | Almost every candidate passes, so it barely discriminates. |
| Cost to operate | 2 | Binary in practice — either it fits €200/month or it doesn't. |
| Revenue potential | 2 | Deliberately light. Optimising for the ceiling at this stage is how founders pick unbuildable ideas. |

**What the weighting deliberately punishes:** ideas that are fun to build, easy to
describe, and have no repeat purchase. **What it deliberately rewards:** a boring
external clock plus a real reason to pay.

---

## Full comparison table

\* Competition = *ease* of the landscape (10 = wide open).

| # | Opportunity | Audience | Primary motivation | Value mechanism | Demand | Pay | Retention | AI | Competition* | MVP | **Overall** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Overtake - FPL rival-aware decision engine | 18-30 FPL mini-league players | Beat my friends | Status / Better decisions | 8 | 7 | 8 | 7 | 5 | 9 | **7.72** |
| 2 | Vinted/second-hand seller copilot | 16-30 EU resellers | Earn side income | Saved time / Better decisions | 9 | 8 | 7 | 7 | 3 | 5 | **6.99** |
| 3 | Co-DM - TTRPG campaign assistant | 20-35 Dungeon Masters | Run a good game for friends | Saved time / Self-expression | 7 | 6 | 8 | 9 | 6 | 6 | **6.98** |
| 4 | Short-form idea/outlier engine for creators | 18-30 short-form creators | Grow and earn | Better decisions / Saved time | 9 | 8 | 6 | 7 | 3 | 6 | **6.95** |
| 5 | Thumbnail/title CTR predictor | 18-32 YouTubers | Higher CTR | Better decisions | 7 | 7 | 6 | 8 | 4 | 5 | **6.32** |
| 6 | TCG collection tracker + scanner | 15-32 card collectors | Know what I own | Curiosity / Status | 8 | 7 | 7 | 6 | 3 | 4 | **6.26** |
| 7 | AI astrology / personality entertainment | 16-30, female-skewing | Be seen / be known | Entertainment / Curiosity | 7 | 6 | 6 | 5 | 4 | 8 | **6.21** |
| 8 | Climbing/bouldering training coach | 18-35 climbers | Climb harder | Personalisation / Status | 6 | 6 | 7 | 6 | 7 | 6 | **6.15** |
| 9 | End-to-end faceless-channel pipeline | 18-30 channel operators | Passive income | Saved time / Convenience | 8 | 7 | 5 | 7 | 3 | 3 | **6.05** |
| 10 | AI dating conversation coach | 18-30 app daters | Be liked | Status / Anxiety reduction | 8 | 7 | 5 | 5 | 3 | 7 | **5.97** |
| 11 | LoL/Valorant AI improvement coach | 15-28 ranked gamers | Climb rank | Status / Better decisions | 8 | 5 | 6 | 6 | 2 | 5 | **5.88** |
| 12 | Curriculum-specific AI study companion | 16-19 exam candidates | Pass the exam | Anxiety reduction | 8 | 5 | 5 | 7 | 4 | 6 | **5.88** |
| 13 | AI language conversation partner | 16-35 language learners | Actually speak | Personalisation | 8 | 6 | 5 | 6 | 2 | 6 | **5.84** |
| 14 | Twitch clip finder + highlight editor | 18-30 streamers | Repurpose streams | Saved time | 6 | 6 | 6 | 7 | 5 | 4 | **5.81** |
| 15 | AI quiz night generator for friend groups | 16-30 friend groups | Have a fun night | Entertainment / Social | 6 | 4 | 5 | 6 | 7 | 8 | **5.79** |
| 16 | AI chess improvement coach (Lichess) | 15-35 online chess players | Gain rating | Better decisions / Status | 6 | 6 | 6 | 6 | 3 | 7 | **5.77** |
| 17 | Student flat-hunting copilot (DACH) | 18-27 students relocating | Secure a flat | Anxiety reduction / Convenience | 8 | 7 | 3 | 6 | 6 | 5 | **5.77** |
| 18 | Padel improvement + match logging | 22-40 padel players | Improve | Personalisation / Social | 6 | 6 | 6 | 5 | 7 | 6 | **5.76** |
| 19 | Wardrobe stylist from your own closet | 17-30 fashion-aware | Look good daily | Self-expression / Status | 7 | 5 | 5 | 6 | 4 | 5 | **5.67** |
| 20 | AI journaling / self-insight | 18-32 journallers | Understand myself | Curiosity / Anxiety reduction | 6 | 5 | 5 | 6 | 4 | 7 | **5.44** |
| 21 | AI meal planner + grocery optimiser | 20-35 home cooks | Stop deciding daily | Convenience / Saved time | 7 | 5 | 5 | 5 | 2 | 7 | **5.39** |
| 22 | AI CV + job application tailoring for students | 19-26 job seekers | Get callbacks | Anxiety reduction / Saved time | 8 | 6 | 3 | 5 | 3 | 7 | **5.35** |
| 23 | Contract / scam checker for young adults | 18-30 first contracts | Avoid a costly mistake | Anxiety reduction | 7 | 5 | 3 | 6 | 6 | 6 | **5.27** |
| 24 | Steam backlog 'what to play next' engine | 17-35 PC gamers | Escape the backlog | Convenience / Curiosity | 6 | 3 | 4 | 5 | 7 | 8 | **5.16** |
| 25 | AI personal finance for young Europeans | 20-32 first salaries | Not mess up money | Anxiety reduction | 7 | 5 | 5 | 5 | 3 | 5 | **5.15** |
| 26 | Music taste analytics (Spotify) | 16-30 music listeners | Show my taste | Status / Self-expression | 6 | 3 | 4 | 4 | 5 | 6 | **5.03** |
| 27 | Sneaker/streetwear resale portfolio | 16-28 resale collectors | Track value | Status / Better decisions | 6 | 5 | 5 | 5 | 4 | 5 | **4.97** |
| 28 | Anime/manga tracker + recommender | 15-28 anime fans | Find the next show | Curiosity | 6 | 3 | 5 | 4 | 3 | 7 | **4.95** |
| 29 | AI travel itinerary builder | 20-35 travellers | Plan a trip | Convenience | 7 | 4 | 2 | 4 | 2 | 7 | **4.26** |
| 30 | Tech purchase 'second opinion' advisor | 20-35 buyers | Buy the right thing | Better decisions | 6 | 3 | 2 | 4 | 3 | 6 | **4.11** |

---

## The four gate tests

Every opportunity above 6.0 was run through the four tests in sections 18–21 of
the brief. These are pass/fail, not scored — a failure eliminates regardless of
the weighted score.

### Test 1 — "Why would I pay €X every month instead of using a free alternative?"

| Opportunity | Answer | Verdict |
|---|---|---|
| Overtake | The free mini-league tools are descriptive (ownership, standings, differentials). None simulate an outcome, and none answer "what do I have to do to overtake him?". The paid tools answer a different question (global rank). | **Pass** |
| Seller copilot | Free alternative is doing it by hand, badly. Strong answer. | **Pass** |
| Co-DM | Free alternative is ChatGPT plus Obsidian, which loses campaign state. Moderate answer. | **Pass** |
| Creator engine | Free alternative is the YouTube Studio dashboard plus manual competitor scrolling. Answer exists but the *paid* alternatives (vidIQ free tier) are strong. | **Weak pass** |
| Astrology | Free alternative is Co-Star's free tier, which is very good. | **Fail** |
| Steam backlog | Free alternative is your own library page. | **Fail** |
| Music analytics | Free alternative is Spotify Wrapped, once a year, and people are satisfied with that. | **Fail** |
| Anime tracker | Free alternative is MyAnimeList/AniList, free forever, community-owned. | **Fail** |

### Test 2 — "Why would I return?"

| Opportunity | Daily | Weekly | Monthly | Verdict |
|---|---|---|---|---|
| Overtake | Price changes, injury news, rival transfers | **The deadline** — a hard, externally imposed weekly commitment | Chip windows, monthly league standings resets, fixture-swing planning | **Pass, strongest on the list** |
| Seller copilot | New items to list | Weekly listing session | Monthly earnings review | **Pass** |
| Co-DM | — | **Session prep** | Campaign arc planning | **Pass** |
| Creator engine | Trend refresh | Weekly upload cycle | Monthly performance review | **Pass** |
| CV tailoring | — | — | — | **Fail — the product's success terminates the subscription** |
| Flat-hunting | Daily during a search | — | Terminates when they move in | **Fail on subscription fit** |
| Travel builder | — | — | 1–3× per year | **Fail** |
| Contract checker | — | — | A few times a year | **Fail** |

### Test 3 — AI replacement test ("could I just use ChatGPT?")

| Opportunity | Could a general model do it? | What stops it |
|---|---|---|
| Overtake | **No.** | It has no access to live FPL state, cannot see your rivals' squads, does not know today's prices or injury news, and cannot run 20,000 season simulations. The value is a *computation over private-to-the-moment data*, and the LLM is only the narrator. |
| Seller copilot | Partly | Vision + copy is promptable; live comparables pricing is not. |
| Co-DM | Partly | Generation is promptable; persistent structured campaign state is not. |
| Creator engine | Partly | Ideation is promptable; the outlier corpus is not. |
| Meal planner | **Yes** | Nothing stops it. Eliminated. |
| Travel builder | **Yes** | Nothing stops it. Eliminated. |
| Language partner | **Yes** | Voice mode already does this. Eliminated. |
| Tech advisor | **Yes** | With web search, this is a single prompt. Eliminated. |

### Test 4 — Free alternative test

Handled inside Test 1. Four opportunities were eliminated by it outright.

---

## Elimination log

Every opportunity that did not reach the final three, and the specific reason.

| # | Opportunity | Eliminated because |
|---|---|---|
| 02 | Creator idea engine | **Undifferentiated competition.** vidIQ, 1of10 ($29/$69), Spikes and OutlierKit already ship this. A solo founder's only wedge would be brand. Scored 6.95 — the narrowest miss on the list. |
| 05 | Chess coach | The platform owns the category (Chess.com acquired Aimchess and bundles improvement analytics) and the long tail is dense with near-identical clones. |
| 06 | LoL/Valorant coach | Free, entrenched incumbents with desktop overlays and years of habit. Differentiation 3/10. |
| 07 | Curriculum study companion | Capitalised competition (Knowunity, €27M) plus a structurally terminal audience — students graduate — plus a minors-by-default user base. |
| 08 | CV tailoring | Fails the return test absolutely: the product works by making itself unnecessary. |
| 09 | Flat-hunting | Subscription fit 4/10, extreme seasonality, and it depends on scraping listing portals. |
| 10 | Dating coach | Fails on values before it fails on score: the product's job is to help people present a version of themselves they did not write. Also handles screenshots of private conversations — third-party personal data under GDPR with no lawful basis. |
| 11 | Meal planner | Fails the AI replacement test outright. |
| 12 | Personal finance | Regulated-advice boundary, open-banking access costs real money, and the incumbent is the user's own bank app. |
| 13 | TCG tracker | Camera-first product in a web-first brief; crowded with mobile-native incumbents (Collectr, Ludex, CollX); price data needs licensing. |
| 14 | Sneaker portfolio | Thin demand post-hype; StockX shows the numbers for free. |
| 15 | Travel builder | Frequency 3/10, subscription fit 2/10, fails AI replacement test. |
| 16 | Language partner | Fails AI replacement test; competing with Duolingo. |
| 17 | Journaling | Extremely sensitive data with a wellbeing duty of care, and retention depends on a habit the product cannot create. |
| 18 | Astrology | Fails the free alternative test against Co-Star; and the "content" is unfalsifiable, which means quality cannot be defended and the category races to the bottom. |
| 19 | Steam backlog | WTP 3/10. A lovely free tool, not a business. |
| 20 | Music analytics | WTP 3/10 and existential platform risk from Spotify's API restrictions. |
| 21 | Climbing coach | The best of the "underserved niche sport" family, but market size 4/10 and a cold-start problem: nothing works until the user has logged 20 sessions. |
| 22 | Padel | As above, with an audience skewing past the brief's range. |
| 23 | Anime tracker | Fails the free alternative test against MyAnimeList/AniList. |
| 24 | Quiz generator | Genuinely fun, viral 8/10, but the host pays and the group free-rides. WTP 4/10. |
| 25 | Contract checker | Frequency 4/10 and a legal-advice boundary. Better as a free lead magnet than a subscription. |
| 26 | CTR predictor | Requires a labelled training corpus the founder does not have on day one, and vidIQ ships a version already. |
| 27 | Clip finder | Video processing costs break a €200 budget immediately. |
| 28 | Tech advisor | Frequency 3/10, subscription fit 2/10. An affiliate site wearing a SaaS costume. |
| 29 | Wardrobe stylist | Cold-start chore: cataloguing a wardrobe is an hour of work before any value appears. |
| 30 | Faceless pipeline | Cost 2/10 and MVP feasibility 3/10 — rendering video is the single most expensive item on this list — in the most commoditised segment of the whole market. |
| 04 | Seller copilot | Reached the final three and was eliminated there. See `04-top3-and-winner.md`. |
| 03 | Co-DM | Reached the final three and was eliminated there. See `04-top3-and-winner.md`. |

# The 30 opportunities

Every entry uses the same fields: **Audience · Problem/desire · Value mechanisms ·
Motivation · Existing behaviour · Competitors · Gap · Solution · AI role ·
Subscription reason · Frequency · Retention · Virality · SEO · Acquisition ·
Risks · Difficulty.**

Difficulty is 1 (weekend) to 5 (needs a team). Scores for all 30 are in
`03-scoring-and-elimination.md`.

---

## 01 — Overtake ★ SELECTED

**Audience** 18–30 FPL managers in a competitive mini-league of 5–30 people.
**Problem/desire** "I don't care about my global rank. I want to beat Dave."
**Value mechanisms** Status (primary), Better decisions, Anxiety reduction, Curiosity, Reason to return.
**Motivation** Bragging rights in a permanent, named peer group with a 38-week scoreboard.
**Existing behaviour** Manually clicking through rivals' squads after each deadline, spreadsheets, group-chat arguments, pasting squads into ChatGPT.
**Competitors** Fantasy Football Scout (£10/mo, £50/yr), Fantasy Football Hub (tiered, "win your mini-league or money back"), Fantasy Football Fix, LiveFPL, free analysers (Premier Fantasy Tools, FPL Core, FPL Toolbox, Fantasy Football Pundit), Mini League Mate (Patreon newsletter).
**Gap** Paid tools optimise expected points against the global field. Free tools describe mini-league statistics. Nobody optimises *P(finish above this specific rival)*.
**Solution** Connect your FPL ID → the app pulls your league, every rival's squad, transfers and chips → a Monte Carlo engine simulates the remaining season → an LLM writes the argument: who to catch, which differential does it, when the gap closes, what it costs if it fails.
**AI role** Interpretation and argumentation on top of simulation; behavioural profiling of rivals from their transfer history; conversational "what if" against live state.
**Subscription reason** A new answer is required every gameweek, ~38 times a season, because the fixtures, prices and your rivals all changed.
**Frequency** Daily in the 48h before a deadline; 2–4 sessions per gameweek.
**Retention** The Premier League fixture list is the retention mechanism.
**Virality** Extremely high and native — the product's output is about a group of friends, and sharing it into the league chat is the natural act.
**SEO** High: programmatic pages per player/fixture/gameweek plus a genuinely linkable free tool.
**Acquisition** r/FantasyPL, FPL Twitter/X, FPL YouTube, Discord leagues, free public league-analysis tool as the top of funnel.
**Risks** Seasonality (June–July dead); the FPL API is public but undocumented and could be restricted; incumbents could bundle a rival module.
**Difficulty** 2.

---

## 02 — Outlier (short-form idea engine)

**Audience** 18–30 creators posting Shorts/Reels/TikToks, 1k–500k followers.
**Problem/desire** "I don't know what to make next, and my last three flopped."
**Value mechanisms** Better decisions, Saved time, Status, Reason to return.
**Motivation** Income and audience growth.
**Existing behaviour** Manually scrolling competitors, saving references, guessing hooks, using ChatGPT for titles.
**Competitors** vidIQ, 1of10 (Free/$29/$69), Spikes, OutlierKit, TubeLab, Creatorset.
**Gap** Most tools surface outliers; few close the loop back to *your own* channel's performance data.
**Solution** Track a niche's channels via the free YouTube Data API, detect views-vs-baseline outliers, cluster the pattern, generate hooks scored against your own historical retention.
**AI role** Pattern extraction from titles/thumbnails, hook generation, per-channel calibration.
**Subscription reason** Trends decay weekly; the corpus must be re-crawled continuously.
**Frequency** Weekly to daily.
**Retention** Moderate — creators churn when they stop posting.
**Virality** Moderate (creators recommend tools publicly).
**SEO** Moderate — brutally contested.
**Acquisition** YouTube, creator Discords, Product Hunt.
**Risks** Undifferentiated competition against funded incumbents; TikTok data is expensive and legally grey.
**Difficulty** 3.

---

## 03 — Co-DM (TTRPG campaign assistant)

**Audience** 20–35 Dungeon Masters running a weekly D&D/Pathfinder campaign.
**Problem/desire** "Prep eats my whole Saturday and I still forget what the players did in session 7."
**Value mechanisms** Saved time, Anxiety reduction, Self-expression, Reason to return.
**Motivation** Running a good game for friends without burning out.
**Existing behaviour** Notion/Obsidian vaults, spreadsheets, ChatGPT for NPC names, hand-written recaps.
**Competitors** World Anvil, LegendKeeper, Chartopia, Friends & Fables, a long tail of AI DM tools.
**Gap** Existing AI tools generate content but have no persistent, structured campaign state, so they contradict last week's session.
**Solution** A campaign graph (NPCs, factions, locations, promises, secrets) that every generation reads from and writes back to, plus session recaps from an uploaded transcript.
**AI role** Structured generation constrained by campaign state; retrieval over session history; consistency checking.
**Subscription reason** Weekly sessions, forever; the value compounds with campaign length.
**Frequency** Weekly (prep) + during session.
**Retention** Very high once a campaign has 10+ sessions in it — switching cost is the campaign itself.
**Virality** Table-level (one DM, 4–6 players who see it).
**SEO** Good — SRD 5.1 is CC-BY, so monster/spell/item pages are legal programmatic SEO.
**Acquisition** r/DMAcademy, r/DnDBehindTheScreen, TTRPG YouTube.
**Risks** Loud anti-AI sentiment in TTRPG communities; smaller market; DMs are ~1 in 5 players.
**Difficulty** 3.

---

## 04 — Second-hand seller copilot (Vinted/Kleinanzeigen/Willhaben)

**Audience** 16–30 casual and semi-pro resellers in the EU.
**Problem/desire** "Listing 20 items takes an evening and I have no idea what to charge."
**Value mechanisms** Saved time, Better decisions, Convenience.
**Motivation** Direct income.
**Existing behaviour** Manual photo → manual title → guessing price by scrolling similar listings.
**Competitors** Vinta.app, Margeo, Nichify, VintiePlus, Telvin, Redrip.
**Gap** Fragmented, mostly grey-market automation; no clean pricing intelligence layer.
**Solution** Photo → brand/model/condition detection → title, description, tags and a price band from live comparables.
**AI role** Vision identification, copy generation, price regression on comparables.
**Subscription reason** You list every week.
**Frequency** Weekly.
**Retention** High while selling.
**Virality** Moderate (reseller TikTok is loud).
**SEO** Good ("how much is X worth on Vinted").
**Acquisition** Reseller TikTok/YouTube, Facebook groups.
**Risks** **Critical** — no public API, comparables require scraping, and Vinted bans accounts for automation.
**Difficulty** 4.

---

## 05 — Chess improvement coach (Lichess/Chess.com)

**Audience** 15–35 online chess players, 800–2000 rating.
**Problem/desire** "I've plateaued and I don't know what to work on."
**Value mechanisms** Better decisions, Status, Personalisation.
**Motivation** Rating gain.
**Existing behaviour** Free engine analysis, random puzzles, YouTube.
**Competitors** Chess.com's own Insights/Game Review, Chessable, Aimchess (acquired by Chess.com), plus a dense tail of tiny AI-coach apps.
**Gap** Narrow — the platform owns the category and bundles it.
**Solution** Pull game history via free APIs, run engine analysis, cluster error patterns, generate spaced-repetition puzzles from your own blunders.
**AI role** Error clustering, natural-language diagnosis, training-plan generation.
**Subscription reason** You keep playing; the diagnosis keeps changing.
**Frequency** Daily.
**Retention** Moderate — improvement plateaus break the habit.
**Virality** Low.
**SEO** Moderate, heavily spammed.
**Acquisition** r/chess, chess YouTube.
**Risks** Chess.com is both the platform and the competitor; engine compute cost.
**Difficulty** 3.

---

## 06 — LoL/Valorant improvement coach
**Audience** 15–28 ranked players. **Desire** climb rank. **Mechanisms** Status, Better decisions. **Behaviour** op.gg, VOD review, coaching. **Competitors** op.gg, Blitz, Mobalytics, Porofessor — all free, all entrenched, all with overlays. **Gap** minimal. **Solution/AI** match-history diagnosis and drills. **Sub reason** daily play. **Frequency** daily. **Retention** moderate. **Virality** moderate. **SEO** contested. **Risks** free incumbents with habit lock-in; Riot API rate limits for production keys. **Difficulty** 4.

## 07 — Curriculum-specific AI study companion (matura/Abitur/A-level)
**Audience** 16–19 exam candidates. **Desire** "am I actually ready?" **Mechanisms** Anxiety reduction, Personalisation. **Behaviour** past papers, Quizlet, ChatGPT. **Competitors** Knowunity (€27M raised), StudySmarter, Turbolearn, Quizlet. **Gap** narrow national curricula, but tiny markets each. **AI** question generation graded against a real syllabus, readiness estimation. **Sub reason** exam season only. **Frequency** daily for 3 months, then zero. **Retention** structurally terminal — students graduate. **Risks** capitalised competition, minors-by-default audience, brutal seasonality. **Difficulty** 3.

## 08 — CV + application tailoring for students
**Audience** 19–26 job/internship seekers. **Desire** more callbacks. **Mechanisms** Anxiety reduction, Saved time. **Competitors** Teal, Simplify, Careerflow, Kickresume, plus LinkedIn itself. **Gap** minimal. **Sub reason** weak — people cancel the day they get hired. **Frequency** burst then zero. **Retention** structurally terminal. **Risks** the product succeeds by making itself unnecessary. **Difficulty** 2.

## 09 — Student flat-hunting copilot (DACH)
**Audience** 18–27 students moving to Vienna/Munich/Berlin. **Desire** get a flat before 200 other applicants. **Mechanisms** Anxiety reduction, Convenience, Better decisions. **Behaviour** refreshing portals, alert bots, mass-applying. **Competitors** portal alerts, WG-Gesucht bots. **Gap** real — scam detection and instant German-language applications. **Sub reason** poor: 4–10 weeks of use then cancel (defensible as a "cancel when you move in" model, but LTV is capped). **Frequency** daily for weeks. **Risks** scraping portals; extreme seasonality (Aug–Sep). **Difficulty** 3.

## 10 — Dating conversation coach
**Audience** 18–30 app daters. **Mechanisms** Status, Anxiety reduction. **Competitors** a crowded, App-Store-native field. **Gap** minimal. **Risks** ethically shaky (coaching people to misrepresent themselves), 18+ only, screenshot-based data handling is sensitive personal data under GDPR. **Rejected on values as much as on score.** **Difficulty** 2.

## 11 — Meal planner + grocery optimiser
**Audience** 20–35 cooking for themselves. **Mechanisms** Convenience, Saved time. **Competitors** dozens, plus every general assistant. **Gap** none — this is the canonical "just a better prompt" product. **Difficulty** 2.

## 12 — Personal finance for young Europeans
**Audience** 20–32 first-salary. **Mechanisms** Anxiety reduction, Better decisions. **Competitors** banking apps themselves, Revolut, Monarch. **Risks** regulated advice boundary; open-banking access costs real money; the incumbent is the bank. **Difficulty** 4.

## 13 — TCG collection tracker + scanner
**Audience** 15–32 Pokémon/One Piece/MTG collectors. **Mechanisms** Curiosity, Status, Better decisions. **Behaviour** spreadsheets, Cardmarket tabs. **Competitors** Collectr, Ludex, CollX, Rippr, TCGIndex, Cards AI. **Gap** EU/Cardmarket pricing is thinner than US, but the category is mobile-native and crowded. **Risks** camera-first product is a bad fit for a web MVP; price-data licensing. **Difficulty** 4.

## 14 — Sneaker/streetwear resale portfolio
**Audience** 16–28. **Mechanisms** Status, Better decisions. **Competitors** StockX itself, Sole Retriever. **Gap** thin; hype cycle has cooled. **Difficulty** 3.

## 15 — AI travel itinerary builder
**Audience** 20–35. **Fatal flaw** frequency: 1–3 times a year. Subscription fit 2/10. Absorbed by general assistants. **Difficulty** 2.

## 16 — AI language conversation partner
**Audience** 16–35 learners. **Competitors** Duolingo, Speak, Praktika, plus voice mode in every general assistant. **Gap** none a solo founder can hold. **Difficulty** 3.

## 17 — AI journaling / self-insight
**Audience** 18–32. **Mechanisms** Curiosity, Anxiety reduction. **Competitors** Rosebud, Day One, Stoic. **Risks** the data is among the most sensitive a person has; wellbeing duty of care; retention depends on a habit the product cannot enforce. **Difficulty** 2.

## 18 — AI astrology / personality entertainment
**Audience** 16–30, female-skewing. **Mechanisms** Entertainment, Curiosity, Social, Status. **Competitors** Co-Star, The Pattern, Sanctuary. **Strengths** genuine daily-return mechanic and strong virality. **Weakness** the "content" is unfalsifiable, which makes quality undefendable and invites a race to the bottom; ARPU is thin. **Difficulty** 2.

## 19 — Steam backlog "what to play next"
**Audience** 17–35 PC gamers. **Fatal flaw** willingness to pay 3/10 — it is a nag, not a gain. Free Steam API, delightful product, no business. **Difficulty** 1.

## 20 — Music taste analytics
**Audience** 16–30. **Strengths** virality (Wrapped-style shareables). **Fatal flaw** WTP 3/10; Spotify has restricted several API endpoints for new applications, which is existential platform risk. **Difficulty** 2.

## 21 — Climbing/bouldering training coach
**Audience** 18–35 indoor climbers. **Strengths** genuinely underserved, passionate, growing; Runna proved the adaptive-plan subscription model works in endurance sport. **Weakness** market size 4/10; data must be self-reported, so cold-start is hard. **Difficulty** 3.

## 22 — Padel improvement + match logging
Same shape as 21. Booming in southern Europe, almost no software. Audience skews slightly older than the brief's target. Market size 4/10. **Difficulty** 3.

## 23 — Anime/manga tracker + recommender
**Audience** 15–28. **Fatal flaw** WTP 3/10 — MyAnimeList and AniList are free, beloved and community-owned. **Difficulty** 2.

## 24 — AI quiz night generator for friend groups
**Audience** 16–30. **Strengths** virality 8/10, MVP 8/10, genuinely fun. **Weakness** the host pays and the group free-rides; Kahoot proved this monetises in education/work, not among friends. WTP 4/10. **Difficulty** 2.

## 25 — Contract / scam checker for young adults
**Audience** 18–30 signing first leases, phone contracts, freelance agreements. **Strengths** value intensity 8/10 — a bad lease is expensive. **Fatal flaw** frequency 4/10 and subscription fit 3/10; also a legal-advice boundary that requires careful framing. **Difficulty** 3.

## 26 — Thumbnail/title CTR predictor
**Audience** 18–32 YouTubers. **Strengths** highest pure AI leverage on the list (8/10) — a real trained model, not a prompt. **Weakness** requires a training corpus the founder does not have; vidIQ already ships a version. **Difficulty** 4.

## 27 — Twitch clip finder + highlight editor
**Audience** 18–30 streamers. **Weakness** video processing costs are the enemy of a €200 budget (cost 3/10) and MVP feasibility is 4/10. **Difficulty** 4.

## 28 — Tech purchase "second opinion" advisor
**Fatal flaw** frequency 3/10, subscription fit 2/10. A great affiliate site, not a subscription. **Difficulty** 2.

## 29 — Wardrobe stylist from your own closet
**Audience** 17–30. **Weakness** cataloguing your wardrobe is a large upfront chore for a speculative payoff; cold-start kills it. **Difficulty** 3.

## 30 — End-to-end faceless-channel pipeline
**Audience** 18–30 automation-channel operators. **Strengths** demand 8/10, WTP 7/10. **Fatal flaw** MVP feasibility 3/10 and cost 2/10 — rendering video is the single most expensive thing on this list, and the €50–200 budget dies on day one. Also a commodity with 50+ competitors. **Difficulty** 5.

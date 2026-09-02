# Product specification

## 1. Product definition

**Name.** **Overtake**
*(Domain, social handles and a UK/EU trademark search must be run before any
money is spent on branding. Fallbacks: `playovertake.com`, `overtake.fpl`,
`getovertake.com`.)*

**One sentence.** Overtake tells you exactly what to do to finish above the
specific people in your FPL mini-league.

**Elevator pitch.**
Every FPL tool on the market optimises the same number: expected points against
13 million strangers. But nobody actually cares about those 13 million people.
They care about eight friends, a group chat, and ten months of bragging rights.
Those are different problems. If you're 40 points behind the leader with six
gameweeks left, the highest-expected-points move is the *worst* move you can make
— it locks in your deficit. Overtake reads your league from the official FPL API,
simulates the rest of the season 20,000 times against every rival's actual squad,
and tells you the move that most improves your odds of finishing above them — and
what it costs if it goes wrong.

**Core promise.** *You'll know exactly what it takes to catch them.*

**Primary value mechanism.** Status.
**Secondary.** Better decisions · Anxiety reduction · Curiosity · Reason to return.

**Problem/desire.** "I don't care about my global rank. I want to beat Dave, and I
don't know whether I still can."

**Solution.** Rival-relative simulation, narrated.

**Unique selling proposition.** *The only FPL tool that optimises for beating the
people you actually know.*

**Why users return.** ~38 hard deadlines a season, plus price changes and injury
news between them, plus rivals whose moves change your optimal move every week.

**Why users pay.** The free tier answers *what is happening*. The paid tier
answers *what to do about it*, for every rival, every week. And the market has
already established that this answer is worth £50/year.

**Why AI matters.** The simulation produces a probability distribution. A
distribution does not change anyone's behaviour. The LLM turns it into a specific,
named, defensible argument — and answers the follow-up question the user has at
23:47 on a Friday, against live state. Neither half works alone.

**What Overtake does NOT do.**

- It does not sell odds, accept stakes, or link to bookmakers. Ever. This is not
  a gambling product and must never look like one.
- It does not make transfers on your behalf. It never touches your FPL account
  with write access, and never asks for your FPL password.
- It does not try to beat Fantasy Football Scout at points projection. Projections
  are an input, not the product.
- It does not have a mobile app at launch. It is a responsive web app.
- It does not cover other sports at launch.
- It does not scrape anything.

---

## 2. Personas

### Persona A — "Marcus", 24, the one who's behind

- **Lifestyle.** Graduate scheme, Manchester, shares a flat, watches every match.
- **Occupation.** Junior analyst.
- **Goals.** Finish above the four people from his old university house who have
  been in the same 9-person league since 2019. He has never won it.
- **Frustrations.** He reads FPL content for hours and ends up with the same team
  as everyone else. He knows this is why he never gains ground and doesn't know
  what to do instead.
- **Motivations.** Nine years of unbroken mockery from one specific friend.
- **Online behaviour.** r/FantasyPL daily, two FPL YouTubers, an FPL Twitter list,
  the league WhatsApp group all week.
- **Spending.** Spotify, a gym membership, Steam sales, has tried a free trial of
  a paid FPL site and cancelled because "it just told me to buy the same players
  everyone has".
- **Existing solutions.** The official app, a fixture ticker screenshot, ChatGPT
  when he's undecided at 11pm.
- **Emotional trigger.** Seeing the gap in the league table on Monday morning.
- **Reason to subscribe.** "Marcus is 44 points behind Dan. Captaining Wirtz this
  week — 4% owned in your league — is worth +6.1 expected points *of gap closure*,
  and lifts your odds of finishing above him from 18% to 26%."
- **Reason not to subscribe.** He is a value-conscious 24-year-old with eleven
  subscriptions already, and he suspects any FPL tool is content dressed as maths.

### Persona B — "Priya", 29, the one defending a lead

- **Lifestyle.** Product designer, London, plays in a 22-person work league with a
  £10 buy-in and enormous social stakes.
- **Goals.** Protect a 30-point lead for eleven more gameweeks without doing
  anything stupid.
- **Frustrations.** Every piece of FPL advice is written for people chasing. She
  wants the opposite advice and there is nowhere to get it.
- **Motivations.** Loss aversion. She does not want to be the person who blew it.
- **Online behaviour.** Light — checks once before each deadline, does not read
  FPL content.
- **Spending.** Pays for convenience readily; will buy a season pass without
  thinking if the first answer is good.
- **Emotional trigger.** A rival taking a −8 hit and gaining 20 points on her.
- **Reason to subscribe.** Overtake is the only product that says "cover his
  differentials, don't chase points" — the defensive strategy nobody publishes.
- **Reason not to subscribe.** She only opens it once a week; €4.99/month may feel
  like a lot for four visits. (This is exactly who the €29.99 season pass is for.)

### Persona C — "Tom", 17, the school-league one

- **Lifestyle.** Sixth form, Leeds, plays in a 30-person year-group league and a
  6-person one with close friends.
- **Occupation.** Student, part-time weekend job.
- **Goals.** Win the friends' league. The year-group league is unwinnable and he
  knows it.
- **Frustrations.** Everyone in his league watches the same YouTuber and picks the
  same team, so the league is decided by captaincy luck.
- **Motivations.** Pure social standing among 30 people he sees every day.
- **Online behaviour.** TikTok and YouTube Shorts FPL content, Discord.
- **Spending.** Limited and parent-mediated. High price sensitivity — but he pays
  for a game battle pass, so the *category* of spend is not alien.
- **Emotional trigger.** Being called out in the group chat.
- **Reason to subscribe.** The differential finder — it tells him what nobody in
  his league owns, which is the only lever he has.
- **Reason not to subscribe.** Payment friction (no card of his own), and the
  under-16/under-18 handling in `11-legal-security-risk.md` deliberately makes
  this persona harder to convert, on purpose. **Tom is a persona we serve well on
  the free tier and do not aggressively monetise.**

---

## 3. User stories

**Onboarding**
- As a new visitor, I can paste a league ID or my manager ID and get a real
  answer before creating an account, so I can judge the product without signing up.
- As a new user, I can find my manager ID without knowing what it is (paste the
  URL from the FPL site, or search my team name).

**Core loop**
- As a manager, I can see, for each rival, my probability of finishing above them.
- As a manager, I can see which players they own that I don't, and what that gap
  is worth per gameweek.
- As a manager, I can ask "what if I captain X instead of Y" and see the effect on
  my odds against a named rival, not on my global rank.
- As a manager, I can get a Deadline Brief before every deadline, summarising the
  single highest-leverage move for my league position.
- As a manager, I can see a rival's behavioural profile built from their transfer
  history (hit-taker, template-follower, early wildcarder).
- As a manager, I can plan chip usage against the specific gameweeks where my
  rivals are exposed.
- As a manager, I get a Monday recap showing what actually happened versus what
  was projected, and how the odds moved.

**Sharing**
- As a manager, I can generate a shareable image of the league odds table.
- As a manager, I can share a single dossier line ("I'm 71% to finish above you")
  to a group chat.

**Account**
- As a user, I can export or delete all my data without emailing anyone.
- As a subscriber, I can cancel in two clicks and keep access until the period ends.

---

## 4. User journey and the aha moment

| # | Stage | What happens | Design intent |
|---|---|---|---|
| 1 | **Discovery** | A search for "fpl mini league analyser" or a Reddit comment linking a specific league analysis | The free tool must be linkable and useful without an account |
| 2 | **Landing page** | Headline names the emotion, not the feature. One input: your league ID. | Zero-friction first action |
| 3 | **First action** | Paste league ID → live league board with odds appears in <5 seconds | No signup wall before value |
| 4 | **First result** | "You are **18%** to finish above Dan. Here are the three people you can realistically still catch." | This is the hook |
| 5 | **AHA MOMENT** | **Reading one rival dossier: the named person, their exact differentials, and the sentence "closing this gap needs +3.7 points per gameweek — here is the one move that gets you 60% of the way there."** | Everything before this is setup; everything after is delivery |
| 6 | **Signup** | Prompted only *after* the aha moment, to save the league and get the Deadline Brief by email | Signup is now a save action, not a toll gate |
| 7 | **Return** | Deadline Brief email 36h before the deadline; Monday recap email | Two externally-timed re-entry points per week |
| 8 | **Free limit** | The second rival dossier is locked. The Overtake Simulator is locked. | The limit sits *after* the aha moment and *on* the repeat action |
| 9 | **Upgrade** | Inline, on the locked dossier, with the actual rival's name in the button: "Unlock all 8 rivals" | Specific, not generic |
| 10 | **Payment** | Stripe Checkout, two fields, monthly or season pass | Season pass presented as the default |
| 11 | **Continued use** | 2–4 sessions per gameweek | |
| 12 | **Renewal** | Monthly auto-renews; season pass ends in May with a pre-season renewal offer in July | Renewal ask lands when excitement is highest, not lowest |

**The aha moment, stated precisely:** *the moment the user reads a specific,
named rival's dossier and sees, for the first time, that catching them is a
solvable problem with a stated cost.* Every product decision upstream exists to
get the user there in under 90 seconds, and every decision downstream exists to
make it repeatable.

---

## 5. Feature prioritisation

### MUST HAVE (in the 14-day MVP)

| Feature | Purpose | Value | Complexity | Depends on |
|---|---|---|---|---|
| FPL data ingest + cache | Everything | Critical | M | — |
| League board with odds | The free hook | Critical | M | ingest, simulator |
| Monte Carlo season simulator | The differentiator | Critical | M | ingest |
| Rival dossier (1 free, rest paid) | **The aha moment** | Critical | M | simulator |
| Deadline Brief (in-app + email) | The return mechanism | Critical | M | simulator, LLM |
| Magic-link auth | Accounts without password risk | High | S | — |
| Stripe Checkout + webhooks | Revenue | Critical | M | auth |
| Shareable league image | Free distribution | High | S | league board |
| Analytics + event tracking | Answering the GO/NO-GO question | Critical | S | — |
| Legal pages, cookie handling, deletion | Non-negotiable | Critical | S | — |

### SHOULD HAVE (V1, weeks 3–8)

| Feature | Purpose | Value | Complexity |
|---|---|---|---|
| Overtake Simulator ("what if I captain X") | The most-requested follow-up | High | M |
| Rival behavioural profiles | Real personalisation and a moat | High | M |
| Chip planner vs. rivals | The highest-stakes decision of the season | High | L |
| Monday recap email | Second weekly re-entry | Medium | S |
| Ask-the-Gaffer conversational Q&A | Handles the long tail | Medium | M |
| Head-to-head league support | A whole format currently unserved | Medium | M |
| Price-change watchlist for rival-owned players | Daily return reason | Medium | S |

### COULD HAVE (V2)

- Multi-league dashboard for people in 4+ leagues
- UEFA Champions League Fantasy (fixes summer/winter gaps)
- Public "league of the week" content engine for SEO
- Browser extension overlaying odds on the official FPL site
- Discord bot posting the weekly odds into the league's own server
- A "league pass" purchasable by one admin for a whole mini-league

### DO NOT BUILD

| Not building | Why |
|---|---|
| Our own points-projection model competing with Opta-licensed incumbents | We would lose, and it is not the product. Use public/derived projections as an input and be transparent about their accuracy. |
| Anything touching odds, stakes, or bookmaker affiliates | Turns a skill-analysis product into a regulated gambling-adjacent one and poisons every acquisition channel. |
| Automated transfers / write access to FPL accounts | Requires the user's FPL password, breaks their ToS, and creates a catastrophic security liability. |
| A native mobile app in year one | The audience is at a desktop or a mobile browser before a deadline. A PWA covers it. |
| A social network, feed, or comments | The users already have a group chat. Competing with it is a losing fight; feeding it is a winning one. |
| An AI chatbot as the front door | The simulation is the product. Leading with a chat box tells users this is a wrapper. |
| Free-tier unlimited simulation | The simulation is the cost centre and the value. Cap it. |

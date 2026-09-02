# Growth: SEO, acquisition, virality, retention, analytics

## 1. SEO strategy

FPL search volume is highly seasonal and enormous in-season, but the head terms
("fpl tips", "fpl captain") are owned by ten-year-old domains with hundreds of
backlinks. **We do not compete for head terms.** We compete on three things
incumbents structurally cannot do well.

### 1.1 The tool page is the SEO asset

`/l/{league_id}` is a real, useful, indexable page that answers a query no
content page can: "how is *my* league doing". Every league a user pastes creates a
shareable URL. This is the same mechanic that built op.gg and Untappd — the tool
*is* the content.

**Index policy:** league pages are `noindex` by default (they contain other
people's team names and are of no value to a stranger) but are fully shareable via
URL. What *is* indexed is `/how-to/find-your-fpl-league-id`, the comparison pages,
and the programmatic set below. This distinction matters: shareability and
indexability are different goals.

### 1.2 Programmatic SEO (the volume play)

| Template | Pages | Query intent | Refresh |
|---|---|---|---|
| `/player/{slug}` | ~700 | "haaland fpl points", "is X worth it fpl" | Weekly, auto |
| `/player/{a}-vs-{b}` | ~2,000 curated pairs | **"salah or haaland fpl"** — the single highest-intent FPL query shape | Weekly |
| `/gameweek/{n}` | 38 | "fpl gameweek 12 tips" | Per gameweek |
| `/gameweek/{n}/captain` | 38 | "fpl gw12 captain" | Per gameweek |
| `/differentials/gameweek/{n}` | 38 | "fpl differentials gw12" — **on-thesis**, differentials are the mini-league lever | Per gameweek |
| `/team/{club}/fpl` | 20 | "arsenal fpl players" | Weekly |
| `/mini-league/{topic}` | ~30 | "how to win your fpl mini league", "fpl mini league strategy behind" | Static, evergreen |

Total ≈ 2,900 pages. **Quality gate:** every generated page must contain at least
one number that exists nowhere else (our simulated differential impact, our
measured ownership swing). A page that only restates public stats is thin content
and will be treated as such. If a template cannot clear that bar, it does not ship.

### 1.3 Technical SEO

- SSR/ISR on all public pages; player pages revalidate hourly, gameweek pages on
  data change.
- `Article`, `FAQPage`, `SportsEvent` and `BreadcrumbList` JSON-LD where genuinely
  applicable.
- Auto-generated sitemap split by template, submitted per gameweek.
- Internal linking: every player page links to its comparison pages, its club page
  and the current gameweek page. Every gameweek page links to the differentials
  page. This is the link equity engine.
- Canonicals on comparison pairs (`a-vs-b` canonical, `b-vs-a` redirects).
- Core Web Vitals: the league board must render server-side within the LCP budget;
  the simulation loads after.

### 1.4 Backlinks

Not bought, not exchanged. Three earned sources:

1. **The free league tool.** People link to their own league page in forums and
   Discords. This is the primary mechanism.
2. **An annual public data study** — "We simulated 50,000 mini-leagues: here's when
   your season is actually over." Genuinely novel, uses data we already have, and
   is the kind of thing FPL media quote.
3. **Guest analysis** for FPL newsletters and podcasts, offering the rival-relative
   angle nobody else can write.

---

## 2. Acquisition ladder

### First 10 users — week 1

Hand-recruited. Post the founder's own league analysis in **r/FantasyPL** as a
comment on an existing "rate my team" thread, offering to run the analysis for
anyone who replies with a league ID. Not a product pitch — a demonstration. Do the
first ten by hand if necessary. Channel: Reddit + one FPL Discord.

### First 100 — weeks 2–4

1. A single, honest **r/FantasyPL** post: "I built a tool that works out what it
   takes to beat the people in your mini-league — free, no signup." Read the
   subreddit's self-promotion rules first and follow them exactly; that community
   bans hard and it is the single most valuable channel we have.
2. **FPL Discord servers** — dozens exist, each with hundreds of engaged managers.
   Ask moderators first.
3. **The share loop** — every league page shared into a WhatsApp group reaches 8–30
   qualified people.

### First 1,000 — months 2–4

1. The share loop compounding (see §3).
2. **X/Twitter FPL community** — a weekly "most brutal mini-league in the game"
   post using anonymised aggregate data. Native content, not ads.
3. **Micro-influencer partnerships**: 10–20 FPL YouTubers/streamers with
   5k–50k subscribers. Offer a free season pass and a co-branded league page, not
   cash. This audience is over-served by big sponsors and under-served by tools
   that make good video (watching probabilities move is inherently watchable).
4. Programmatic SEO begins to index (expect 8–12 weeks to meaningful traffic).

### First 10,000 — months 4–12

1. SEO is the primary channel by now.
2. Season-review content in May and pre-season content in July — the two moments
   FPL attention spikes outside gameweeks.
3. A **Discord bot** that posts weekly odds into a league's own server. This puts
   the product where the banter already happens and is the highest-leverage
   distribution build in the roadmap.
4. Only now consider paid: small-budget Reddit and YouTube pre-roll on FPL
   channels, capped at a CAC that keeps LTV/CAC above 3.

**Channels explicitly not used:** TikTok (wrong format for a numerate product),
Instagram, LinkedIn, cold email, Google Ads on head terms (unwinnable auction
against incumbent budgets), and any affiliate arrangement with a bookmaker.

---

## 3. Virality

The loop is real and does not need to be manufactured:

```
User pastes league ID
   → sees odds against named friends
   → screenshots or shares the league card into the league group chat
   → 8–30 rivals see their own name and a probability attached to it
   → competitive reflex: "hang on, what does it say about me?"
   → they open the same public league page (no signup needed)
   → they become users
   → they share it into their *other* leagues
```

**Why this works better than a referral scheme:** the shared artefact is *about
the recipient*. It is not an ad; it is a claim about them, in a group where they
have social standing to defend. The k-factor is unknown and must be measured, but
the mechanism is structurally sound.

**Design requirements to protect the loop:**
- The public league page must never require signup.
- The share image must contain the rivals' real team names.
- Sharing must be one tap, with a pre-written message.
- No referral bribes. A bribed share is a worse share and it cheapens the product.

**[assumption]** Target k-factor ≥ 0.4 by month 3. If it lands below 0.2, the
growth plan is SEO-only and the timeline roughly doubles.

---

## 4. Retention

| Cadence | Mechanism | Why it works |
|---|---|---|
| **Daily** | Price-change alerts on players your rivals own; injury news affecting a rival's differential | Something changed that affects *your* gap, not generic news |
| **Weekly** | **The deadline.** Deadline Brief email 36h before; Monday recap showing how the odds moved | The Premier League enforces this; we do not have to |
| **Monthly** | Chip windows, fixture-swing planning, league standing milestones ("you've moved above two people this month") | Longer-arc narrative |
| **Seasonal** | Season review, final table card, July renewal offer | Ends the story well, which is what makes renewal feel natural |

**The compounding mechanisms**
- **Personalisation** — rival archetypes get sharper with every gameweek of
  transfer history.
- **History** — "Dan has taken 6 hits this season and gained 11 points from them"
  is a sentence only we can write, and only after we've watched.
- **Progress** — the odds line for the season is a personal narrative graph.
- **Changing data** — the input changes 38 times a year without us doing anything.
- **Habit** — the deadline countdown in the header ties the product to a ritual
  the user already has.

**No dark patterns.** No streaks that punish absence, no artificial urgency, no
guilt copy on cancellation, no notification spam. The FPL calendar supplies all
the urgency this product will ever need; manufacturing more would be both
unnecessary and corrosive.

**Churn management**: the honest risk is that a user who is mathematically out of
contention in their league stops caring in March. Mitigations: surface *secondary*
targets (finishing above the next person down), the head-to-head cup, and next
season's planning. If a user genuinely cannot catch anyone, tell them so and let
them cancel — the alternative is selling them a lie for two months and losing them
forever.

---

## 5. Analytics

### Event taxonomy

| Stage | Events |
|---|---|
| Acquisition | `page_view`, `league_id_pasted`, `referrer_channel`, `share_link_opened` |
| Activation | `league_board_viewed`, `dossier_viewed`, **`aha_reached`** (dossier scrolled past "WHERE THE GAP IS"), `signup_started`, `signup_completed` |
| Engagement | `brief_viewed`, `simulator_run`, `gaffer_message_sent`, `chip_planner_opened`, `session_count_per_gameweek` |
| Sharing | `share_clicked`, `share_image_generated`, `shared_league_visit`, `viral_signup` (signup attributable to a shared link) |
| Monetisation | `paywall_shown`, `checkout_started`, `checkout_completed`, `plan_selected`, `upgrade`, `cancel_started`, `cancel_completed` |
| Retention | `gameweeks_active`, `return_within_deadline_window`, `email_open`, `email_click` |
| AI | `brief_generated`, `grounding_check_failed`, `fallback_template_served`, `llm_cost_usd` |
| Quality | `projection_mae_weekly`, `sim_duration_ms`, `stale_data_shown` |

### North Star Metric

> **Weekly Active Deciding Managers (WADM)** — unique users who view a rival
> dossier or Deadline Brief **within the 72 hours before a gameweek deadline.**

**Why this and not MRR, DAU or signups.** It is the only metric that is
simultaneously (a) the moment of value delivery, (b) the moment of habit
formation, and (c) a leading indicator of both retention and revenue. Signups
measure curiosity. DAU rewards the wrong behaviour — this product should be used
intensely twice a week, not idly every day, and optimising for daily opens would
push us toward notification spam. MRR is a lagging indicator that arrives too late
to steer a 14-day build. WADM rising while MRR is flat means the pricing is wrong;
WADM falling means the product is wrong. That diagnostic separation is exactly
what a solo founder needs.

**Supporting metrics**: aha-rate (visitors reaching `aha_reached`), free→paid
conversion, gameweek-over-gameweek retention cohorts, k-factor, LLM cost per paid
user, projection MAE.

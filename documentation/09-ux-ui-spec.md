# UX / UI specification

## 1. Design direction

The primary value mechanism is **status**, so the interface has to feel like a
scoreboard and a briefing room — not a dashboard, and definitely not a chatbot.

**Reference feel:** a broadcast graphic crossed with a trading terminal. Dense,
confident, numerate. Dark-first, because this is used at 11pm on a Friday.

**Principles**

1. **The rival's name is always on screen.** Never "your rank" — always "you vs
   Dan". Specificity is the product.
2. **Probability before prose.** The number lands first; the explanation supports it.
3. **Every number is auditable.** Hovering any figure shows how it was computed and
   when. Trust is the whole business.
4. **No chat box on the front door.** Ask-the-Gaffer is a secondary surface reached
   from a dossier, not the primary interface. A chat box says "wrapper".
5. **The deadline is a clock, not a feature.** A live countdown is persistent in
   the header. It is the product's heartbeat.

**Visual system**

| Token | Value |
|---|---|
| Base | `#0B0F14` background, `#121821` surface, `#1C2531` border |
| Text | `#E8EDF4` primary, `#93A1B4` secondary |
| Accent (you) | `#3DDC97` — used only for the user's own row and gains |
| Accent (rival) | `#FF6B6B` — used only for rivals and losses |
| Neutral data | `#7C8CA1` |
| Type | Inter (UI) · JetBrains Mono (all numbers) |
| Numbers | Tabular figures, always. Probabilities to whole percent, points to one decimal. |
| Radius | 8px · Spacing scale 4/8/12/16/24/32/48 |

Light mode ships in V1, not MVP. Respect `prefers-color-scheme` when it does.

---

## 2. Pages

| Route | Auth | Purpose |
|---|---|---|
| `/` | public | Landing page |
| `/l/{league_id}` | public | **The free hook** — league board with odds |
| `/l/{league_id}/vs/{entry_id}` | public (1 free) | Rival dossier — **the aha moment** |
| `/app` | session | Dashboard: primary league, countdown, brief |
| `/app/brief` | Pro | Deadline Brief |
| `/app/simulator` | Pro | Overtake Simulator |
| `/app/chips` | Pro | Chip planner vs rivals |
| `/app/leagues` | session | Manage tracked leagues |
| `/app/account` | session | Plan, billing portal, export, delete |
| `/player/{slug}` | public | Programmatic SEO player page |
| `/gameweek/{n}` | public | Programmatic SEO gameweek page |
| `/how-it-works`, `/pricing`, `/faq` | public | Conversion support |
| `/privacy`, `/terms`, `/cookies` | public | Legal |

---

## 3. Key screens

### 3.1 Landing page (`/`)

```
┌──────────────────────────────────────────────────────────────┐
│  OVERTAKE                              How it works  Pricing │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│      Stop trying to beat 13 million strangers.               │
│      Start beating the eight people in your league.          │
│                                                              │
│      Overtake simulates the rest of the season against       │
│      your rivals' actual squads and tells you exactly        │
│      what it takes to finish above them.                     │
│                                                              │
│      ┌────────────────────────────────┐  ┌───────────────┐   │
│      │ Paste your league ID or URL    │  │ See my odds → │   │
│      └────────────────────────────────┘  └───────────────┘   │
│         No signup. No FPL password. Ever.                    │
│                                                              │
│   ── live example ─────────────────────────────────────────  │
│   You are 18% to finish above Dan · 71% above Priya          │
│   Catching Dan needs +3.7 pts/GW. One move gets you 60%.     │
└──────────────────────────────────────────────────────────────┘
```

**Copy blocks (write these, not startup boilerplate):**

- **Headline** — "Stop trying to beat 13 million strangers. Start beating the
  eight people in your league."
- **Subheadline** — "Every other FPL tool optimises your global rank. Nobody has a
  global rank framed on their wall. Overtake works out what it takes to finish
  above the specific people you actually play against."
- **Problem block** — "You're 40 points behind. So you read the tips, you buy the
  template, and you finish 40 points behind. Copying the field is how you stay
  where you are."
- **Product block** — "Overtake reads your league from the official FPL API,
  simulates the remaining season 20,000 times against every rival's real squad,
  and ranks your options by how much they close the gap — not by expected points."
- **AI block** — "The maths is a simulation, not a chatbot. The AI's job is to
  tell you what the simulation means, in a sentence you can act on before the
  deadline. It never invents a number: every figure in every brief is checked
  against the simulation that produced it."
- **How it works** — 1. Paste your league ID · 2. We pull every rival's squad from
  the public FPL API · 3. We simulate the rest of the season · 4. You get one
  clear move before each deadline.
- **Objection block** — "We never ask for your FPL password. We only read data
  that is already public on the FPL website."
- **Pricing** — Free / €4.99 a month / €29.99 for the season. "The season pass is
  cheaper than one bad −8 hit."
- **FAQ** — Is this gambling? (No — no odds, no stakes, no bookmakers, ever.) ·
  Is it allowed? (We only read public FPL pages; we never touch your account.) ·
  How accurate are the projections? (Here is our measured error, updated weekly.) ·
  What happens in the summer? (Season passes cover August to May; we'll email you
  in July.) · Can I cancel? (One click, and you keep access to the end of the period.)
- **Final CTA** — "Paste your league ID. See who you can still catch."

### 3.2 League board (`/l/{id}`) — the free hook

A ranked table, the user's own row highlighted in accent-green. Columns:
`Rank · Manager · Team · Points · Gap · P(you finish above) · Trend`.

The probability column is the entire reason this page exists. Above the table, one
sentence: **"You can realistically still catch 3 of 8."** Below it, three rival
cards; the first is unlocked, the rest are blurred with a specific label —
"Unlock Dan's dossier", not "Upgrade to Pro".

### 3.3 Rival dossier (`/l/{id}/vs/{entry_id}`) — the aha moment

```
┌───────────────────────────────────────────────────────────┐
│  YOU  vs  DAN                              GW7 · 2d 04:11 │
│                                                           │
│        18%          44 pts behind        6 GWs left       │
│   to finish above        the gap          to close it     │
│                                                           │
│  ── WHAT IT TAKES ───────────────────────────────────────  │
│  +3.7 points per gameweek, every gameweek.                │
│                                                           │
│  ── WHERE THE GAP IS ────────────────────────────────────  │
│  He owns, you don't:   Wirtz  41.2 xPts remaining         │
│                        Gvardiol 22.8                      │
│  You own, he doesn't:  Mbeumo 28.4                        │
│                        Semenyo 19.1                       │
│  Net differential swing: −16.5 xPts over 6 GWs            │
│                                                           │
│  ── HIS PATTERN ─────────────────────────────────────────  │
│  Template loyalist · 0.4 hits/GW · wildcards early        │
│  (built from 47 gameweeks of his transfer history)        │
│                                                           │
│  ── THE MOVE ────────────────────────────────────────────  │
│  Captain Wirtz this week.                                 │
│  18% → 26% to finish above Dan.                           │
│  Downside: if he blanks, −3.1 pts vs your current captain.│
│                                                           │
│  ▸ Ask why    ▸ Try a different move    ▸ Share to chat   │
└───────────────────────────────────────────────────────────┘
```

Everything above "THE MOVE" is free on the first dossier. "THE MOVE", "Try a
different move" and "Ask why" are Pro.

### 3.4 Overtake Simulator (Pro)

Left: your squad with drag-to-swap. Right: a live-updating bar of P(above) for
every rival, showing the delta as you experiment. The interaction is the value —
watching one probability rise while another falls is what makes the trade-off real.

### 3.5 Deadline Brief (Pro)

One card, one recommendation, one risk statement, one "do nothing" case. Never a
list of ten options — the product's job is to decide, not to present a menu.
Footer: `simulated 20,000 seasons · data as of 14:22 · projection MAE 1.9 · seed 8814`.

---

## 4. States

| State | Treatment |
|---|---|
| **Loading (first sim)** | A real progress narrative — "Reading 9 squads… simulating 20,000 seasons…" — not a spinner. The wait is the credibility. |
| **Empty (no league yet)** | A worked example with a real public league so the value is visible before any input |
| **Empty (pre-season)** | "Season starts in 12 days. Here's what happened in your league last year." — keeps July alive |
| **Stale data** | Amber banner with exact timestamp. Never silently stale. |
| **FPL API down** | "The FPL API isn't responding. These numbers are from 14:22. We'll refresh automatically." |
| **Simulation queued** | Show last gameweek's odds, clearly labelled, with an ETA |
| **Free limit hit** | The blurred card names the specific rival. Price and both plan options inline. No modal. |
| **Error** | Plain language, an error id to quote, and a mailto. Never a stack trace. |
| **Success (upgrade)** | Land straight back on the dossier they were blocked on, unlocked. Never a generic "welcome" page. |
| **Past due** | Full access for 7 days with a dismissible banner, then downgrade. Never delete data. |
| **Cancelled** | "Pro until 14 May. Nothing changes until then." No guilt copy. |
| **Season ended** | Season review, league final table, a shareable card, and one renewal email in July |

---

## 5. Mobile and responsive

Assume **mobile-majority** — the deadline check happens on a phone.

- League board becomes a card list; `P(above)` stays visible in every card.
- The dossier stacks in the order above; "THE MOVE" is sticky at the bottom.
- The countdown moves into a compact header pill.
- The simulator is desktop-first; on mobile it degrades to a tap-to-swap list with
  the same live probability bar. Do not ship a broken drag interaction on touch.
- Installable PWA with the countdown as the badge. No native app in year one.

## 6. Accessibility

- Never encode meaning in colour alone — every gain/loss carries a sign or arrow.
- Contrast ≥ 4.5:1 for text (the dark palette above is chosen to pass).
- Full keyboard navigation for the simulator, including swaps.
- `prefers-reduced-motion` respected on the probability animations.
- All data tables are real `<table>` elements with scope, not divs.

## 7. Share artefacts

Two, both generated server-side as PNG via OG image generation:

1. **League odds card** — the full table with probabilities, branded, ~1200×630.
2. **Head-to-head card** — "I'm 71% to finish above you" with both team names.

Both carry a short URL back to the public league page. This is the growth loop and
it must look good enough to post without embarrassment — that is a design
requirement, not a nice-to-have.

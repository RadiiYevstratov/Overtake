# Your tasks — things only you can do

Everything in this file needs *you*: your accounts, your card, your name on a
public post, or a decision that is yours to make. Everything technical is done
and tested (see the bottom of this file).

Work top to bottom. Tick a box when a task is done.

**Next FPL deadline: Gameweek 6 — Saturday 10 October, 10:00 UTC (12:00 in
Bratislava).** Three weeks of break until then: the recruitment window.

---

## 1. Today / this week (blocks the beta)

### 1.1 Your own FPL team — use Overtake on yourself

You can't honestly sell a tool for FPL mini-leagues without living in one.

- [ ] Go to <https://fantasy.premierleague.com> and sign in (or create an account).
- [ ] Pick a squad before **10 October, 10:00 UTC**. The GW5 deadline has passed; GW6 is your first.
- [ ] Join 3–5 mini-leagues: friends, a work league, and 1–2 public ones. You'll need their codes from the people who run them.
- [ ] On the FPL site: **Points** → your name → the number in the page address is your **manager ID**.
- [ ] On Overtake: **Account** → enter that manager ID.
- [ ] Paste each league's ID on the Overtake homepage. It now loads any league, and the first visit takes about 5 seconds.
- [ ] Every gameweek: read your Deadline Brief, ask the Gaffer one question, and write down one thing that confused you or was wrong. That list is your product backlog.

### 1.2 A real payment, once (optional but recommended)

The payment system is proven without a charge: live prices, the webhook, and
its signing secret all checked on 18 September (details at the bottom). The one
thing not yet seen is **a real card going through** — 3-D Secure, your bank,
the receipt email. About 10 minutes.

- [ ] Sign out of Overtake. Sign in with a **second address** that has never been used — e.g. `radkoyevko+paytest@gmail.com`. Gmail delivers it to your normal inbox.
  - Don't use your main account: it's on the unlimited list, so it wouldn't behave like a customer's.
- [ ] Go to **Pricing** → **Monthly (€4.99)** → pay with your own card.
- [ ] Check that you're sent back to Overtake and the **Account** page says *Pro — monthly*.
- [ ] Check that you received Stripe's receipt email.
- [ ] Refund it: <https://dashboard.stripe.com> → **Payments** → the €4.99 payment → **Refund**.
- [ ] Cancel it: Stripe → **Customers** → that customer → the subscription → **Cancel** → *Immediately*.
- [ ] Refresh Overtake's **Account** page. It should now say *Free*.
- [ ] If any step doesn't match, tell me which one.

### 1.3 Sentry — deeper error monitoring (optional)

You're **already covered**: a crash on the website, in the API or in a background
job now emails **hello@overtakefpl.com**, which is forwarded to your Gmail. At
most one email an hour per problem. Sentry adds full error context on top.

- [ ] Sign up at <https://sentry.io> (the free plan is enough) using hello@overtakefpl.com.
- [ ] Create a project → platform **FastAPI** → name it `overtake-api`.
- [ ] Copy the **DSN**. It looks like `https://abc123@o123.ingest.sentry.io/456`.
- [ ] Run this in Git Bash, pasting your DSN between the quotes:
  ```bash
  flyctl secrets set -a overtake SENTRY_DSN="paste-the-DSN-here"
  ```
  The API restarts in about 30 seconds, and it and the worker report to Sentry from then on. Nothing else to set.

### 1.4 Add an email filter so alerts stand out

- [ ] In Gmail, create a filter: subject contains `[Overtake]` → **Star it** + **Never send it to Spam** + label it `Overtake alerts`.
- [ ] When one arrives, forward it to me or paste it into our chat. It includes the exact command to find the error in the logs.

---

## 2. Before you tell anyone about it

### 2.1 Reserve the name everywhere

Use **hello@overtakefpl.com** for all of them: it forwards to your Gmail, so
verification emails arrive. Put every password in a password manager and switch
on two-factor login.

- [ ] **Reddit** — <https://www.reddit.com/register> → username `overtakefpl`.
- [ ] **X / Twitter** — <https://x.com/i/flow/signup> → handle `@overtakefpl`.
- [ ] **Instagram** — <https://www.instagram.com/accounts/emailsignup/> → `overtakefpl`.
- [ ] **TikTok** — <https://www.tiktok.com/signup> → `overtakefpl`.
- [ ] **Discord** — <https://discord.com/register> → username `overtakefpl`.
- [ ] Where a name is taken, use the same fallback everywhere, e.g. `overtake.fpl` or `overtakefpl_app`, and tell me which you used.
- [ ] On each profile: link to <https://overtakefpl.com> and add one line — *Beat the people in your FPL mini-league.*

### 2.2 Google Search Console and Bing

This lets Google tell you what people search to find you, and which pages are indexed.

- [ ] Open <https://search.google.com/search-console> → **Add property** → choose **Domain** → enter `overtakefpl.com`.
- [ ] Google shows a **TXT record**. Add it at your domain registrar — the same place you added the ImprovMX email records. Type `TXT`, host `@`, value exactly as Google shows it.
- [ ] Back in Search Console, click **Verify**. DNS can take up to an hour.
- [ ] Go to **Sitemaps** → submit `https://overtakefpl.com/sitemap.xml`.
- [ ] Open <https://www.bing.com/webmasters> → **Import from Google Search Console**. It takes one click once Google is verified.

### 2.3 Try every competitor yourself — before claiming any difference

Don't write "the only tool that…" until you've checked. Spend about 20 minutes on each:

- [ ] **LiveFPL** (livefpl.net) — live mini-league tables and rank projections.
- [ ] **FPL Review** (fplreview.com) — projections and a planner; paid tier.
- [ ] **Fantasy Football Hub** (fantasyfootballhub.co.uk) — AI tools and a rival comparison.
- [ ] **Fantasy Football Scout** (fantasyfootballscout.co.uk) — member tools and articles.
- [ ] **FPL Statistics / Fantasy Football Fix** — mini-league and rival features.
- [ ] For each, write down: *Does it give me the probability of finishing above a named rival? Does it tell me the single move that changes that? Does it explain why?* Only claim what survives this check.

---

## 3. Every day during the break: warm up communities

20 minutes a day. **No links and no mention of Overtake for the first 2–3 weeks.**
Accounts that arrive and immediately promote get banned.

- [ ] **Read the rules first**:
  - r/FantasyPL → sidebar and wiki (self-promotion is heavily restricted)
  - r/FantasyPLCommunity
  - r/PremierLeague
- [ ] **Reddit**: answer 2–3 questions a day in the daily threads (Rate My Team, Quick Questions), especially mini-league questions — *"I'm 40 points behind my mate, what do I do?"* is exactly your topic.
- [ ] **Discord**: join 2–3 large FPL servers (search "Fantasy Premier League Discord", or ask on Reddit which are good) and be useful in their help channels.
- [ ] Keep a note of which communities allow a tool to be shared, where, and when (e.g. a "resources" or "self-promo Saturday" thread).

---

## 4. The beta: 30 users and one FPL expert

### 4.1 Find your experienced FPL helper

Someone with a strong multi-season record who will tell you when the numbers look wrong.

- [ ] Look for people who give consistently good answers in r/FantasyPL, or top finishers in public leagues.
- [ ] Offer free Pro for the season plus credit on the site, in exchange for 20 minutes of honest feedback each gameweek.

### 4.2 Recruit 30 beta testers

- [ ] Start with people you know: friends, family, colleagues, your own mini-league members. Aim for 10.
- [ ] Then communities, **only once you're allowed to post links there**. Aim for 20.
- [ ] Always share **tagged links**, so the scorecard shows which channel worked:

  | Where you share | Link to use |
  |---|---|
  | Reddit | `https://overtakefpl.com/?utm_source=reddit&utm_medium=social&utm_campaign=beta` |
  | Discord | `https://overtakefpl.com/?utm_source=discord&utm_medium=social&utm_campaign=beta` |
  | X | `https://overtakefpl.com/?utm_source=x&utm_medium=social&utm_campaign=beta` |
  | Friends / WhatsApp | `https://overtakefpl.com/?utm_source=friends&utm_medium=direct&utm_campaign=beta` |
  | TikTok / Instagram bio | `https://overtakefpl.com/?utm_source=tiktok&utm_medium=social&utm_campaign=beta` (change `tiktok` to `instagram` for Instagram) |

  (Links shared from inside the app are already tagged automatically.)
- [ ] Offer something concrete: *"Free Pro for the rest of the season if you give me feedback after 3 gameweeks."*
- [ ] Keep a simple sheet: name, how you reached them, their league ID, date joined, feedback.

---

## 5. Weekly scorecard and stop criteria (your decisions)

### 5.1 How to read the numbers

Your account needs admin access to see the funnel. I've switched it on for
`radkoyevko@gmail.com`. Every Monday:

- [ ] Sign in, then open <https://overtakefpl.com/api/v1/analytics/funnel?days=7>.
  You'll see raw numbers, a GO/NO-GO verdict per metric, and `by_source` — visitors, boards viewed, sign-ups and purchases for each channel.
- [ ] Copy them into this table (keep it in a spreadsheet):

| Week | Visitors | Boards viewed | Sign-ups | Paid | Aha rate | Share rate | Best source | Worst source |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

### 5.2 Thresholds already in the product (from your original plan)

| Metric | GO if at least | NO-GO if below |
|---|---|---|
| Aha rate (dossier → aha moment) | 45% | 25% |
| Share rate (dossier → share clicked) | 15% | 8% |
| Paywall click-through | 8% | 4% |
| Paid conversion (sign-up → paid) | 3% | — |

### 5.3 Stop criteria — decide and sign them **before** launch

A draft for you to change. The point is to write them down *now*, while you're neutral.

- [ ] **After 4 gameweeks of beta**: if the aha rate is below 25% **and** fewer than 10 of the 30 testers use it two gameweeks running → stop building features; talk to users until you know why.
- [ ] **After the public launch + 6 weeks**: if paid conversion is below 1% with at least 300 sign-ups → change the offer (price, free tier, or positioning) before spending anything on marketing.
- [ ] **Any week**: if one source brings more than half of all paid users → put your 20 minutes a day there, and cut the source with no sign-ups at all.
- [ ] Write the date you agreed these: ____________

---

## 6. Content: bank two weeks of posts before launch

Overtake already generates public pages from live data. Use them as material
rather than writing from scratch:

- `https://overtakefpl.com/gameweek/6` — the gameweek preview
- `https://overtakefpl.com/player/<name>` — projections for every player
- `https://overtakefpl.com/compare/<player-a>-vs-<player-b>` — head-to-head comparisons
- The **Share** button on any league board makes an image of the odds. It's tagged automatically.

- [ ] Write 10 short posts, one per day for two weeks. A proven format: one question a mini-league player actually has, answered with one number from Overtake. For example: *"Is it worth taking a hit to catch the leader? In 20,000 simulations of a typical league…"*
- [ ] Put them in a scheduler (Buffer, or X's own scheduler) so they go out even in a busy week.

---

## 7. Housekeeping

- [ ] **Rotate the Fly.io access token before about 5 October.** At <https://fly.io/user/personal_access_tokens>, create a new token, update it wherever you use it (your computer, CI), then delete the old one.
- [ ] **VAT / accountant**: selling to EU consumers means VAT at *their* country's rate. Ask an accountant whether to register for the EU **OSS** scheme in Slovakia. Stripe Tax can calculate it, but only you can register.
- [ ] **Anthropic credits**: <https://console.anthropic.com> → **Billing**. A brief costs under half a cent, and the app is capped at $3 a day. Top up before the balance runs out, or briefs silently fall back to the plain version.
- [ ] **An old program on your computer**: a Python process started on 3 September is still listening on port 8000 — almost certainly an old local API from early development. Harmless, but if you don't recognise it, close it (Task Manager → *python.exe* started 3 September → End task).

---

## Done and verified (18 September)

For your reference. None of this needs action.

- **New leagues work.** Pasting any league ID fetches it from FPL; a waiting screen refreshes itself; the board appears in about 5 seconds. Checked on three real leagues, including two sharing a member with yours.
- **The homepage number is true.** FPL's live count, rounded down (10.8 million).
- **Ask-the-Gaffer has a screen**, under the Deadline Brief. The conversation is kept across reloads. A question the writer can't answer costs nothing.
- **Traffic sources are tracked.** Each browser's first source is recorded; shared links are tagged; **sign-ups are now counted** (they never were before, which left paid conversion permanently blank).
- **Errors reach you.** A crash emails you within seconds, at most one email an hour per problem, with personal data scrubbed. Sentry switches on when you add the key.
- **Payments proven in live mode without a charge:**
  - prices are live and correct (€4.99 per month, €29.99 per season)
  - the webhook points at the right address with exactly the six events the code handles
  - a real signed Stripe event was received, verified and recorded, which proves the webhook secret. The webhook subscription was restored straight afterwards.
- **Your account is unlimited** for testing — no daily caps — while spending real money against the $3/day AI cap.

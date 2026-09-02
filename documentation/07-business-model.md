# Business model, pricing and financial model

All figures reproduce with `python3 finance.py`. Every input is labelled
**[verified]**, **[estimate]** or **[assumption]**.

---

## 1. Pricing

| Tier | Price | Includes |
|---|---|---|
| **Free** | €0 | 1 league · live league board with win-probabilities · squad diagnosis · **1 rival dossier per season** · shareable league image |
| **Pro — monthly** | **€4.99 / month** | Unlimited rivals and leagues · Deadline Brief (in-app + email) · Overtake Simulator · chip planner · Ask-the-Gaffer · Monday recap |
| **Pro — season pass** | **€29.99 / season** (August–May) | Identical to monthly, one payment, no mid-season renewal decision |

No trial. A free tier that delivers the aha moment *is* the trial, and RevenueCat's
data shows 3-day trials are effectively one-hour trials — 84% of trial
cancellations happen on day 0–1 **[verified]**. A permanently useful free tier
also does the SEO and virality work a trial cannot.

### Why these numbers

| Input | Value | Source |
|---|---|---|
| Fantasy Football Scout | £10/mo, £50/yr, £100/yr bundle | **[verified]** |
| Fantasy Football Hub | tiered Starter/Pro/Ultra, "win your mini-league or money back" | **[verified]** |
| Gen Z pays readily but cancels readily | Visa / eMarketer / Recurly | **[verified]** |
| AI-app 12-month monthly-plan retention is 36% worse than non-AI | RevenueCat 2026 | **[verified]** |

The reasoning:

1. **Undercut, don't match.** At €29.99/season Overtake is roughly half Fantasy
   Football Scout's £50/year. We are entering an established category from below
   with a differently-aimed product, not creating a new price point.
2. **Make the season pass the default.** It solves three problems at once: it
   matches the natural unit of the product (a season), it removes the June–July
   seasonality gap from the churn calculation, and it sidesteps the AI-app
   monthly-churn problem entirely. **[assumption]** 60% of subscribers choose it.
3. **Keep monthly cheap enough to be an impulse.** €4.99 is below the threshold
   where a 24-year-old with eleven subscriptions stops to think.
4. **Do not price for Persona C.** The 15–17 school-league user is served well on
   free and is not a monetisation target — for both ethical and legal reasons
   (`11-legal-security-risk.md`).

### Pricing experiments to run in V1 (not at MVP)

- **League Pass**, €19.99/season, bought by one league admin, unlocking Pro for
  every member of that league. Lower ARPU, dramatically better virality. Test as a
  separate SKU on a subset of leagues.
- Regional pricing (India, Nigeria, Egypt — significant FPL populations with very
  different purchasing power) via Stripe Adaptive Pricing.
- €39.99 season pass to test elasticity upward before assuming €29.99 is right.

---

## 2. Subscription mechanics

| Aspect | Decision |
|---|---|
| Free tier | Permanent, genuinely useful, hard-limited on rival dossiers (the repeat action) |
| Trial | None |
| Billing | Stripe Checkout + Customer Portal. No custom billing UI. |
| Currency | EUR primary, GBP presentment for UK, Stripe Adaptive Pricing later |
| Upgrade | Immediate, prorated by Stripe |
| Downgrade | At period end; access retained until then |
| Cancellation | Two clicks in the Customer Portal, no retention interrogation, no dark pattern |
| Refunds | Full refund on request within 14 days, no questions. EU distance-selling rules give a 14-day withdrawal right for digital services unless the user expressly waives it at purchase — we do **not** ask for a waiver; we honour it. |
| Failed payments | Stripe Smart Retries + dunning emails; 7-day grace period with full access, then downgrade to free (never delete data) |
| Season pass expiry | Ends with the season; renewal offer sent in July when pre-season hype peaks, not in May when the user is sick of it |

**Anti-dark-pattern commitments**, written here so they are testable later: no
pre-ticked upsells, no hidden auto-renew, no "are you sure" gauntlet, cancellation
reachable from the account page in one click, and email reminders **before** a
season pass renews rather than after.

---

## 3. Unit economics

```
Monthly plan            EUR 4.99 / month
Season pass             EUR 29.99 / 10 months (= EUR 3.00 / month)
Plan mix                40% monthly / 60% season          [assumption]
Blended gross ARPU      EUR 3.80 / paid user / month
Payment fees            EUR 0.23  (6.2% of gross)
Blended net ARPU        EUR 3.56 / paid user / month
```

**Payment fees, built up from verified Stripe rates** (stripe.com/en-sk/pricing):

| Component | Rate | Applies to |
|---|---|---|
| UK cards | 2.5% + €0.25 | ~60% of volume **[assumption]** — the UK is the primary market |
| Standard EEA cards | 1.5% + €0.25 | ~30% **[assumption]** |
| International cards | 3.15% + €0.25 | ~10% **[assumption]** |
| Stripe Tax (Basic, no-code) | 0.5% | all transactions |
| Stripe Billing (pay-as-you-go) | 0.7% | **recurring charges only** |

Blended card rate ≈ **2.27%**.

Two structural points fall out of this, and both favour the season pass:

1. **The fixed €0.25 is brutal on small recurring charges.** It costs **8.5%** of a
   €4.99 monthly charge but only **3.6%** of a €29.99 season pass.
2. **Stripe Billing's 0.7% applies to subscriptions, not one-time payments.** The
   season pass is implemented as a one-time charge with a stored entitlement
   (`08-technical-spec.md` §7), so it avoids that fee entirely.

Net effect: **the season pass keeps ~96.4% of its face value; the monthly plan
keeps ~91.5%.**

**Cost per paid user per month**

| Cost | Amount | Note |
|---|---|---|
| AI (bottom-up) | $0.10–0.59 | See `06-ai-spec.md` §9 |
| AI (budgeted) | €0.25–0.60 | 5–15× headroom |
| Simulation CPU | ~€0 marginal | Cached per league, not per user |
| Payment fees | €0.19 | Included above |
| Infrastructure | Stepped fixed cost, not per-user | See below |

---

## 4. Revenue scenarios

"Users" means **registered free accounts**, not visitors. Conversion is
free→paid on registered accounts.

**Assumptions per scenario**

| Scenario | Free→paid | AI cost/paid/mo | Monthly-plan churn | CAC |
|---|---|---|---|---|
| Conservative | 2.0% | €0.60 | 15% | €6.00 |
| Realistic | 4.0% | €0.35 | 10% | €3.00 |
| Optimistic | 7.0% | €0.25 | 7% | €1.50 |

Anchoring: RevenueCat's median Day-35 freemium conversion is **2.1%** **[verified]**
— that is the conservative case. The realistic case assumes web (no app-store
tax, no store friction), an engaged hobbyist audience, and a paywall placed
directly on the repeat action rather than on the first action. **[assumption]**

Infrastructure step function **[estimate]**: €0 up to 200 users (free tiers),
€25/mo to 2,000, €120/mo to 20,000, €900/mo beyond.

### Conservative

| Users | Paid | MRR | ARR | AI | Infra | Gross margin | Contribution/mo |
|---|---|---|---|---|---|---|---|
| 100 | 2 | €8 | €91 | €1 | €0 | 78.0% | €6 |
| 1,000 | 20 | €76 | €911 | €12 | €25 | 45.1% | €34 |
| 10,000 | 200 | €759 | €9,109 | €120 | €120 | 62.2% | €472 |
| 100,000 | 2,000 | €7,591 | €91,090 | €1,200 | €900 | 66.2% | €5,023 |

### Realistic

| Users | Paid | MRR | ARR | AI | Infra | Gross margin | Contribution/mo |
|---|---|---|---|---|---|---|---|
| 100 | 4 | €15 | €182 | €1 | €0 | 84.6% | €13 |
| 1,000 | 40 | €152 | €1,822 | €14 | €25 | 68.1% | €103 |
| 10,000 | 400 | €1,518 | €18,218 | €140 | €120 | 76.7% | €1,165 |
| 100,000 | 4,000 | €15,182 | €182,179 | €1,400 | €900 | 78.7% | €11,946 |

### Optimistic

| Users | Paid | MRR | ARR | AI | Infra | Gross margin | Contribution/mo |
|---|---|---|---|---|---|---|---|
| 100 | 7 | €27 | €319 | €2 | €0 | 87.2% | €23 |
| 1,000 | 70 | €266 | €3,188 | €18 | €25 | 77.8% | €207 |
| 10,000 | 700 | €2,657 | €31,881 | €175 | €120 | 82.7% | €2,198 |
| 100,000 | 7,000 | €26,568 | €318,814 | €1,750 | €900 | 83.9% | €22,280 |

### LTV and CAC

Blended lifetime **[estimate]**: monthly-plan users live 1/churn months; season-pass
users live 10 months with an **[assumption]** 55% season-over-season renewal,
i.e. 10/0.45 ≈ 22 months.

| Scenario | LTV | CAC | LTV/CAC |
|---|---|---|---|
| Conservative | €47 | €6.00 | 7.9 |
| Realistic | €56 | €3.00 | 18.6 |
| Optimistic | €63 | €1.50 | 42.1 |

**Read these ratios sceptically.** They are high because CAC assumes an
organic-first channel mix (Reddit, SEO, in-league sharing) with essentially no
paid spend, which is a *plan*, not a *fact*. If organic acquisition fails and CAC
has to be bought at €15–25 through paid social, the realistic LTV/CAC falls to
2–4 — still viable, but a completely different business. **The validation plan
tests acquisition before it tests anything else** for exactly this reason.

### Break-even

```
Contribution per paid user      EUR 3.21 / month  (realistic)
Paid users to cover EUR 25 infra          7.8
Registered users needed                   195
Paid users for EUR 1,000 MRR              263   (= ~6,600 registered users)
```

**8 paying subscribers make this business cash-positive against its
infrastructure.** That is the number that makes a €50–200 budget rational.

---

## 5. What would make the model wrong

| Assumption | If it's wrong | Detect it by |
|---|---|---|
| 4% free→paid | Everything scales linearly with it; at 1% the business needs 26,000 registered users for €1k MRR | Measure from week 1; GO/NO-GO threshold in `12-mvp-14-day-plan.md` |
| 60% choose season pass | Monthly-heavy mix raises churn exposure and payment fees | Stripe plan mix, visible from day one |
| 55% season renewal | Untestable until August 2027 — the single largest unknown | Nothing can validate this in year one. Treat year-one LTV as 10 months, not 22, when making spending decisions. |
| Organic CAC ≈ €0–3 | The whole model | Track cost per registered user from day 1 including time |
| Seasonality is survivable | June–July revenue is near zero on monthly plans | Season pass mix; plan the summer as a build period, not a revenue period |

**[insufficient evidence]** on the one number that would most improve this model:
what proportion of the 13.1M FPL managers are in a *competitive* mini-league of
5–30 people. FPL does not publish league-size distributions. Serviceable market
is therefore unestimated rather than guessed, and the first 1,000 users will be
the measurement.

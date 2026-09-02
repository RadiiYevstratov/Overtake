# Overtake — market discovery → product → development-ready documentation

Complete chain from market research to a build-ready specification for a
subscription web product aimed at 15–35-year-olds.

**Selected opportunity:** *Overtake* — a rival-aware decision engine for Fantasy
Premier League mini-leagues. It does not try to maximise your global rank. It
maximises your probability of finishing above the specific people in your
mini-league, using the free, public, real-time FPL API — which exposes every
rival's squad, transfers, chips and standing.

---

## Document map

| File | Contains |
|---|---|
| `00-executive-summary.md` | The whole decision in three pages |
| `01-market-research.md` | Market landscape, trends, evidence, gaps, sources |
| `02-opportunity-longlist.md` | 30 opportunities in full format |
| `03-scoring-and-elimination.md` | Weighted model, full score table, elimination reasoning |
| `04-top3-and-winner.md` | Finalist deep-dives, winner selection, why #2 and #3 lost |
| `05-product-spec.md` | Personas, product definition, user journey, aha moment, features |
| `06-ai-spec.md` | AI architecture, models, prompts, memory, validation, cost, abuse |
| `07-business-model.md` | Pricing, subscription mechanics, unit economics, revenue scenarios |
| `08-technical-spec.md` | Architecture, stack, database schema, API, auth, payments, infra |
| `09-ux-ui-spec.md` | Design direction, pages, components, states, flows, copy |
| `10-growth-and-seo.md` | SEO strategy, acquisition ladder, virality, retention, analytics |
| `11-legal-security-risk.md` | GDPR, minors, ToS/platform risk, security, failure analysis, moat |
| `12-mvp-14-day-plan.md` | Day-by-day 14-day build plan |
| `13-roadmap-and-final-verdict.md` | V1/V2/long-term roadmap and the 12 final answers |

## Runnable models

| File | What it does |
|---|---|
| `score.py` | The weighted opportunity scoring model. `python3 score.py` reproduces the ranking. |
| `finance.py` | Pricing, unit economics, break-even and revenue scenarios. `python3 finance.py` reproduces every number in `07-business-model.md`. |

## Evidence standard used

Claims are labelled:

- **[verified]** — taken from a primary or near-primary source, cited in `01-market-research.md`
- **[estimate]** — a modelled number with its assumptions stated
- **[assumption]** — a judgement call with no supporting data
- **[insufficient evidence]** — a question that was asked and could not be answered

No competitor revenue, user count or market size is stated here unless it came
from a source that is cited. Where a number could not be found, the document
says so rather than inventing one.

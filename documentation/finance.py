"""Overtake - unit economics and revenue scenarios.

All figures EUR. "Users" = registered (free) accounts, not visitors.
Everything here is an ASSUMPTION unless labelled BENCHMARK; sources are in
07-business-model.md. Run: python3 finance.py
"""

PRICE_MONTHLY = 4.99      # EUR / month
PRICE_SEASON = 29.99      # EUR / season pass (10 active months, Aug-May)
SEASON_MONTHS = 10

# Stripe card pricing, VERIFIED at stripe.com/en-sk/pricing:
#   standard EEA cards   1.5%  + 0.25 EUR
#   UK cards             2.5%  + 0.25 EUR
#   international cards  3.15% + 0.25 EUR
# Primary market is the UK, so the blend is UK-weighted.
CARD_MIX = {"uk": (0.60, 0.0250), "eea": (0.30, 0.0150), "intl": (0.10, 0.0315)}
STRIPE_PCT = sum(share * rate for share, rate in CARD_MIX.values())   # ~2.265%
STRIPE_FIX = 0.25
STRIPE_TAX_PCT = 0.005     # Stripe Tax Basic, no-code: 0.5% per transaction
STRIPE_BILLING_PCT = 0.007  # Stripe Billing pay-as-you-go, RECURRING charges only
                            # -> the one-time season pass avoids this entirely

MIX_MONTHLY = 0.40        # share of paid subscribers on the monthly plan
MIX_SEASON = 0.60

SCENARIOS = {
    #                 conv   ai_cost  monthly_churn  cac
    "conservative": (0.020,  0.60,    0.15,          6.0),
    "realistic":    (0.040,  0.35,    0.10,          3.0),
    "optimistic":   (0.070,  0.25,    0.07,          1.5),
}

LADDER = [100, 1_000, 10_000, 100_000]


def infra_cost(users: int) -> float:
    """Fixed monthly infrastructure, stepped by scale."""
    if users <= 200:
        return 0.0        # free tiers only
    if users <= 2_000:
        return 25.0       # managed Postgres + 1 small worker
    if users <= 20_000:
        return 120.0      # bigger DB, dedicated sim worker, CDN
    return 900.0          # multi-worker sim fleet, replicas, object storage


def blended_arpu() -> tuple[float, float]:
    """Return (gross ARPU per paid user per month, net after payment fees)."""
    # monthly = recurring subscription -> card + tax + Billing
    m_gross = PRICE_MONTHLY
    m_fee = PRICE_MONTHLY * (STRIPE_PCT + STRIPE_TAX_PCT + STRIPE_BILLING_PCT) + STRIPE_FIX

    # season pass = one-time payment -> card + tax only, amortised over the season
    s_gross = PRICE_SEASON / SEASON_MONTHS
    s_fee = (PRICE_SEASON * (STRIPE_PCT + STRIPE_TAX_PCT) + STRIPE_FIX) / SEASON_MONTHS

    gross = MIX_MONTHLY * m_gross + MIX_SEASON * s_gross
    net = MIX_MONTHLY * (m_gross - m_fee) + MIX_SEASON * (s_gross - s_fee)
    return gross, net


def main() -> None:
    gross, net = blended_arpu()
    fee_pct = (gross - net) / gross * 100
    print("PRICING")
    print(f"  Monthly plan            EUR {PRICE_MONTHLY:.2f} / month")
    print(f"  Season pass             EUR {PRICE_SEASON:.2f} / {SEASON_MONTHS} months "
          f"(= EUR {PRICE_SEASON/SEASON_MONTHS:.2f} / month)")
    print(f"  Plan mix                {MIX_MONTHLY:.0%} monthly / {MIX_SEASON:.0%} season")
    print(f"  Blended gross ARPU      EUR {gross:.2f} / paid user / month")
    print(f"  Payment fees            EUR {gross-net:.2f}  ({fee_pct:.1f}% of gross)")
    print(f"  Blended net ARPU        EUR {net:.2f} / paid user / month")
    print()

    for sname, (conv, ai, churn, cac) in SCENARIOS.items():
        print(f"=== {sname.upper()}  "
              f"(conv {conv:.1%}, AI EUR {ai:.2f}/paid/mo, "
              f"monthly-plan churn {churn:.0%}, CAC EUR {cac:.2f})")
        hdr = (f"{'Users':>8} {'Paid':>7} {'MRR':>10} {'ARR':>11} "
               f"{'AI':>8} {'Infra':>8} {'GrossMgn':>9} {'Contrib/mo':>11} {'LTV':>8} {'LTV/CAC':>8}")
        print(hdr)
        print("-" * len(hdr))
        for users in LADDER:
            paid = users * conv
            mrr_gross = paid * gross
            mrr_net = paid * net
            ai_cost = paid * ai
            inf = infra_cost(users)
            contrib = mrr_net - ai_cost - inf
            gm = contrib / mrr_gross * 100 if mrr_gross else 0.0
            # blended lifetime: monthly plan 1/churn months; season pass
            # 10 months + 55% renewal -> 10/(1-0.55) months
            life_m = MIX_MONTHLY * (1 / churn) + MIX_SEASON * (SEASON_MONTHS / 0.45)
            ltv = (net - ai) * life_m
            print(f"{users:>8,} {paid:>7,.0f} {mrr_gross:>10,.0f} {mrr_gross*12:>11,.0f} "
                  f"{ai_cost:>8,.0f} {inf:>8,.0f} {gm:>8.1f}% {contrib:>11,.0f} "
                  f"{ltv:>8,.0f} {ltv/cac:>8.1f}")
        print()

    # --- AI cost bottom-up sanity check -------------------------------------
    print("AI COST BOTTOM-UP (per paid user per gameweek)")
    jobs = [
        # name, input tokens, output tokens, calls per gameweek
        ("Deadline Brief",        8_000, 1_200, 1),
        ("Ask-the-Gaffer Q&A",    5_000,   500, 4),
        ("Gameweek Recap",        6_000,   800, 1),
        ("Rival dossier refresh", 4_000,   600, 2),
    ]
    bands = {  # USD per 1M tokens (input, output) - re-verify at build time
        "small  (~$0.30/$2.50)": (0.30, 2.50),
        "mid    (~$2.00/$12.00)": (2.00, 12.00),
    }
    for bname, (pin, pout) in bands.items():
        tot_in = sum(i * c for _, i, _, c in jobs)
        tot_out = sum(o * c for _, _, o, c in jobs)
        usd_gw = tot_in / 1e6 * pin + tot_out / 1e6 * pout
        usd_mo = usd_gw * 4          # ~4 gameweeks per month
        print(f"  {bname}: {tot_in:,} in + {tot_out:,} out per GW "
              f"= ${usd_gw:.4f}/GW  ~= ${usd_mo:.3f}/month")
    print("  Headroom assumption used in scenarios: EUR 0.25-0.60/paid user/month "
          "(5-15x the bottom-up figure) to absorb power users, retries and caching misses.")
    print()

    # --- Break-even ---------------------------------------------------------
    print("BREAK-EVEN (realistic scenario, EUR 25/mo infra tier)")
    conv, ai, churn, cac = SCENARIOS["realistic"]
    per_paid = net - ai
    print(f"  Contribution per paid user   EUR {per_paid:.2f}/month")
    print(f"  Paid users to cover EUR 25   {25/per_paid:.1f}")
    print(f"  Registered users needed      {25/per_paid/conv:.0f}")
    print(f"  Paid users for EUR 1k MRR    {1000/gross:.0f}  "
          f"(= {1000/gross/conv:,.0f} registered users)")


if __name__ == "__main__":
    main()

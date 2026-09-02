"""Weighted opportunity scoring model.

Criteria are scored 1-10. Two criteria are inverted for readability:
  competition  = EASE of competing (10 = wide open, 1 = brutal)
  cost         = ability to run cheaply (10 = near-zero marginal cost)
"""

WEIGHTS = {
    "demand": 10,        # strength of the underlying desire/problem
    "value": 7,          # value intensity across the 11 mechanisms
    "freq": 7,           # how often the need recurs
    "wtp": 10,           # realistic willingness to pay
    "subfit": 7,         # does recurring payment make sense
    "ret": 9,            # why users continue
    "ai": 6,             # genuine AI leverage (not cosmetic)
    "diff": 8,           # can it be meaningfully different
    "comp": 5,           # ease of the competitive landscape
    "size": 5,           # addressable market
    "aud": 3,            # fit with 15-35
    "acq": 6,            # can users realistically be reached
    "viral": 4,          # natural sharing / invitation
    "seo": 4,            # search-driven traffic potential
    "mvp": 5,            # core hypothesis testable in ~2 weeks
    "cost": 2,           # runs inside a EUR 50-200 budget
    "rev": 2,            # ceiling as a business
}
assert sum(WEIGHTS.values()) == 100, sum(WEIGHTS.values())

K = list(WEIGHTS.keys())

# name: [demand, value, freq, wtp, subfit, ret, ai, diff, comp, size, aud, acq, viral, seo, mvp, cost, rev]
OPPS = {
 "01 Overtake - FPL rival-aware decision engine":      [8,8,9,7,8,8,7,8,5,6,9,8,9,7,9,9,6],
 "02 Short-form idea/outlier engine for creators":     [9,7,9,8,8,6,7,4,3,9,9,6,6,6,6,6,8],
 "03 Co-DM - TTRPG campaign assistant":                [7,8,8,6,8,8,9,7,6,5,7,6,7,7,6,5,5],
 "04 Vinted/second-hand seller copilot":               [9,8,8,8,8,7,7,5,3,8,8,6,6,7,5,5,7],
 "05 AI chess improvement coach (Lichess)":            [6,6,8,6,7,6,6,4,3,6,8,5,4,5,7,5,4],
 "06 LoL/Valorant AI improvement coach":               [8,6,9,5,7,6,6,3,2,8,9,5,5,5,5,4,5],
 "07 Curriculum-specific AI study companion":          [8,7,7,5,6,5,7,5,4,5,8,5,5,6,6,5,4],
 "08 AI CV + job application tailoring for students":  [8,7,5,6,4,3,5,3,3,8,8,5,3,6,7,6,5],
 "09 Student flat-hunting copilot (DACH)":             [8,8,6,7,4,3,6,6,6,5,8,5,4,6,5,4,4],
 "10 AI dating conversation coach":                    [8,7,8,7,7,5,5,3,3,8,8,4,3,5,7,6,6],
 "11 AI meal planner + grocery optimiser":             [7,6,8,5,7,5,5,2,2,8,6,4,3,5,7,6,5],
 "12 AI personal finance for young Europeans":         [7,6,5,5,5,5,5,4,3,7,7,4,3,6,5,5,5],
 "13 TCG collection tracker + scanner":                [8,7,7,7,7,7,6,4,3,7,8,5,6,7,4,5,6],
 "14 Sneaker/streetwear resale portfolio":             [6,5,5,5,5,5,5,3,4,6,8,4,5,6,5,4,4],
 "15 AI travel itinerary builder":                     [7,5,3,4,2,2,4,2,2,8,7,4,4,6,7,5,4],
 "16 AI language conversation partner":                [8,6,8,6,8,5,6,3,2,9,8,4,3,5,6,4,6],
 "17 AI journaling / self-insight":                    [6,6,8,5,7,5,6,4,4,6,7,4,2,4,7,6,4],
 "18 AI astrology / personality entertainment":        [7,7,8,6,7,6,5,3,4,7,8,6,7,6,8,6,5],
 "19 Steam backlog 'what to play next' engine":        [6,5,5,3,4,4,5,5,7,6,9,5,5,5,8,7,3],
 "20 Music taste analytics (Spotify)":                 [6,5,5,3,4,4,4,4,5,7,9,6,8,5,6,6,3],
 "21 Climbing/bouldering training coach":              [6,7,7,6,8,7,6,6,7,4,7,5,4,5,6,7,4],
 "22 Padel improvement + match logging":               [6,6,6,6,7,6,5,6,7,4,6,5,4,5,6,7,4],
 "23 Anime/manga tracker + recommender":               [6,5,7,3,4,5,4,3,3,7,9,5,5,5,7,6,3],
 "24 AI quiz night generator for friend groups":       [6,7,5,4,5,5,6,6,7,6,8,5,8,5,8,7,3],
 "25 Contract / scam checker for young adults":        [7,8,4,5,3,3,6,5,6,6,7,4,4,7,6,6,4],
 "26 Thumbnail/title CTR predictor":                   [7,7,8,7,7,6,8,5,4,7,8,5,5,5,5,5,6],
 "27 Twitch clip finder + highlight editor":           [6,6,7,6,7,6,7,5,5,6,8,5,6,4,4,3,5],
 "28 Tech purchase 'second opinion' advisor":          [6,5,3,3,2,2,4,3,3,7,7,4,3,8,6,5,3],
 "29 Wardrobe stylist from your own closet":           [7,6,7,5,6,5,6,4,4,8,8,5,6,5,5,4,5],
 "30 End-to-end faceless-channel pipeline":            [8,7,8,7,8,5,7,4,3,7,8,5,5,5,3,2,6],
}

def ranked():
    rows = []
    for name, vals in OPPS.items():
        assert len(vals) == len(K), (name, len(vals))
        d = dict(zip(K, vals))
        total = sum(d[k] * WEIGHTS[k] for k in K) / 100.0
        rows.append((total, name, d))
    rows.sort(reverse=True, key=lambda r: r[0])
    return rows


if __name__ == "__main__":
    rows = ranked()
    print(f"{'#':>3}  {'Opportunity':<52} {'Score':>6}")
    print("-" * 66)
    for i, (total, name, d) in enumerate(rows, 1):
        print(f"{i:>3}  {name:<52} {total:>6.2f}")

    print()
    print("Top 5 criterion detail:")
    hdr = "  ".join(f"{k:>6}" for k in K)
    print(f"{'':<52}  {hdr}")
    for total, name, d in rows[:5]:
        line = "  ".join(f"{d[k]:>6}" for k in K)
        print(f"{name:<52}  {line}")

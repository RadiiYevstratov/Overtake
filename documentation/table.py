"""Emit the comparison table required by section 51 of the brief."""
from score import OPPS, WEIGHTS, K

META = {
 "01": ("18-30 FPL mini-league players", "Beat my friends", "Status / Better decisions"),
 "02": ("18-30 short-form creators", "Grow and earn", "Better decisions / Saved time"),
 "03": ("20-35 Dungeon Masters", "Run a good game for friends", "Saved time / Self-expression"),
 "04": ("16-30 EU resellers", "Earn side income", "Saved time / Better decisions"),
 "05": ("15-35 online chess players", "Gain rating", "Better decisions / Status"),
 "06": ("15-28 ranked gamers", "Climb rank", "Status / Better decisions"),
 "07": ("16-19 exam candidates", "Pass the exam", "Anxiety reduction"),
 "08": ("19-26 job seekers", "Get callbacks", "Anxiety reduction / Saved time"),
 "09": ("18-27 students relocating", "Secure a flat", "Anxiety reduction / Convenience"),
 "10": ("18-30 app daters", "Be liked", "Status / Anxiety reduction"),
 "11": ("20-35 home cooks", "Stop deciding daily", "Convenience / Saved time"),
 "12": ("20-32 first salaries", "Not mess up money", "Anxiety reduction"),
 "13": ("15-32 card collectors", "Know what I own", "Curiosity / Status"),
 "14": ("16-28 resale collectors", "Track value", "Status / Better decisions"),
 "15": ("20-35 travellers", "Plan a trip", "Convenience"),
 "16": ("16-35 language learners", "Actually speak", "Personalisation"),
 "17": ("18-32 journallers", "Understand myself", "Curiosity / Anxiety reduction"),
 "18": ("16-30, female-skewing", "Be seen / be known", "Entertainment / Curiosity"),
 "19": ("17-35 PC gamers", "Escape the backlog", "Convenience / Curiosity"),
 "20": ("16-30 music listeners", "Show my taste", "Status / Self-expression"),
 "21": ("18-35 climbers", "Climb harder", "Personalisation / Status"),
 "22": ("22-40 padel players", "Improve", "Personalisation / Social"),
 "23": ("15-28 anime fans", "Find the next show", "Curiosity"),
 "24": ("16-30 friend groups", "Have a fun night", "Entertainment / Social"),
 "25": ("18-30 first contracts", "Avoid a costly mistake", "Anxiety reduction"),
 "26": ("18-32 YouTubers", "Higher CTR", "Better decisions"),
 "27": ("18-30 streamers", "Repurpose streams", "Saved time"),
 "28": ("20-35 buyers", "Buy the right thing", "Better decisions"),
 "29": ("17-30 fashion-aware", "Look good daily", "Self-expression / Status"),
 "30": ("18-30 channel operators", "Passive income", "Saved time / Convenience"),
}

rows = []
for name, vals in OPPS.items():
    d = dict(zip(K, vals))
    total = sum(d[k] * WEIGHTS[k] for k in K) / 100.0
    rows.append((total, name, d))
rows.sort(reverse=True, key=lambda r: r[0])

print("| # | Opportunity | Audience | Primary motivation | Value mechanism | Demand | Pay | Retention | AI | Competition* | MVP | **Overall** |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, (total, name, d) in enumerate(rows, 1):
    num = name[:2]
    label = name[3:]
    aud, mot, mech = META[num]
    print(f"| {i} | {label} | {aud} | {mot} | {mech} | {d['demand']} | {d['wtp']} | "
          f"{d['ret']} | {d['ai']} | {d['comp']} | {d['mvp']} | **{total:.2f}** |")

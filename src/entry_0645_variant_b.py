# ADDED AFTER the pre-registered result (which called 2026-10-14 LONG): direction = sign(09:45 open - prior session close).
import datetime as dt, json, math, sys
import numpy as np
sys.path.insert(0, '/Users/anupampatil/zero-dte-lab/src')
import key_times_study as k
import entry_0645_study as e
k.LAST_SETTLED = dt.date(2026, 10, 14)
days, src, info = k.load_bars()
ds = sorted(days); rows = []
prev_close = None
for d in ds:
    g = days[d].set_index("m")
    pc = prev_close
    prev_close = float(g["close"].iloc[-1])
    if pc is None or not {585, 600, 645, 705}.issubset(g.index): continue
    o945 = float(g.loc[585, "open"]); s = 1.0 if o945 > pc else -1.0 if o945 < pc else 0
    if s == 0: continue
    close = float(g["close"].iloc[-1])
    r = {"date": str(d), "gap_pct": o945 / pc - 1, "dir": "long" if s > 0 else "short"}
    for nm, m in (("15", 600), ("60", 645), ("2h", 705)):
        r["b_" + nm] = s * (float(g.loc[m, "open"]) - o945)
    r["b_close"] = s * (close - o945)
    rows.append(r)
out = {}
for name, sample in (("all_days", rows), ("big_move_days", [r for r in rows if abs(r["gap_pct"]) >= 0.003])):
    out[name] = {ex: e.summarize(sample, "b_" + ex) for ex in ("15", "60", "2h", "close")}
out["today"] = rows[-1]
json.dump(out, open('/Users/anupampatil/zero-dte-lab/results/entry_0645_variant_b.json', 'w'), indent=1)
for name in ("all_days", "big_move_days"):
    for ex in ("15", "60", "2h", "close"):
        m = out[name][ex]; print(name, ex, "n", m["n"], "win %.1f%%" % (100 * m["win"]), "mean $%.3f" % m["mean_usd"], "t %.2f" % m["t"], "total $%.0f" % m["total_usd"])
print("today", out["today"])

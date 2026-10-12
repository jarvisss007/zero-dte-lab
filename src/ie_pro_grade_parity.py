"""Grade parity: does the port's A / A+ / B grade, computed at the bar of each chart label, equal the grade the chart printed?
Evidence for the A+-only question (2026-10-11). Reads data/paper/chart_labels_2026-09-30_10-09.csv (30 labels transcribed from his
screenshots, entry E = the close of a real 5m bar on 30 of 30) and the FROZEN cleaned seed bars. Counts nothing, places nothing.
Run: /opt/anaconda3/bin/python src/ie_pro_grade_parity.py > results/IE_PRO_GRADE_PARITY_2026-10-11.txt
A label is matched to the bar whose close equals E within a cent on that day, within 15 minutes of the transcribed time (the
transcribed times come from screenshot positions)."""
from pathlib import Path
import sys
import pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import ie_pro_one_trigger as T, ie_pro_trigger as P, paper_bars as B

lab = pd.read_csv(HERE.parent / "data" / "paper" / "chart_labels_2026-09-30_10-09.csv", dtype={"day_mmdd": str})
df = B.clean(B.load(HERE.parent / "data" / "paper" / "bars_seed_2026-10-09.csv"))
r = P.run(df, htf_mode="developing")
r["pt"] = r.ts.dt.tz_convert("America/Los_Angeles"); r["d"] = r.pt.dt.strftime("%m-%d"); r["hm"] = r.pt.dt.strftime("%H:%M")
c = r.close.to_numpy(float); e9, e21 = T.ema(c, 9), T.ema(c, 21)
mins = lambda h: int(h[:2]) * 60 + int(h[3:])


def grade(i, long_):
    x = r.loc[i]
    rs = (x.rsi > 63) if long_ else (x.rsi < 37)
    vs = bool(x.volume > x.vol_ma * 1.5) if x.vol_ma == x.vol_ma else False
    sep = ((e9[i] - e21[i]) > x.atr * 0.3) if long_ else ((e21[i] - e9[i]) > x.atr * 0.3)
    return "A+" if (rs and vs and sep) else "A" if (rs or vs) else "B"


rows = []
for _, l in lab.iterrows():
    cand = r[(r.d == l.day_mmdd) & ((r.close - l.E).abs() < 0.0151)]
    cand = cand[[abs(mins(h) - mins(l.bar_time_pt_approx)) <= 15 for h in cand.hm]]
    if cand.empty:
        rows.append((l.day_mmdd, l.bar_time_pt_approx, l.side, l.chart_grade, None, None, "no bar (post-close bars are dropped)")); continue
    i = int(min(cand.index, key=lambda k: abs(mins(r.hm[k]) - mins(l.bar_time_pt_approx))))
    rows.append((l.day_mmdd, r.hm[i], l.side, l.chart_grade, grade(i, l.side == "L"), "06:30" <= r.hm[i] <= "12:55", ""))
t = pd.DataFrame(rows, columns=["day", "bar_pt", "side", "chart", "port", "rth", "note"])
print(f"{len(lab)} labels; matched to a bar {t.port.notna().sum()}; unmatched {t.port.isna().sum()} (post-close labels)\n")
for name, sub in (("REGULAR HOURS (the only tradable ones)", t[t.rth == True]), ("PREMARKET (volume is 0 in the free feed)", t[t.rth == False])):
    print(f"== {name}: n {len(sub)}, grade equal {int((sub.chart == sub.port).sum())}")
    print(pd.crosstab(sub.chart, sub.port, rownames=["chart"], colnames=["port"]).to_string())
    a, p = sub[sub.chart == "A+"], sub[sub.port == "A+"]
    print(f"chart A+ {len(a)} -> port A+ on {int((a.port == 'A+').sum())}; port A+ {len(p)} -> chart A+ on {int((p.chart == 'A+').sum())}\n")
print(t[t.port.notna()].to_string(index=False))

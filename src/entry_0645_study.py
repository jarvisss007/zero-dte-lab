"""entry_0645_study.py — "I think I should trade at 6:45am daily": enter at 06:45 PT with the open's direction, and hold?

Asked 2026-10-14 (20:00 PT) after a CPI day on which SPY fell from about 776.4 at 06:45 PT to a 769.60 close: "i think i
should trade at 6:45am daily can you test this thesis ... i was lazy today ... could have made a lot of money by just
holding onto my positions".

PRE-DECLARED before any data was read (committed first):
DATA  SPY 5-min regular-session bars, Alpaca IEX 2020-07-27 .. 2026-07-10 + Yahoo 5m for the last 60 days, through the
      last settled session (key_times_study.load_bars, unchanged).
RULE  06:45 PT = 09:45 ET. Direction = the sign of the first 15 minutes: open of the 09:45 bar minus open of the 09:30 bar
      (zero = no trade). Entry = open of the 09:45 bar, in that direction.
EXITS (each scored separately; one SPY share, no costs):
      15 MIN    = open of the 10:00 bar (added at his request, 20:0x PT, before any data was read)
      CLOCK 60  = open of the 10:45 bar (his Exit Card's clock)
      TWO HOURS = open of the 11:45 bar
      CLOSE     = close of the session's last bar ("just holding")
RESULT per day = SPY dollars moved in the trade's direction. Win = more than zero.
BASELINES on the same days and windows: ALWAYS LONG (SPY drifts up) and FADE (the opposite direction).
CONDITIONAL (one, pre-named): days whose first 15 minutes moved at least 0.30% (big opening moves, like today's).
OPTIONS VIEW (approximate, labelled so): an at-the-money same-day option bought at 06:45 costs roughly
      0.4 x (prior day's VIX/100) x spot x sqrt(hours left / (252 x 6.5)); held to the close it pays only if SPY's move in the
      trade's direction beats that premium. Share of days it would have.
LUCK  4 exits x 2 samples = 8 looks: about a 34% chance one shows |t| >= 2 by luck.
OUTPUT results/entry_0645_study.json. A description of SPY, not a signal and not a trade (sim-only, his Rule 7).
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import key_times_study as k  # noqa: E402

OUT = ROOT / "results" / "entry_0645_study.json"
M0930, M0945, M1000, M1045, M1145 = 570, 585, 600, 645, 705
BIG = 0.0030


def tstat(x):
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else None


def summarize(rows, key):
    v = np.array([r[key] for r in rows if r[key] is not None])
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "win": float((v > 0).mean()), "mean_usd": float(v.mean()), "median_usd": float(np.median(v)),
            "total_usd": float(v.sum()), "t": tstat(v), "best": float(v.max()), "worst": float(v.min())}


def vix_daily():
    import yfinance as yf
    v = yf.download("^VIX", period="10y", interval="1d", progress=False, auto_adjust=False)
    if hasattr(v.columns, "levels"):
        v.columns = v.columns.get_level_values(0)
    return {d.date(): float(c) for d, c in v["Close"].dropna().items()}


def main():
    k.LAST_SETTLED = dt.date.today() if dt.datetime.now().hour >= 14 else dt.date.today() - dt.timedelta(days=1)
    days, src, info = k.load_bars()
    vix = vix_daily()
    rows = []
    for d in sorted(days):
        g = days[d].set_index("m")
        if not {M0930, M0945, M1000, M1045, M1145}.issubset(g.index):
            continue
        o930, o945 = float(g.loc[M0930, "open"]), float(g.loc[M0945, "open"])
        first = o945 - o930
        if first == 0:
            continue
        sgn = 1.0 if first > 0 else -1.0
        close = float(g["close"].iloc[-1])
        x15, x60, x2h = float(g.loc[M1000, "open"]), float(g.loc[M1045, "open"]), float(g.loc[M1145, "open"])
        prior = [x for x in vix if x < d]
        v = vix[max(prior)] if prior else None
        hours_left = (g.index.max() + 5 - M0945) / 60
        prem = 0.4 * v / 100 * o945 * math.sqrt(hours_left / (252 * 6.5)) if v else None
        rows.append({"date": str(d), "first15": first, "first15_pct": first / o930, "dir": "long" if sgn > 0 else "short",
                     "entry": o945, "mom_15": sgn * (x15 - o945), "mom_60": sgn * (x60 - o945), "mom_2h": sgn * (x2h - o945), "mom_close": sgn * (close - o945),
                     "long_15": x15 - o945, "long_60": x60 - o945, "long_2h": x2h - o945, "long_close": close - o945,
                     "fade_15": -sgn * (x15 - o945), "fade_60": -sgn * (x60 - o945), "fade_2h": -sgn * (x2h - o945), "fade_close": -sgn * (close - o945),
                     "premium_est": prem,
                     "opt_close_pays": (sgn * (close - o945) > prem) if prem else None})
    big = [r for r in rows if abs(r["first15_pct"]) >= BIG]
    rep = {"asked": "2026-10-14", "data": {"from": rows[0]["date"], "to": rows[-1]["date"], "days": len(rows),
                                           "big_open_days": len(big)}, "rule": "momentum of the first 15 minutes, entered 09:45 ET"}
    for name, sample in (("all_days", rows), ("big_open_days", big)):
        rep[name] = {}
        for ex in ("15", "60", "2h", "close"):
            rep[name][ex] = {"momentum": summarize(sample, f"mom_{ex}"), "always_long": summarize(sample, f"long_{ex}"),
                             "fade": summarize(sample, f"fade_{ex}")}
        pays = [r["opt_close_pays"] for r in sample if r["opt_close_pays"] is not None]
        rep[name]["option_held_to_close_pays_share"] = float(np.mean(pays)) if pays else None
        prem = [r["premium_est"] for r in sample if r["premium_est"]]
        rep[name]["premium_est_median"] = float(np.median(prem)) if prem else None
    yr = {}
    for r in rows:
        yr.setdefault(r["date"][:4], []).append(r["mom_close"])
    rep["by_year_close"] = {y: {"n": len(v), "win": float(np.mean(np.array(v) > 0)), "total_usd": float(np.sum(v))}
                            for y, v in yr.items()}
    rep["last_20"] = rows[-20:]
    rep["today"] = rows[-1]
    OUT.write_text(json.dumps(rep, indent=1, default=str))  # BOOK-001: research one-off; sole writer, no reader of this file (grep 2026-10-15)
    print(json.dumps({k_: rep[k_] for k_ in ("data", "all_days", "big_open_days", "by_year_close", "today")}, indent=1,
                     default=str)[:6000])


if __name__ == "__main__":
    main()

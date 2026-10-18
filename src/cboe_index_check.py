"""
cboe_index_check.py -- pre-registered 2026-10-17 (Sat ~22:30 PT). Rules written and committed BEFORE the CBOE
index files were read for any number. Nothing in this docstring changes after the first run; additions go in a
dated ADDED block at the bottom.

QUESTION (his "ok", 2026-10-17): the VRP defined-risk study (fca1f28) found the option premium real on a MODEL,
and said the condor's answer hangs on the price level k (k = 0.939 x VIX9D; at 0.9k the condor nearly vanishes).
CBOE publishes daily histories of strategy indexes built from REAL S&P 500 option prices. Do real prices show the
premium, and what price level k* do they imply for the model?

DATA
  CBOE daily index histories, https://cdn.cboe.com/api/global/us_indices/daily_prices/<X>_History.csv:
    WPUT  one-week ATM put-write, collateralised in T-bills (file from 2006-01-31)
    PUT   one-month ATM put-write, collateralised (file from 1991-03-04)
    BXM   one-month ATM buy-write (file from 2002-03-22)
    CNDR  one-month iron condor, collateralised (file from 1986-06-20)
  Yahoo: ^SP500TR (S&P 500 total return, 1988+), ^IRX (13-week T-bill yield) for the cash leg.
  The frozen VRP study's calibration and data (results/vrp_defined_risk_study.json, data/vrp/).
  CBOE indexes are frictionless (priced at mid/VWAP, no spread): costs are haircut below.
  DISCLOSED: during the availability check (before this file existed) the first and last row of each CBOE file were
  printed: WPUT 100 (2006-01-31) -> 263.03, PUT 153.5 (1991-03-04) -> 3691.65, CNDR 100 (1986-06-20) -> 828.89,
  BXM 584.3 (2002-03-22) -> 2553.94 (all 2026-10-16). That reveals each index's long-run growth, not any test here.

SAMPLING: every series at the last session of each ISO week; returns between consecutive week-ends. Cash return
for a week = IRX/100 x calendar days / 365, IRX taken at the start of the week. Excess = return - cash.

COUNTED LOOKS (5)
  R1 WPUT 2006-2026, R2 PUT 1991-2026, R3 BXM 2002-2026, R4 CNDR 1986-2026: mean weekly excess over T-bills.
  R5 the model: k* = the k at which the frozen model's weekly ATM cash-secured put-write (sell at the Friday close,
     settle at the next Friday close, zero cost, vol = k x VIX9D) earns the same mean weekly excess as real WPUT over
     the same weeks. Then the frozen iron condor (sell +-1 move, buy +-2, measured skew, 1x measured cost) at k*.

VERDICT BAR (written now)
  R1, R2, R3 "premium real at real prices": mean excess > 0 with Newey-West (lag 4) t >= 2 AFTER the haircut
     (WPUT 3 bp a week; PUT and BXM 3 bp a month = 0.7 bp a week), AND Sharpe >= the S&P total-return Sharpe over the
     same weeks.
  R4 "real condor": mean excess > 0 with NW t >= 2 after a 10 bp a month haircut (2.3 bp a week), AND > 0 in each era
     1986-2007, 2008-2019, 2020-2026.
  R5 "the model's condor at the real price level": IC mean > 0 with NW t >= 2 at k*, over 2006-2026 AND 1990-2026.
     Reading rule: k* >= 0.845 (0.9 x 0.939) -> the model's price level stands. k* < 0.845 -> the model was too
     generous, and the condor is judged at k*.
  Haircuts at 2x are reported (not a separate look). Anything that passes goes to edge-refute before it is called
  an edge. No desk (COUNCIL-021), sim only (Rule 7), naked selling stays blocked (EV-3).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import vrp_defined_risk_study as V  # noqa: E402  (the frozen model: pricing, simulate, nw_t)

DATA = ROOT / "data" / "cboe"
OUT = ROOT / "results" / "cboe_index_check.json"
INDEXES = ("WPUT", "PUT", "BXM", "CNDR")
HAIRCUT_BP_WEEK = {"WPUT": 3.0, "PUT": 3.0 * 12 / 52, "BXM": 3.0 * 12 / 52, "CNDR": 10.0 * 12 / 52}
ERAS = {"1986_2007": ("1986-01-01", "2007-12-31"), "2008_2019": ("2008-01-01", "2019-12-31"),
        "2020_2026": ("2020-01-01", "2026-12-31")}
K_FROZEN = 0.939


def fetch():
    import datetime as dt
    import urllib.request
    import yfinance as yf
    DATA.mkdir(parents=True, exist_ok=True)
    for x in INDEXES:
        req = urllib.request.Request(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{x}_History.csv",
                                     headers={"User-Agent": "Mozilla/5.0"})
        (DATA / f"{x}.csv").write_bytes(urllib.request.urlopen(req, timeout=60).read())
    for t, fn in (("^SP500TR", "sp500tr.csv"), ("^IRX", "irx.csv")):
        df = yf.download(t, start="1985-01-01", end="2026-10-17", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df[["Close"]].dropna().rename_axis("Date").to_csv(DATA / fn)
    (DATA / "PULLED.txt").write_text(f"cboe cdn daily_prices + yahoo yfinance {yf.__version__}; pulled "
                                     f"{dt.datetime.now().isoformat(timespec='seconds')}\n")


def load_cboe(x):
    df = pd.read_csv(DATA / f"{x}.csv")
    df.columns = [c.strip().upper() for c in df.columns]
    s = pd.Series(pd.to_numeric(df[x], errors="coerce").values, index=pd.to_datetime(df["DATE"], format="%m/%d/%Y"))
    return s.dropna().sort_index()


def load_close(fn):
    return pd.read_csv(DATA / fn, parse_dates=["Date"]).set_index("Date").Close.sort_index()


def week_ends(idx):
    d = pd.DatetimeIndex(idx)
    return pd.DatetimeIndex(pd.Series(d, index=d).groupby([d.isocalendar().year, d.isocalendar().week]).max().values)


def weekly(series, ends):
    s = series.reindex(series.index.union(ends)).ffill().reindex(ends)
    return s


def cash_returns(irx, ends):
    r = irx.reindex(irx.index.union(ends)).ffill().reindex(ends) / 100
    days = pd.Series(ends[1:] - ends[:-1], index=ends[1:]).dt.days
    return pd.Series(r.values[:-1] * days.values / 365, index=ends[1:])


def stats(x, per_year=52):
    x = np.asarray(x, float)
    eq = np.cumprod(1 + x)
    dd = eq / np.maximum.accumulate(eq) - 1
    return {"weeks": int(len(x)), "mean_bp": round(float(x.mean()) * 1e4, 2), "nw_t": round(V.nw_t(x), 2),
            "sharpe_annual": round(float(x.mean() / x.std(ddof=1) * math.sqrt(per_year)), 3),
            "max_dd_pct": round(float(dd.min()) * 100, 1)}


def model_putwrite_excess(gspc, sig, k, ends):
    """The frozen model's weekly ATM cash-secured put-write: excess return over cash per week, zero cost."""
    c = gspc.Close
    out = {}
    for e0, e1 in zip(ends[:-1], ends[1:]):
        if e0 not in c.index or e1 not in c.index or e0 not in sig.index or pd.isna(sig.loc[e0]):
            continue
        S, ST = float(c.loc[e0]), float(c.loc[e1])
        T = (e1 - e0).days / 365
        prem = V.bs(S, S, T, k * float(sig.loc[e0]), call=False)
        out[e1] = (prem - max(S - ST, 0.0)) / S
    return pd.Series(out)


def run():
    tr, irx = load_close("sp500tr.csv"), load_close("irx.csv")
    idx = {x: load_cboe(x) for x in INDEXES}
    res = {"meta": {"haircut_bp_week": HAIRCUT_BP_WEEK, "files": {x: [str(s.index[0].date()), str(s.index[-1].date()), len(s)]
                                                                    for x, s in idx.items()}}}
    for x, s in idx.items():
        ends = week_ends(s.index)
        w = weekly(s, ends)
        ret = w.pct_change().dropna()
        cash = cash_returns(irx, ends).reindex(ret.index)
        ex = (ret - cash).dropna()
        hc = HAIRCUT_BP_WEEK[x] / 1e4
        blk = {"gross": stats(ex), "net": stats(ex - hc), "net_2x": stats(ex - 2 * hc)}
        trw = weekly(tr, ends).pct_change().reindex(ex.index)
        both = pd.concat([ex - hc, trw - cash.reindex(ex.index)], axis=1).dropna()
        blk["vs_sp500tr_same_weeks"] = {"strategy_net": stats(both.iloc[:, 0]), "sp500tr": stats(both.iloc[:, 1]),
                                        "from": str(both.index[0].date())}
        for era, (lo, hi) in ERAS.items():
            sub = (ex - hc)[(ex.index >= lo) & (ex.index <= hi)]
            if len(sub) > 20:
                blk[era] = stats(sub)
        res[x] = blk

    # R5: price level implied by real WPUT
    gspc, vix, vix9d = V.load("gspc.csv"), V.load("vix.csv"), V.load("vix9d.csv")
    a, b, _ = V.vix9d_map(vix, vix9d)
    est = np.exp(a + b * np.log(vix.Close))
    sig = (vix9d.Close.reindex(vix.index).fillna(est) / 100)
    w_ends = week_ends(gspc.index[(gspc.index >= idx["WPUT"].index[0])])
    real = weekly(idx["WPUT"], w_ends).pct_change() - cash_returns(irx, w_ends)
    real = real.dropna()

    def gap(k):
        m = model_putwrite_excess(gspc, sig, k, w_ends).reindex(real.index).dropna()
        return float(m.mean() - real.reindex(m.index).mean()), m
    lo_k, hi_k = 0.3, 1.6
    for _ in range(40):
        mid = (lo_k + hi_k) / 2
        if gap(mid)[0] > 0:
            hi_k = mid
        else:
            lo_k = mid
    k_star = round((lo_k + hi_k) / 2, 4)
    g0, m0 = gap(K_FROZEN)
    _, mstar = gap(k_star)
    res["R5"] = {"k_star": k_star, "k_frozen": K_FROZEN, "k_0.9": round(0.9 * K_FROZEN, 4),
                 "weeks": int(len(real)), "real_wput_mean_excess_bp": round(float(real.mean()) * 1e4, 2),
                 "model_at_k_frozen_mean_excess_bp": round(float(m0.mean()) * 1e4, 2),
                 "model_minus_real_at_k_frozen_bp": round(g0 * 1e4, 2),
                 "weekly_corr_model_real_at_k_star": round(float(np.corrcoef(mstar.values, real.reindex(mstar.index).values)[0, 1]), 3)}
    frozen = json.loads((ROOT / "results" / "vrp_defined_risk_study.json").read_text())
    cal = frozen["calibration"]
    df = V.simulate(gspc, sig[sig.index >= "1990-01-02"], cal, k_star, "measured", 1.0)
    full = df.IC.fillna(0.0)
    post = df[df.entry >= "2006-01-31"].IC.fillna(0.0)
    res["R5"]["IC_at_k_star"] = {"1990_2026": {"mean_r": round(float(full.mean()), 4), "nw_t": round(V.nw_t(full.values), 2),
                                               "win_pct": round(float((df.IC > 0).mean()) * 100, 1)},
                                 "2006_2026": {"mean_r": round(float(post.mean()), 4), "nw_t": round(V.nw_t(post.values), 2)}}
    for s in ("PCS", "CCS"):
        x = df[s].fillna(0.0)
        res["R5"][f"{s}_at_k_star_1990_2026"] = {"mean_r": round(float(x.mean()), 4), "nw_t": round(V.nw_t(x.values), 2)}

    # verdicts
    v = {}
    for x in ("WPUT", "PUT", "BXM"):
        n, cmp_ = res[x]["net"], res[x]["vs_sp500tr_same_weeks"]
        ok = n["mean_bp"] > 0 and n["nw_t"] >= 2 and cmp_["strategy_net"]["sharpe_annual"] >= cmp_["sp500tr"]["sharpe_annual"]
        v[x] = "SUPPORTS (-> edge-refute)" if ok else "NOT SUPPORTED"
    n = res["CNDR"]["net"]
    eras_ok = all(res["CNDR"].get(e, {"mean_bp": -1})["mean_bp"] > 0 for e in ERAS)
    v["CNDR"] = "SUPPORTS (-> edge-refute)" if (n["mean_bp"] > 0 and n["nw_t"] >= 2 and eras_ok) else "NOT SUPPORTED"
    ic = res["R5"]["IC_at_k_star"]
    v["R5_model_condor_at_k_star"] = ("SUPPORTS (-> edge-refute)" if all(ic[p]["mean_r"] > 0 and ic[p]["nw_t"] >= 2 for p in ic)
                                      else "NOT SUPPORTED")
    v["R5_reading"] = "model price level stands" if k_star >= 0.9 * K_FROZEN else "model was too generous; condor judged at k*"
    res["verdicts"] = v
    res["luck_tally"] = {"looks": 5}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    run()

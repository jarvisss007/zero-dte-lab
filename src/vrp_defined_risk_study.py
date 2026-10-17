"""
vrp_defined_risk_study.py -- pre-registered 2026-10-17. The rules below were written and committed BEFORE any
data was pulled, any calibration number was computed, or any P&L was seen. Nothing in this docstring changes
after the first run; additions go in a dated ADDED block at the bottom, labelled as added.

QUESTION (his "ok", 2026-10-17): options cost more than the moves they pay for (zero-dte-lab r17: implied >
realized in all 8 buckets). Does a DEFINED-RISK way of selling that premium on the S&P 500 keep the extra after
the crash years, 1990-2026? Naked selling stays BLOCKED (EV-3); it appears only as a reference line.
This is a study, not a desk (COUNCIL-021) and not a trade (sim only until Rule 7).

DATA (Yahoo, pulled by fetch(); vendor and pull time stamped in data/vrp/PULLED.txt)
  ^GSPC daily close 1990-01-02 .. 2026-10-16: entry price and settlement (SPX weeklies are cash-settled on the
    close; European, so no early exercise).
  ^VIX (1990+), ^VIX9D (2011+), ^VIX1D (2023-04+) daily.
  Recorded SPY 0DTE chains, data/chains/SPY_*.csv (2026-07..2026-10): CALIBRATION ONLY, never P&L.

THE TRADE (every week, no exceptions, no management, held to expiry)
  Entry: the close of the last session of each ISO week. Expiry: the close of the last session of the next ISO
  week. T = calendar days between / 365.
  Weekly ATM vol: sigma = k * VIX9D on the entry day. Before 2011 VIX9D is estimated from VIX with
  ln(VIX9D) = a + b ln(VIX), fitted by OLS on every 2011-2026 day where both exist.
  One expected move: sd = sigma * sqrt(T). Strike at z expected moves: K = S * exp(z * sd).
  Leg price: Black-Scholes, r = q = 0 (forward = spot), vol = sigma * r(z) (the skew ratio below).
  Fills are executable, never mid (Firm Brain: mid vs executable): a sold leg receives price * (1 - h(z)), a
  bought leg pays price * (1 + h(z)).
    IC   iron condor: sell the -1 put and the +1 call, buy the -2 put and the +2 call (EV-23 geometry).
    PCS  put credit spread: sell -1 put, buy -2 put.
    CCS  call credit spread: sell +1 call, buy +2 call.
    NAKED reference only (EV-3 blocked): sell the -1 put and +1 call, no wings. Reported in % of spot.
  P&L per trade in units of max risk: (credit - payoff at expiry) / (wider wing width - credit). A trade whose
  executable credit is <= 0 is not placed (P&L 0, counted as skipped).
  Equity curve: risk f = 2% of equity at max loss each week; cash earns 0. Benchmark: SPX price, same weeks.
  Contracts before Oct 2005 (SPX weeklies' launch) are hypothetical; the premium question still stands.

CALIBRATION (procedure frozen here; the numbers are computed from the recorded chains after this commit and
before any P&L). Per recorded session: the earliest snapshot whose quote date equals the file date (stale
CDN books are skipped, OPT-029).
  C1 k: one-day 1-sd move from the chain = ATM straddle mid / 0.7979. One-day 1-sd move from VIX1D =
     S * VIX1D_open/100 * sqrt(minutes to 16:00 / 525,600). k = median ratio. Convention-free on the chain side.
  C2 skew r(z): z(K) = ln(K/S) / (chain 1-sd move / S). At the OTM option nearest z = -2, -1 (puts) and +1, +2
     (calls): vendor iv(K) / ATM iv (ATM = mean of call and put iv at the strike nearest spot). Median across
     sessions. r(0) = 1; piecewise-linear in z between knots, flat beyond.
  C3 cost h(z): median half-spread / mid at the same four strikes. 0DTE quotes are a conservative stand-in for
     weeklies (smaller premiums, so larger percentage spreads).

HYPOTHESES / COUNTED CELLS (4 looks in this study; deflation uses N = 150 for the repo family)
  V0  model-free premium: weekly implied vol (sigma) > realized vol over the same week (sqrt of the sum of
      squared daily log returns, annualized by T). Reported: % of weeks implied > realized, mean gap in vol
      points, for k = measured and k = 1 (raw VIX9D).
  S-IC, S-PCS, S-CCS: mean P&L per week in units of max risk, primary settings (measured k, r(z), h(z)).

VERDICT BAR (written now). A strategy SUPPORTS only if ALL hold:
  (a) mean P&L > 0 at primary settings with Newey-West (lag 4) t >= 2;
  (b) mean > 0 in EACH era: 1990-2007, 2008-2019, 2020-2026;
  (c) mean > 0 at 2x cost AND at 0.9 k (premium 10% cheaper than measured);
  (d) deflated Sharpe >= 0.95 at N = 150 trials, on the weekly equity returns (skew and kurtosis included),
      with the Sharpe variance taken across the sensitivity grid below.
  Anything else = NOT SUPPORTED. Anything that passes goes to edge-refute before it is called an edge.

SENSITIVITY GRID (reported; also the trial set for the Sharpe variance in (d)):
  3 strategies x cost {0, 1x, 2x} x k {0.9k, k, 1.0} x skew {flat, measured, 2x measured deviation} = 81.

CRASH AUDIT (descriptive): the 15 worst weeks for IC and PCS (SPX move that week, loss in max-risk units, and
"weeks of premium eaten" = loss / mean winning-week P&L); P&L by calendar year with the crash years marked
(1997 1998 2000 2001 2002 2008 2010 2011 2015 2018 2020 2022 2025); the longest drawdown. 1987 predates VIX:
defined risk caps any single week at one max loss, which is stated rather than simulated.
"""
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "vrp"
CHAINS = ROOT / "data" / "chains"
OUT = ROOT / "results" / "vrp_defined_risk_study.json"
RISK_F = 0.02
N_TRIALS = 150
ERAS = {"1990_2007": ("1990-01-01", "2007-12-31"), "2008_2019": ("2008-01-01", "2019-12-31"),
        "2020_2026": ("2020-01-01", "2026-12-31")}
CRASH_YEARS = [1997, 1998, 2000, 2001, 2002, 2008, 2010, 2011, 2015, 2018, 2020, 2022, 2025]
KNOTS = [-2.0, -1.0, 1.0, 2.0]


# ------------------------------------------------------------------ data
def fetch(end="2026-10-17"):
    import yfinance as yf
    DATA.mkdir(parents=True, exist_ok=True)
    for t, fn in (("^GSPC", "gspc.csv"), ("^VIX", "vix.csv"), ("^VIX9D", "vix9d.csv"), ("^VIX1D", "vix1d.csv")):
        df = yf.download(t, start="1989-12-01", end=end, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close"]].dropna(subset=["Close"])
        df.index.name = "Date"
        df.to_csv(DATA / fn)
    (DATA / "PULLED.txt").write_text(f"yahoo yfinance {yf.__version__} auto_adjust=False end={end} "
                                     f"pulled {dt.datetime.now().isoformat(timespec='seconds')}\n")


def load(fn):
    return pd.read_csv(DATA / fn, parse_dates=["Date"]).set_index("Date").sort_index()


# ------------------------------------------------------------------ calibration
def calibrate():
    vix1d = load("vix1d.csv")
    rows = []
    for f in sorted(CHAINS.glob("SPY_*.csv")):
        day = f.stem.split("_")[1]
        df = pd.read_csv(f)
        df = df[df.expiry == day]
        if df.empty:
            continue
        df["qdate"] = df.quote_ts.astype(str).str[:10]
        df = df[df.qdate == day]
        if df.empty:
            continue
        first = df.fetched_at_et.min()
        snap = df[df.fetched_at_et == first].copy()
        S = float(snap.spot.iloc[0])
        t_fetch = pd.Timestamp(first)
        minutes = (pd.Timestamp(f"{day} 16:00:00") - t_fetch).total_seconds() / 60
        if minutes < 60 or pd.Timestamp(day) not in vix1d.index:
            continue
        snap["mid"] = (snap.bid + snap.ask) / 2
        strikes = np.sort(snap.strike.unique())
        katm = strikes[np.argmin(np.abs(strikes - S))]
        c = snap[(snap.strike == katm) & (snap.type == "C")]
        p = snap[(snap.strike == katm) & (snap.type == "P")]
        if c.empty or p.empty:
            continue
        straddle = float(c.mid.iloc[0] + p.mid.iloc[0])
        em = straddle / math.sqrt(2 / math.pi)
        v1d = float(vix1d.loc[pd.Timestamp(day), "Open"]) / 100
        em_vix = S * v1d * math.sqrt(minutes / 525600)
        iv_atm = float((c.iv.iloc[0] + p.iv.iloc[0]) / 2)
        rec = {"day": day, "spot": S, "minutes": round(minutes, 1), "k": em / em_vix}
        for z in KNOTS:
            side = "P" if z < 0 else "C"
            kz = S * math.exp(z * em / S)
            leg = snap[snap.type == side]
            leg = leg.iloc[[int(np.argmin(np.abs(leg.strike.values - kz)))]]
            mid = float(leg.mid.iloc[0])
            rec[f"r_{z:+.0f}"] = float(leg.iv.iloc[0]) / iv_atm if iv_atm > 0 else None
            rec[f"h_{z:+.0f}"] = float((leg.ask.iloc[0] - leg.bid.iloc[0]) / 2 / mid) if mid > 0 else None
        rows.append(rec)
    cal = pd.DataFrame(rows)
    out = {"sessions": len(cal), "first": cal.day.min(), "last": cal.day.max(),
           "k": round(float(cal.k.median()), 4), "k_iqr": [round(float(cal.k.quantile(q)), 4) for q in (0.25, 0.75)]}
    for z in KNOTS:
        out[f"r_{z:+.0f}"] = round(float(cal[f"r_{z:+.0f}"].dropna().median()), 4)
        out[f"h_{z:+.0f}"] = round(float(cal[f"h_{z:+.0f}"].dropna().median()), 4)
    return out, cal


def mf_k(cal, sigma=0.15, T=7 / 365):
    """ADDED 2026-10-17 (C1'): ATM vol / model-free vol for a smile shaped like the measured r(z).
    VIX9D is a model-free variance index (it integrates every OTM strike), so ATM = k' * VIX9D."""
    sd = sigma * math.sqrt(T)
    z = np.linspace(-10, 10, 40001)
    K = np.exp(z * sd)
    dK = np.gradient(K)
    px = np.array([bs(1.0, kk, T, sigma * skew_ratio(zz, cal, "measured"), call=zz > 0) for kk, zz in zip(K, z)])
    return float(sigma / math.sqrt(2 / T * np.sum(px / K ** 2 * dK)))


def vix9d_map(vix, vix9d):
    j = pd.concat([vix.Close.rename("v"), vix9d.Close.rename("v9")], axis=1).dropna()
    b, a = np.polyfit(np.log(j.v), np.log(j.v9), 1)
    return float(a), float(b), len(j)


# ------------------------------------------------------------------ pricing
def ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs(S, K, T, vol, call):
    sd = vol * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    if call:
        return S * ncdf(d1) - K * ncdf(d2)
    return K * ncdf(-d2) - S * ncdf(-d1)


def skew_ratio(z, cal, mode):
    if mode == "flat":
        return 1.0
    xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    ys = [cal["r_-2"], cal["r_-1"], 1.0, cal["r_+1"], cal["r_+2"]]
    r = float(np.interp(z, xs, ys))
    return 1.0 + 2.0 * (r - 1.0) if mode == "2x" else r


def legs(S, T, sigma, cal, skew_mode, cost_mult):
    out = {}
    for z in KNOTS:
        K = S * math.exp(z * sigma * math.sqrt(T))
        px = bs(S, K, T, sigma * skew_ratio(z, cal, skew_mode), call=z > 0)
        out[z] = (K, px, cal[f"h_{z:+.0f}"] * cost_mult)
    return out


def trade(kind, L, ST):
    (kp2, pp2, hp2), (kp1, pp1, hp1), (kc1, pc1, hc1), (kc2, pc2, hc2) = L[-2.0], L[-1.0], L[1.0], L[2.0]
    put_credit = pp1 * (1 - hp1) - pp2 * (1 + hp2)
    call_credit = pc1 * (1 - hc1) - pc2 * (1 + hc2)
    put_pay = max(kp1 - ST, 0) - max(kp2 - ST, 0)
    call_pay = max(ST - kc1, 0) - max(ST - kc2, 0)
    if kind == "PCS":
        credit, pay, width = put_credit, put_pay, kp1 - kp2
    elif kind == "CCS":
        credit, pay, width = call_credit, call_pay, kc2 - kc1
    else:
        credit, pay, width = put_credit + call_credit, put_pay + call_pay, max(kp1 - kp2, kc2 - kc1)
    if credit <= 0:
        return None
    return (credit - pay) / (width - credit)


def naked(L, S, ST):
    kp1, pp1, hp1 = L[-1.0]
    kc1, pc1, hc1 = L[1.0]
    credit = pp1 * (1 - hp1) + pc1 * (1 - hc1)
    pay = max(kp1 - ST, 0) + max(ST - kc1, 0)
    return (credit - pay) / S


# ------------------------------------------------------------------ stats
def nw_t(x, lag=4):
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    g0 = e @ e / n
    s = g0
    for l in range(1, lag + 1):
        g = e[l:] @ e[:-l] / n
        s += 2 * (1 - l / (lag + 1)) * g
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def equity_stats(r, per_year=52):
    r = np.asarray(r, float)
    eq = np.cumprod(1 + r)
    yrs = len(r) / per_year
    dd = eq / np.maximum.accumulate(eq) - 1
    # longest drawdown in weeks
    peak, longest, cur = eq[0], 0, 0
    for v in eq:
        if v >= peak:
            peak, cur = v, 0
        else:
            cur += 1
            longest = max(longest, cur)
    return {"cagr_pct": round((eq[-1] ** (1 / yrs) - 1) * 100, 2),
            "sharpe_annual": round(float(r.mean() / r.std(ddof=1) * math.sqrt(per_year)), 3),
            "max_dd_pct": round(float(dd.min()) * 100, 1), "worst_week_pct": round(float(r.min()) * 100, 2),
            "longest_dd_weeks": int(longest), "final_multiple": round(float(eq[-1]), 3)}


def dsr(r, sr_var, n_trials=N_TRIALS):
    import sys
    sys.path.insert(0, str(Path.home() / "backtest-overfitting"))
    from overfit import deflated_sharpe_ratio
    r = np.asarray(r, float)
    sr = r.mean() / r.std(ddof=1)
    sk = float(pd.Series(r).skew())
    ku = float(pd.Series(r).kurt()) + 3.0
    d, sr0 = deflated_sharpe_ratio(sr, len(r), sr_var, n_trials, skew=sk, kurtosis=ku)
    return {"weekly_sharpe": round(float(sr), 4), "skew": round(sk, 2), "kurtosis": round(ku, 1),
            "sr_benchmark": round(float(sr0), 4), "dsr": round(float(d), 4)}


# ------------------------------------------------------------------ run
def weeks(gspc):
    d = gspc.index
    wk = pd.Series(d, index=d).groupby([d.isocalendar().year, d.isocalendar().week]).max().values
    return [pd.Timestamp(x) for x in wk]


def simulate(gspc, sig, cal, k, skew_mode, cost_mult):
    ends = weeks(gspc)
    recs = []
    c = gspc.Close
    for e0, e1 in zip(ends[:-1], ends[1:]):
        if e0 not in sig.index or pd.isna(sig.loc[e0]):
            continue
        S, ST = float(c.loc[e0]), float(c.loc[e1])
        T = (e1 - e0).days / 365
        sigma = k * float(sig.loc[e0])
        L = legs(S, T, sigma, cal, skew_mode, cost_mult)
        path = c.loc[e0:e1]
        rv = float(np.sum(np.diff(np.log(path.values)) ** 2))
        recs.append({"entry": e0, "expiry": e1, "S": S, "ST": ST, "move_pct": (ST / S - 1) * 100, "sigma": sigma,
                     "realized_vol": math.sqrt(rv / T), "IC": trade("IC", L, ST), "PCS": trade("PCS", L, ST),
                     "CCS": trade("CCS", L, ST), "NAKED_pct_spot": naked(L, S, ST)})
    return pd.DataFrame(recs)


def summarize(df, col):
    x = df[col].dropna().values
    allw = df[col].fillna(0.0).values
    wins = x[x > 0]
    return {"n_weeks": int(len(df)), "n_traded": int(len(x)), "skipped": int(df[col].isna().sum()),
            "mean_r": round(float(allw.mean()), 4), "nw_t": round(nw_t(allw), 2),
            "win_pct": round(float((x > 0).mean()) * 100, 1), "mean_win_r": round(float(wins.mean()), 4) if len(wins) else None,
            "max_loss_weeks": int((x <= -0.999).sum()), "worst_r": round(float(x.min()), 4)}


def run():
    gspc, vix, vix9d = load("gspc.csv"), load("vix.csv"), load("vix9d.csv")
    cal, cal_df = calibrate()
    cal["k_c1_frozen_INVALID"] = cal["k"]
    cal["k_c1_frozen_iqr"] = cal.pop("k_iqr")
    cal["k"] = round(mf_k(cal), 4)
    cal["k_source"] = "C1' model-free consistency (ADDED 2026-10-17); frozen C1 was a time-convention artifact"
    a, b, n_fit = vix9d_map(vix, vix9d)
    est = np.exp(a + b * np.log(vix.Close))
    sig = vix9d.Close.reindex(vix.index).fillna(est) / 100
    sig = sig[sig.index >= "1990-01-02"]
    res = {"meta": {"risk_f": RISK_F, "n_trials": N_TRIALS, "vix9d_map": {"a": round(a, 4), "b": round(b, 4), "n_days": n_fit}},
           "calibration": cal}

    base = simulate(gspc, sig, cal, cal["k"], "measured", 1.0)
    raw = simulate(gspc, sig, cal, 1.0, "measured", 1.0)
    # V0: model-free premium
    res["V0"] = {"weeks": int(len(base)),
                 "pct_implied_gt_realized": round(float((base.sigma > base.realized_vol).mean()) * 100, 1),
                 "mean_gap_vol_pts": round(float((base.sigma - base.realized_vol).mean()) * 100, 2),
                 "raw_vix9d_pct_implied_gt_realized": round(float((raw.sigma > raw.realized_vol).mean()) * 100, 1),
                 "raw_vix9d_mean_gap_vol_pts": round(float((raw.sigma - raw.realized_vol).mean()) * 100, 2)}

    prim = {}
    for s in ("IC", "PCS", "CCS"):
        blk = {"primary": summarize(base, s)}
        for era, (lo, hi) in ERAS.items():
            sub = base[(base.entry >= lo) & (base.entry <= hi)]
            blk[era] = summarize(sub, s)
        r = RISK_F * base[s].fillna(0.0).values
        blk["equity"] = equity_stats(r)
        prim[s] = blk
    spx = base.ST.values / base.S.values - 1
    res["benchmark_spx_price"] = equity_stats(spx)
    nk = base.NAKED_pct_spot.values
    res["naked_reference"] = {"mean_pct_spot": round(float(nk.mean()), 4), "nw_t": round(nw_t(nk), 2),
                              "win_pct": round(float((nk > 0).mean()) * 100, 1), "worst_pct_spot": round(float(nk.min()), 2),
                              "mean_win_pct_spot": round(float(nk[nk > 0].mean()), 4)}

    # sensitivity grid = trial set
    grid, sharpes = {}, []
    for cm in (0.0, 1.0, 2.0):
        for kk, kl in ((0.9 * cal["k"], "0.9k"), (cal["k"], "k"), (1.0, "k=1")):
            for sm in ("flat", "measured", "2x"):
                df = base if (cm == 1.0 and kl == "k" and sm == "measured") else simulate(gspc, sig, cal, kk, sm, cm)
                for s in ("IC", "PCS", "CCS"):
                    x = df[s].fillna(0.0).values
                    grid[f"{s}|cost{cm:g}x|{kl}|skew_{sm}"] = {"mean_r": round(float(x.mean()), 4), "nw_t": round(nw_t(x), 2)}
                    sharpes.append(x.mean() / x.std(ddof=1) if x.std() > 0 else 0.0)
    res["grid"] = grid
    sr_var = float(np.var(sharpes, ddof=1))
    res["grid_sharpe_variance"] = sr_var

    verdicts = {}
    for s in ("IC", "PCS", "CCS"):
        p = prim[s]
        d = dsr(RISK_F * base[s].fillna(0.0).values, sr_var)
        prim[s]["dsr"] = d
        a_ok = p["primary"]["mean_r"] > 0 and p["primary"]["nw_t"] >= 2
        b_ok = all(p[e]["mean_r"] > 0 for e in ERAS)
        c_ok = grid[f"{s}|cost2x|k|skew_measured"]["mean_r"] > 0 and grid[f"{s}|cost1x|0.9k|skew_measured"]["mean_r"] > 0
        d_ok = d["dsr"] >= 0.95
        verdicts[s] = {"a_mean_t": a_ok, "b_all_eras": b_ok, "c_cost_and_k": c_ok, "d_dsr": d_ok,
                       "verdict": "SUPPORTS (-> edge-refute)" if all((a_ok, b_ok, c_ok, d_ok)) else "NOT SUPPORTED"}
    res["primary"] = prim
    res["verdicts"] = verdicts

    # crash audit
    audit = {}
    for s in ("IC", "PCS"):
        x = base[["entry", "move_pct", "sigma", s]].dropna()
        mw = float(x[s][x[s] > 0].mean())
        worst = x.nsmallest(15, s)
        audit[s] = {"mean_win_r": round(mw, 4),
                    "worst15": [{"entry": str(r.entry.date()), "spx_move_pct": round(r.move_pct, 2), "vol_pct": round(r.sigma * 100, 1),
                                 "loss_r": round(float(r[s]), 3), "weeks_of_premium_eaten": round(-float(r[s]) / mw, 1)}
                                for _, r in worst.iterrows()]}
        yr = base.assign(y=base.entry.dt.year).groupby("y")[s].apply(lambda v: float(v.fillna(0).sum()))
        audit[s]["by_year_sum_r"] = {int(k): round(v, 3) for k, v in yr.items()}
        audit[s]["crash_years_sum_r"] = {y: audit[s]["by_year_sum_r"].get(y) for y in CRASH_YEARS}
    res["crash_audit"] = audit
    res["luck_tally"] = {"looks_this_study": 4, "family_n_for_deflation": N_TRIALS}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    base.to_csv(ROOT / "results" / "vrp_defined_risk_weeks.csv", index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    import sys
    if "--fetch" in sys.argv:
        fetch()
    run()


# ADDED 2026-10-17, after the data pull and calibration, BEFORE any P&L was computed (labelled as added):
#  - C1 as frozen is INVALID. It gave k = 2.14 (IQR 2.06-2.23): the 0DTE straddle at ~09:49 ET looked 2.1x the
#    VIX1D move. That is a time-convention mismatch (VIX1D does not annualize intraday time as plain calendar
#    minutes), not a premium; using it would price every weekly option at ~2x and hand the seller a fake win.
#  - Replaced by C1': k = ATM vol / model-free vol of a smile shaped like the measured r(z) (mf_k). VIX9D is a
#    model-free variance index, so this is the consistent mapping. Result 0.939, stable from 10% to 30% vol
#    (flat smile -> exactly 1.0, which checks the integral). The frozen value is kept in the JSON, marked invalid.
#  - C2 (skew ratios) and C3 (spread fractions) are convention-free ratios and stand as frozen.
#  - The bar, the grid (0.9k, k, 1.0) and every other rule are unchanged.

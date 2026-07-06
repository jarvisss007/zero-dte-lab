"""Python port of the r17 Pine strategy (active config: liquidity sweeps,
"OB Primary Trigger" mode) with an HONEST HTF filter.

What it reproduces from r17:
  - swing pivots (5/5), BOS/CHoCH trend state machine
  - liquidity sweeps: wick through the last swing low/high, close back inside
  - entry (primary mode): sweep + trend agreement + candle direction + 15-min
    HTF bias (EMA9>21, close vs session VWAP, RSI vs 50)
  - min 3 bars between signals, opposite signal reverses the position
  - ATR(14) x 1.0 stop, 2.5R target, breakeven stop after a close beyond +1R
  - fills at signal-bar close (process_orders_on_close), commission 0.01%/side
    + 1 tick slippage/side

What it fixes / measures:
  - CAUSAL HTF: bias uses only the last COMPLETED 15-min bar (like the
    security(expr[1], lookahead_on) idiom).
  - LEAKY HTF: reproduces what r17 actually backtested - every LTF bar sees
    its own 15-min bar's FINAL values (up to 14 min of future). Run both to
    measure how much of r17's edge was borrowed from the future.
  - Worst-case intrabar assumption: if stop and target are both inside one
    bar's range, the stop is assumed to fill first.

Run: /opt/anaconda3/bin/python src/sweep_backtest.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data_utils import load_bats, load_minute_closes, minute_to_pseudo_ohlc, atr

RESULTS = Path(__file__).resolve().parent.parent / "results"

PIV = 5
MIN_GAP = 3
ATR_SL = 1.0
TP_RR = 2.5
COMMISSION = 0.0001      # 0.01% per side (r17 setting)
SLIP = 0.01              # 1 tick per side


# ---------------------------------------------------------------- indicators
def rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    rs = rma(up, n) / rma(dn, n)
    return 100 - 100 / (1 + rs)


def session_vwap(df: pd.DataFrame) -> pd.Series:
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"] if "volume" in df and df["volume"].notna().any() \
        else pd.Series(1.0, index=df.index)
    date = df["ts"].dt.date
    pv = (hlc3 * vol).groupby(date).cumsum()
    vv = vol.groupby(date).cumsum()
    return pv / vv


def htf_bias(df: pd.DataFrame, htf: str, leaky: bool) -> pd.DataFrame:
    """15-min (or htf) bias flags aligned onto the trading timeframe."""
    o = df.set_index("ts").resample(htf, label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum") if "volume" in df else ("close", "size"),
    ).dropna(subset=["close"]).reset_index()
    o["e9"], o["e21"] = o["close"].ewm(span=9, adjust=False).mean(), \
        o["close"].ewm(span=21, adjust=False).mean()
    o["rsi"] = rsi(o["close"])
    o["vwap"] = session_vwap(o)
    o["bull"] = (o.e9 > o.e21) & (o.close > o.vwap) & (o.rsi > 50)
    o["bear"] = (o.e9 < o.e21) & (o.close < o.vwap) & (o.rsi < 50)

    if leaky:
        # every LTF bar inside HTF bar N sees bar N's FINAL values (the r17 bug)
        key = df["ts"].dt.floor(htf)
        m = o.set_index("ts")[["bull", "bear"]]
        return m.reindex(key).fillna(False).reset_index(drop=True)
    # causal: last COMPLETED htf bar as of each LTF bar's close
    o["avail"] = o["ts"] + pd.Timedelta(htf)  # values known after bar closes
    merged = pd.merge_asof(
        df[["ts"]].assign(t=df["ts"]), o[["avail", "bull", "bear"]],
        left_on="t", right_on="avail")
    return merged[["bull", "bear"]].fillna(False).reset_index(drop=True)


# ---------------------------------------------------------------- structure
def build_signals(df: pd.DataFrame, hbias: pd.DataFrame) -> pd.DataFrame:
    h, l, c, op = (df[k].to_numpy() for k in ("high", "low", "close", "open"))
    n = len(df)
    last_sh = np.nan
    last_sl = np.nan
    trend = 0
    last_sig = -999
    sig = np.zeros(n, dtype=int)  # +1 long, -1 short
    bull = hbias["bull"].to_numpy()
    bear = hbias["bear"].to_numpy()
    dates = df["ts"].dt.date.to_numpy()

    for i in range(n):
        # pivot confirmed PIV bars back (same-session only, like a fresh chart day)
        j = i - PIV
        if j >= PIV:
            w_h = h[j - PIV: j + PIV + 1]
            w_l = l[j - PIV: j + PIV + 1]
            if h[j] == w_h.max() and (w_h == h[j]).sum() == 1:
                last_sh = h[j]
            if l[j] == w_l.min() and (w_l == l[j]).sum() == 1:
                last_sl = l[j]

        cross_up = not np.isnan(last_sh) and c[i] > last_sh and \
            (i > 0 and c[i - 1] <= last_sh)
        cross_dn = not np.isnan(last_sl) and c[i] < last_sl and \
            (i > 0 and c[i - 1] >= last_sl)
        if cross_up:
            trend = 1
        if cross_dn:
            trend = -1

        sweep_bull = not np.isnan(last_sl) and l[i] < last_sl and c[i] > last_sl
        sweep_bear = not np.isnan(last_sh) and h[i] > last_sh and c[i] < last_sh

        if i - last_sig < MIN_GAP:
            continue
        if sweep_bull and trend == 1 and c[i] > op[i] and bull[i]:
            sig[i] = 1
            last_sig = i
        elif sweep_bear and trend == -1 and c[i] < op[i] and bear[i]:
            sig[i] = -1
            last_sig = i

    out = df.copy()
    out["sig"] = sig
    return out


# ---------------------------------------------------------------- backtest
@dataclass
class Trade:
    side: int
    entry: float
    exit: float
    risk: float
    bars: int
    ts: pd.Timestamp

    @property
    def r(self) -> float:
        gross = (self.exit - self.entry) * self.side
        cost = (self.entry + self.exit) * COMMISSION + 2 * SLIP
        return (gross - cost) / self.risk

    @property
    def ret(self) -> float:
        gross = (self.exit - self.entry) * self.side
        cost = (self.entry + self.exit) * COMMISSION + 2 * SLIP
        return (gross - cost) / self.entry


def run(df: pd.DataFrame, allow_long: bool, allow_short: bool) -> list[Trade]:
    a = atr(df).to_numpy()
    h, l, c, op = (df[k].to_numpy() for k in ("high", "low", "close", "open"))
    sig = df["sig"].to_numpy()
    ts = df["ts"].to_numpy()
    trades: list[Trade] = []
    pos = 0
    entry = stop = target = risk = 0.0
    be_done = False
    ebar = 0

    def close_trade(i: int, px: float) -> None:
        nonlocal pos
        trades.append(Trade(pos, entry, px, risk, i - ebar, pd.Timestamp(ts[ebar])))
        pos = 0

    for i in range(len(df)):
        if pos != 0 and i > ebar:
            if pos == 1:
                if op[i] <= stop:
                    close_trade(i, op[i])
                elif op[i] >= target:
                    close_trade(i, op[i])
                elif l[i] <= stop:          # worst case: stop before target
                    close_trade(i, stop)
                elif h[i] >= target:
                    close_trade(i, target)
                elif not be_done and c[i] >= entry + risk:
                    stop, be_done = entry, True
            else:
                if op[i] >= stop:
                    close_trade(i, op[i])
                elif op[i] <= target:
                    close_trade(i, op[i])
                elif h[i] >= stop:
                    close_trade(i, stop)
                elif l[i] <= target:
                    close_trade(i, target)
                elif not be_done and c[i] <= entry - risk:
                    stop, be_done = entry, True

        want = sig[i]
        if want == 1 and not allow_long:
            want = 0
        if want == -1 and not allow_short:
            want = 0
        if want != 0 and np.isfinite(a[i]) and a[i] > 0:
            if pos != 0 and want != pos:
                close_trade(i, c[i])        # reversal, like strategy.entry
            if pos == 0:
                pos, entry, ebar, be_done = want, c[i], i, False
                risk = a[i] * ATR_SL
                stop = entry - want * risk
                target = entry + want * risk * TP_RR

    return trades


def summarize(name: str, trades: list[Trade]) -> dict:
    if not trades:
        return {"config": name, "trades": 0}
    r = np.array([t.r for t in trades])
    wins = r > 0
    gp, gl = r[r > 0].sum(), -r[r <= 0].sum()
    tstat = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 2 and r.std() > 0 else np.nan
    return {
        "config": name,
        "trades": len(r),
        "win%": round(100 * wins.mean(), 1),
        "avg_R": round(r.mean(), 3),
        "median_R": round(np.median(r), 3),
        "PF": round(gp / gl, 2) if gl > 0 else np.inf,
        "total_R": round(r.sum(), 1),
        "t": round(tstat, 2) if np.isfinite(tstat) else np.nan,
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    datasets = {
        "BATS 5-min true OHLC (Jul-Aug 2025)": (load_bats("5"), "15min"),
        "BATS 15-min true OHLC (Sep24-Jan25)": (load_bats("15"), "60min"),
        "pseudo 5-min from closes (Aug24-Nov25)": (
            minute_to_pseudo_ohlc(load_minute_closes()), "15min"),
    }
    rows = []
    for dname, (df, htf) in datasets.items():
        variants = {
            "LEAKY(r17)": htf_bias(df, htf, leaky=True),
            "causal": htf_bias(df, htf, leaky=False),
            "no HTF filter": pd.DataFrame(
                {"bull": True, "bear": True}, index=df.index),
        }
        for vname, hb in variants.items():
            sigs = build_signals(df, hb)
            for dirname, (al, ash) in {
                    "short-only": (False, True), "both": (True, True)}.items():
                trades = run(sigs, al, ash)
                tag = f"{dname} | HTF {vname} | {dirname}"
                rows.append(summarize(tag, trades))
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(RESULTS / "sweep_results.csv", index=False)
    print("\nwrote results/sweep_results.csv")


if __name__ == "__main__":
    main()

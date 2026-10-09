"""Python port of the TRIGGER in pine/ie_pro_one.pine (v1.3), ported from the .pine, not from
any earlier port. Paper only: this module only labels bars; it places nothing.

Chart inputs being reproduced (read off the legend):
  SMC mode = OB Primary Trigger, Trade direction = Both, pivot 5, OB depth 20, EMA 9/21,
  vol MA 10, RSI 50/50, ATR SL x1.0, TP 2.5R, volume x1.3, min 3 bars between signals,
  use_ob = false, use_brk = false, use_sweep = true  -> the ONLY trigger is a liquidity sweep.
  (Booleans do not print in the legend; they are the .pine defaults. Whether "Non-repainting
   15m bias" is ON on the chart is NOT visible - that is what htf_mode below is for.)

Signal (pine lines 327-336, 189-223, 294-295):
  long  = sweep_bull and trend == 1  and close > open and htf_bull and bars_since_last_signal >= 3
  short = sweep_bear and trend == -1 and close < open and htf_bear and bars_since_last_signal >= 3
  sweep_bull = low  < lastSL and close > lastSL      (lastSL = last confirmed 5/5 pivot low)
  sweep_bear = high > lastSH and close < lastSH
  trend: close crossing above lastSH sets +1, crossing below lastSL sets -1 (BOS/CHoCH both set it)
  htf_bull = 15m EMA9 > EMA21 and 15m close > 15m session VWAP(hlc3) and 15m RSI14 > 50
  htf_bear = the mirror (RSI < 50)

Everything the trigger does NOT read is left out on purpose: order blocks, breakers, FVG
drawings, the five-leg score (volume leg included), the dashboard, the ticket.

htf_mode - how a 5-minute bar sees the 15-minute bar. This is the one place the .pine is not
causal by default (i_fix_htf = false):
  "leaky"      each 5m bar sees the FINAL values of its own 15m bar (what TradingView draws on
               HISTORY with the script's default lookahead_off; up to 10 minutes of future)
  "developing" the 15m bar as it stands at this 5m bar's close (what a live/replayed bar shows).
               Uses only data up to the close of the 5m bar being decided.
  "fixed"      last COMPLETED 15m bar (the script's own i_fix_htf = true, the r18 fix).
Only "developing" and "fixed" are decidable in real time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PIV = 5
MIN_BARS = 3
ATR_LEN = 14
ATR_SL = 1.0
TP_RR = 2.5


# ----------------------------------------------------------------- Pine-exact smoothing
def _seeded(x: np.ndarray, n: int, alpha: float) -> np.ndarray:
    """Pine ta.ema / ta.rma: NA until n valid values, seeded with their SMA, then recursive."""
    out = np.full(len(x), np.nan)
    valid = np.where(~np.isnan(x))[0]
    if len(valid) < n:
        return out
    i0 = valid[n - 1]
    out[i0] = x[valid[:n]].mean()
    for i in range(i0 + 1, len(x)):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return _seeded(x, n, 2.0 / (n + 1))


def rma(x: np.ndarray, n: int) -> np.ndarray:
    return _seeded(x, n, 1.0 / n)


def rsi14(close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (rsi, up_rma, dn_rma). The two RMA states let 'developing' extend one step."""
    ch = np.diff(close, prepend=np.nan)
    up = rma(np.where(np.isnan(ch), np.nan, np.maximum(ch, 0.0)), 14)
    dn = rma(np.where(np.isnan(ch), np.nan, np.maximum(-ch, 0.0)), 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(dn == 0, 100.0, np.where(up == 0, 0.0, 100.0 - 100.0 / (1.0 + up / dn)))
    r = np.where(np.isnan(up) | np.isnan(dn), np.nan, r)
    return r, up, dn


def atr14(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    tr[0] = h[0] - l[0]  # ta.tr(true) on the first bar
    return rma(tr, ATR_LEN)


# ----------------------------------------------------------------- pivots
def pivots(h: np.ndarray, l: np.ndarray, left: int = PIV, right: int = PIV,
           ties: str = "left_strict") -> tuple[np.ndarray, np.ndarray]:
    """ta.pivothigh / ta.pivotlow. Returns arrays indexed by the CONFIRMATION bar (pivot bar + right).

    ties: Pine's equal-value rule is not documented precisely enough to settle from memory.
      "left_strict": pivot must be strictly beyond the `left` bars before it and >= / <= the `right` bars after
      "strict":      strictly beyond both sides
    count_ties() reports how many bars it matters for."""
    n = len(h)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for j in range(left, n - right):
        wl_h, wr_h = h[j - left:j], h[j + 1:j + right + 1]
        wl_l, wr_l = l[j - left:j], l[j + 1:j + right + 1]
        if ties == "strict":
            ok_h = h[j] > wl_h.max() and h[j] > wr_h.max()
            ok_l = l[j] < wl_l.min() and l[j] < wr_l.min()
        else:
            ok_h = h[j] > wl_h.max() and h[j] >= wr_h.max()
            ok_l = l[j] < wl_l.min() and l[j] <= wr_l.min()
        if ok_h:
            ph[j + right] = h[j]
        if ok_l:
            pl[j + right] = l[j]
    return ph, pl


# ----------------------------------------------------------------- 15-minute bias
def _htf_bars(df: pd.DataFrame) -> pd.DataFrame:
    key = df["ts"].dt.floor("15min")
    g = df.assign(key=key, pv=(df.high + df.low + df.close) / 3 * df.volume).groupby("key", sort=True)
    o = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
              close=("close", "last"), volume=("volume", "sum")).reset_index()
    o["day"] = o["key"].dt.date
    c = o["close"].to_numpy(dtype=float)
    o["e9"], o["e21"] = ema(c, 9), ema(c, 21)
    o["rsi"], o["up"], o["dn"] = rsi14(c)
    hlc3 = (o.high + o.low + o.close) / 3
    o["cpv"] = (hlc3 * o.volume).groupby(o["day"]).cumsum()
    o["cv"] = o.volume.groupby(o["day"]).cumsum()
    o["vwap"] = o["cpv"] / o["cv"].replace(0, np.nan)
    return o


def _flags(e9, e21, close, vwap, rsi):
    bull = (e9 > e21) & (close > vwap) & (rsi > 50)
    bear = (e9 < e21) & (close < vwap) & (rsi < 50)
    return bull, bear


def htf_bias(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Per 5m bar: htf_bull, htf_bear, plus the 15m numbers the decision used."""
    o = _htf_bars(df)
    idx = {k: i for i, k in enumerate(o["key"])}
    b = df["ts"].dt.floor("15min").map(idx).to_numpy()  # row of the enclosing 15m bar
    n = len(df)
    e9, e21, rs, vw, cl = (np.full(n, np.nan) for _ in range(5))

    if mode == "leaky":
        e9, e21, rs, vw, cl = (o[k].to_numpy()[b] for k in ("e9", "e21", "rsi", "vwap", "close"))
    elif mode == "fixed":
        pb = b - 1  # the previous 15m bar in the series (security(...[1], lookahead_on))
        ok = pb >= 0
        for arr, k in ((e9, "e9"), (e21, "e21"), (rs, "rsi"), (vw, "vwap"), (cl, "close")):
            arr[ok] = o[k].to_numpy()[pb[ok]]
    elif mode == "developing":
        # running 15m bar as of THIS 5m bar's close; previous 15m states come from completed bars only
        keys = df["ts"].dt.floor("15min").to_numpy()
        hh = df["high"].to_numpy(); ll = df["low"].to_numpy(); cc = df["close"].to_numpy()
        vv = df["volume"].to_numpy(dtype=float)
        a9, a21 = 2 / 10, 2 / 22
        cur_key = None
        dh = dl = dv = np.nan
        for i in range(n):
            if keys[i] != cur_key:
                cur_key = keys[i]; dh, dl, dv = hh[i], ll[i], 0.0
            dh, dl, dv = max(dh, hh[i]), min(dl, ll[i]), dv + vv[i]
            p = b[i] - 1
            if p < 0:
                continue
            e9[i] = a9 * cc[i] + (1 - a9) * o["e9"].iat[p]
            e21[i] = a21 * cc[i] + (1 - a21) * o["e21"].iat[p]
            ch = cc[i] - o["close"].iat[p]
            up = (o["up"].iat[p] * 13 + max(ch, 0.0)) / 14
            dn = (o["dn"].iat[p] * 13 + max(-ch, 0.0)) / 14
            rs[i] = 100.0 if dn == 0 else (0.0 if up == 0 else 100 - 100 / (1 + up / dn))
            same_day = o["day"].iat[p] == o["day"].iat[b[i]]
            pv0 = o["cpv"].iat[p] if same_day else 0.0
            v0 = o["cv"].iat[p] if same_day else 0.0
            tot_v = v0 + dv
            vw[i] = (pv0 + (dh + dl + cc[i]) / 3 * dv) / tot_v if tot_v > 0 else np.nan
            cl[i] = cc[i]
    else:
        raise ValueError(mode)

    bull, bear = _flags(e9, e21, cl, vw, rs)
    return pd.DataFrame({"htf_bull": bull, "htf_bear": bear, "h_e9": e9, "h_e21": e21,
                         "h_rsi": rs, "h_vwap": vw, "h_close": cl}, index=df.index)


# ----------------------------------------------------------------- the trigger
def run(df: pd.DataFrame, htf_mode: str = "developing", ties: str = "left_strict",
        allow_long: bool = True, allow_short: bool = True) -> pd.DataFrame:
    """df: 5m bars, columns ts (tz-aware ET), open, high, low, close, volume - EXTENDED hours kept,
    as on the chart. Returns df plus the trigger columns. No bar looks at a later bar except via
    htf_mode='leaky'."""
    df = df.sort_values("ts").reset_index(drop=True)
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(df)
    ph, pl = pivots(h, l, ties=ties)
    hb = htf_bias(df, htf_mode)
    bull_htf, bear_htf = hb["htf_bull"].to_numpy(), hb["htf_bear"].to_numpy()
    atr = atr14(h, l, c)

    last_sh = last_sl = np.nan
    trend = 0
    last_sig = -999
    sweep_b = np.zeros(n, bool); sweep_s = np.zeros(n, bool)
    trend_a = np.zeros(n, int)
    lsh_a = np.full(n, np.nan); lsl_a = np.full(n, np.nan)
    sig = np.zeros(n, int)
    for i in range(n):
        if not np.isnan(ph[i]):
            last_sh = ph[i]
        if not np.isnan(pl[i]):
            last_sl = pl[i]
        pc = c[i - 1] if i > 0 else np.nan
        cross_up = not np.isnan(last_sh) and c[i] > last_sh and pc <= last_sh
        cross_dn = not np.isnan(last_sl) and c[i] < last_sl and pc >= last_sl
        if cross_up:
            trend = 1
        if cross_dn:
            trend = -1
        trend_a[i] = trend
        lsh_a[i], lsl_a[i] = last_sh, last_sl
        sweep_b[i] = (not np.isnan(last_sl)) and l[i] < last_sl and c[i] > last_sl
        sweep_s[i] = (not np.isnan(last_sh)) and h[i] > last_sh and c[i] < last_sh
        gap_ok = (i - last_sig) >= MIN_BARS
        long_raw = sweep_b[i] and trend == 1 and c[i] > o[i] and bull_htf[i]
        short_raw = sweep_s[i] and trend == -1 and c[i] < o[i] and bear_htf[i]
        if long_raw and gap_ok and allow_long:
            sig[i] = 1
        elif short_raw and gap_ok and allow_short:
            sig[i] = -1
        if sig[i] != 0:
            last_sig = i

    out = pd.concat([df, hb], axis=1)
    out["sweep_bull"], out["sweep_bear"], out["trend"], out["atr"], out["sig"] = sweep_b, sweep_s, trend_a, atr, sig
    out["lastSH"], out["lastSL"] = lsh_a, lsl_a
    out["E"] = c
    risk = atr * ATR_SL
    out["SL"] = np.where(sig > 0, c - risk, np.where(sig < 0, c + risk, np.nan))
    out["TP1"] = np.where(sig > 0, c + risk, np.where(sig < 0, c - risk, np.nan))
    out["TP2"] = np.where(sig > 0, c + risk * TP_RR, np.where(sig < 0, c - risk * TP_RR, np.nan))
    return out


def count_ties(df: pd.DataFrame) -> int:
    """How many pivot bars differ between the two tie rules (0 = the rule does not matter here)."""
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    a = pivots(h, l, ties="left_strict"); b = pivots(h, l, ties="strict")
    return int((np.nan_to_num(a[0]) != np.nan_to_num(b[0])).sum() + (np.nan_to_num(a[1]) != np.nan_to_num(b[1])).sum())

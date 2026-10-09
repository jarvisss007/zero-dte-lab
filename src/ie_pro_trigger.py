"""Python port of pine/ie_pro_indicator.pine ("Institutional Edge Pro", the indicator that prints the
CONFIRMED LONG/SHORT [A+]/[A]/[B] labels). Ported from the source, not from any other version.
Paper only: this module only labels bars; it places nothing.

Chart settings (the source defaults differ in ONE place: Volume MA is 20 on the chart, 10 in the file):
  EMA 9/21, RSI 14, bull 55, bear 45, Volume MA 20, SL 0.5 ATR, TP1 1.5 ATR, TP2 3 ATR, min bars 20.

The rule (pine lines 33-96):
  long_score  = (ema9>ema21) + (close>vwap) + (rsi>55) + (volume>sma(volume,20)) + (close>ema9)
  short_score = the mirror with rsi<45
  long_signal  = long_score == 5 and htf_bull and long_score[1] != 5 and bars_since_last_signal >= 20
  short_signal = short_score == 5 and htf_bear and short_score[1] != 5 and ...
  htf_bull = 15m EMA9>EMA21 and 15m close > 15m VWAP and 15m RSI14 > 50     (htf_bear: the mirror)
  early zone (printed, not a trade): score >= 3 and htf and score[1] < 3 and gap_ok
  Entry E = close of the signal bar. SL = low - 0.5 ATR (long) / high + 0.5 ATR (short);
  TP1/TP2 = E +/- 1.5 / 3.0 ATR. ATR = Wilder ATR(14).
  Grade: A+ = rsi>63 (<37) and volume > 1.5 x vol MA and |ema9-ema21| > 0.3 ATR in the trade direction;
         A = rsi strong OR volume strong; else B.

There is no structure test, no RSI-exhaustion gate and no time filter. The ONLY thing not causal by default is the
15m bias (request.security with lookahead_off): htf_mode selects how a 5m bar sees the 15m bar (see
ie_pro_one_trigger.py): "leaky" = final values of its own 15m bar (what history shows), "developing" = the 15m bar as of
this 5m close (decidable in real time), "fixed" = last completed 15m bar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ie_pro_one_trigger import atr14, ema, htf_bias, rsi14


def run(df: pd.DataFrame, htf_mode: str = "developing", vol_len: int = 20, rsi_bull: float = 55,
        rsi_bear: float = 45, min_bars: int = 20, sl_mult: float = 0.5, tp1_mult: float = 1.5,
        tp2_mult: float = 3.0) -> pd.DataFrame:
    """df: 5m bars, columns ts (tz-aware ET), open, high, low, close, volume, EXTENDED hours kept, as on the chart.
    Returns df plus the indicator columns. A volume of 0 (Yahoo premarket) makes vwap NaN and vol_ok False, exactly
    as TradingView treats a missing value - so premarket signals cannot appear in free data."""
    df = df.sort_values("ts").reset_index(drop=True)
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    n = len(df)

    ema9, ema21 = ema(c, 9), ema(c, 21)
    rsi, _, _ = rsi14(c)
    atr = atr14(h, l, c)
    vol_ma = pd.Series(v).rolling(vol_len).mean().to_numpy()
    day = df["ts"].dt.date.to_numpy()
    hlc3 = (h + l + c) / 3
    pv = pd.Series(hlc3 * v).groupby(day).cumsum().to_numpy()
    vv = pd.Series(v).groupby(day).cumsum().to_numpy()
    vwap = np.where(vv > 0, pv / np.where(vv > 0, vv, 1.0), np.nan)

    hb = htf_bias(df, htf_mode)
    bull_htf, bear_htf = hb["htf_bull"].to_numpy(), hb["htf_bear"].to_numpy()

    with np.errstate(invalid="ignore"):
        vol_ok = v > vol_ma
        long_score = ((ema9 > ema21).astype(int) + (c > vwap) + (rsi > rsi_bull) + vol_ok + (c > ema9)).astype(int)
        short_score = ((ema9 < ema21).astype(int) + (c < vwap) + (rsi < rsi_bear) + vol_ok + (c < ema9)).astype(int)
        rsi_sb, rsi_ss = rsi > 63, rsi < 37
        vol_strong = v > vol_ma * 1.5
        sep_b, sep_s = (ema9 - ema21) > atr * 0.3, (ema21 - ema9) > atr * 0.3

    last = -999
    sig = np.zeros(n, int)
    early = np.zeros(n, int)
    grade = np.array([""] * n, dtype=object)
    for i in range(1, n):
        gap_ok = (i - last) >= min_bars
        if long_score[i] >= 3 and bull_htf[i] and long_score[i - 1] < 3 and gap_ok:
            early[i] = 1
        if short_score[i] >= 3 and bear_htf[i] and short_score[i - 1] < 3 and gap_ok:
            early[i] = -1 if early[i] == 0 else early[i]
        long_sig = long_score[i] == 5 and bull_htf[i] and long_score[i - 1] != 5 and gap_ok
        short_sig = short_score[i] == 5 and bear_htf[i] and short_score[i - 1] != 5 and gap_ok
        if long_sig:
            sig[i] = 1
            grade[i] = "A+" if (rsi_sb[i] and vol_strong[i] and sep_b[i]) else "A" if (rsi_sb[i] or vol_strong[i]) else "B"
        elif short_sig:
            sig[i] = -1
            grade[i] = "A+" if (rsi_ss[i] and vol_strong[i] and sep_s[i]) else "A" if (rsi_ss[i] or vol_strong[i]) else "B"
        if sig[i] != 0:
            last = i

    out = pd.concat([df, hb], axis=1)
    out["rsi"], out["atr"], out["vwap"], out["vol_ma"] = rsi, atr, vwap, vol_ma
    out["long_score"], out["short_score"], out["early"], out["sig"], out["grade"] = long_score, short_score, early, sig, grade
    out["E"] = c
    out["SL"] = np.where(sig > 0, l - atr * sl_mult, np.where(sig < 0, h + atr * sl_mult, np.nan))
    out["TP1"] = np.where(sig > 0, c + atr * tp1_mult, np.where(sig < 0, c - atr * tp1_mult, np.nan))
    out["TP2"] = np.where(sig > 0, c + atr * tp2_mult, np.where(sig < 0, c - atr * tp2_mult, np.nan))
    return out

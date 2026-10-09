# IE Pro (TradingView indicator) — chart settings and port verification, 2026-10-09

Source: `pine/ie_pro_indicator.pine` (pasted by Anupam, saved verbatim, 293 lines). Port: `src/ie_pro_trigger.py`.
Paper only. A description of a port, not a claimed edge — the lab's verdicts on same-day SPY options still stand.
(This sheet replaces an earlier version written before the source arrived, which wrongly guessed a structure-anchored stop.)

## Settings on the chart (from the dialog screenshots and the status-line legend)
Fast EMA 9, Slow EMA 21, RSI 14, Bull 55, Bear 45, **Volume MA 20** (the file's default is 10), SL ATR x 0.5, TP1 ATR x 1.5,
TP2 ATR x 3, Label offset 3, Min bars between signals 20, HUD / HTF Dots / EMAs / VWAP on. Legend `IE Pro 9 21 14 55 45 20 0.5 1.5 3 3 20`.

## The rule (from the source)
- long_score = EMA9>EMA21, close>VWAP, RSI>55, volume>SMA20(volume), close>EMA9; short is the mirror with RSI<45.
- Signal = score == 5, 15m bias agrees, score was not 5 on the previous bar, and at least 20 bars since the last signal.
  No structure test, no RSI-exhaustion gate, no time filter. 15m bias = EMA9>EMA21, close>VWAP, RSI>50 on 15m (lookahead_off:
  the one non-causal piece on history).
- Entry E = signal-bar close. SL = bar low (long) / high (short) -/+ 0.5 ATR. TP1/TP2 = E +/- 1.5 / 3 ATR (Wilder ATR14).
- Grade: A+ = RSI>63 (<37) and volume>1.5x its MA and EMA separation>0.3 ATR; A = RSI strong or volume strong; else B.
- "LONG/SHORT ZONE" labels (score>=3) are early warnings, not trades.

## Verification against 30 chart labels (8 sessions, 2026-09-30 .. 10-09; 8 Oct post-market included)
| Check | Result |
|---|---|
| Entry = close of a real 5m bar | 30 of 30 labels |
| TP1/TP2 = 1.5 / 3 x ATR | exact on every label; the ATR equals Wilder ATR14 of the bars on regular-hours bars |
| Stop rule (bar low/high -/+ 0.5 ATR) | exact on the labels the free-running port reproduced (2 of 3; the third is within 3 cents of SL, 10 cents of TP) |
| Free-running port reproduces the label | 3 of 30 (3 of 14 in regular hours) |
| Port with the 20-bar spacing anchored on the chart's own labels | fires on 10 of 14 regular-hours labels; misses = 3 volume-leg near-ties (volume 376k vs MA 388k, 426k vs 483k) and 1 bar-timing |
| Regular-hours bars where the rule fires but the chart shows no label | 10 over 7 sessions (some may sit behind other labels) |

**Why the free run does not match the chart:** the rule is right; the feed is not. Yahoo has zero premarket volume (so no premarket
signal can ever fire and VWAP is regular-hours only) and its volume is a different feed from the chart's (ratios 0.48-0.89 of
consolidated), so the volume leg flickers on different bars. The 20-bar spacing then makes the sequence path-dependent: an extra
signal a few bars early uses up the gap that the chart's later label needed. 16 of the 30 labels are premarket or post-market (14 are regular hours).

**How often it fires in regular hours** (what a SPY-option paper trader can use): about 2-3 signals per session in free-run
(22 over 8 sessions, 15m mode leaky/developing; 16 with `fixed`), against 14 labels in 7 sessions on the chart.

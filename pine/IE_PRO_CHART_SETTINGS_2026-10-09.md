# IE Pro (TradingView indicator) — settings as on the chart, 2026-10-09

Combined from five settings-dialog screenshots and the chart's status-line legend. **The Pine source is not available**
(zero-dte-lab README Finding 6 says the same). This sheet is the indicator's configuration, not its rule.
Paper only; no edge is claimed.

## Inputs tab
| Group | Input | Value |
|---|---|---|
| EMA | Fast EMA | 9 |
| EMA | Slow EMA | 21 |
| RSI | RSI Length | 14 |
| RSI | Bull Threshold | 55 |
| RSI | Bear Threshold | 45 |
| Volume | Volume MA | 20 |
| RR | SL ATR x | 0.5 |
| RR | TP1 ATR x | 1.5 |
| RR | TP2 ATR x | 3 |
| RR | Label offset ATR x | 3 |
| Filters | Min bars between signals | 20 |
| Display | HUD Panel / HTF Dots / Show EMAs / Show VWAP | all ON |

Status-line legend `IE Pro 9 21 14 55 45 20 0.5 1.5 3 3 20` = the eleven numbers above, in the same order.
There are no structure inputs, no time-filter inputs and no TP3 on this chart (the June "IE Pro v3" file has all three).

## Style tab
EMA 9 (yellow line), EMA 21 (grey-blue line), VWAP (orange circles), two background-colour fills, HTF Bull (teal) /
HTF Bear (red) / HTF Neutral (grey) shown at the top; graphic objects (boxes, pane labels, lines, tables) ON;
labels on price scale, values and inputs in status line ON. Visibility: all timeframes.

## What the 30 transcribed labels establish (8 sessions, 2026-09-30 .. 10-09)
- Entry `E` is the close of the signal bar: 30 of 30 labels match a real SPY 5m close at the right time.
- TP1 = E ± 1.5 x ATR and TP2 = E ± 3 x ATR on every label, and that ATR is the Wilder ATR(14) of the 5m bars
  (regular-hours bars agree to about 0.003, e.g. 0.787 vs 0.788).
- The stop distance is not a fixed multiple (0.4 to 2.2 ATR): a structure-anchored stop plus 0.5 ATR, as in IE Pro v3.
- On all 14 regular-hours labels the momentum core is true: EMA 9/21, price vs VWAP, RSI 55/45, volume vs its 20-bar
  average, price vs EMA 9 score 5/5 on 11 and 4/5 on 3 (feed noise), and the 15m bias agrees on all 14.

## What is NOT pinned down
- Whether the entry needs 5/5 or 4/5, and the structure condition (v3's structure test is false on 4 of the 14 label bars).
- Path dependence: with 20 bars between signals, which bar of a cluster fires depends on every earlier signal, premarket
  and after-hours included. Yahoo has no premarket volume, so that sequence cannot be replayed faithfully.
- A reconstruction (v3 logic with these settings) fires 15 regular-hours signals against the chart's 14 labels but lands on
  only 6 of the 14 label bars. It is close in rate, not the same rule.

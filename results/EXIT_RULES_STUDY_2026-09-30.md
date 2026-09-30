# Exit rules for a bought 0DTE option: hold-and-hope and give-back (2026-09-30)
STATUS: DESCRIPTION ONLY - nothing registered, no position follows from it. Looks: 324 cells (9 groups x 36: 3 drawdown levels, 3 gain levels, 2 peak readings, 28 rules) plus 81 alternative readings (official-close check, next level including the touching snapshot). All are in the JSON; both A blocks and the E2 pooled grid are shown here.
Data: 45 complete CBOE sessions, 2026-07-17 to 2026-09-29 (today's file excluded); market clock (quote stamp); buy at the ask, every exit at the bid of the snapshot where its rule triggers.
E1 = one entry per session nearest 10:25 ET (84 trades, 42 sessions). E2 = every snapshot 10:00-11:30 ET (1,524 trades, 44 sessions; overlapping, so sessions are the real n). Pooled = ATM call + ATM put.
Results are % of the entry ask; settle is the grid's last-book convention. 90% session-bootstrap intervals are in the JSON (shares: E2 +-3 to +-10 points, E1 +-4 to +-14).

## A1. When a bought option is red, does holding get it back to green?
| set | line | touch (of all trades) | of touchers: gets back to entry ask | green at settle | settle mean / median | closed at first snapshot past the line (mean) |
|---|---|---|---|---|---|---|
| E2 pooled | -20% | 89.0% | 54.8% | 22.3% | -40.9% / -100.0% | -28.3% |
| E2 pooled | -30% | 84.1% | 45.5% | 19.3% | -50.6% / -100.0% | -37.3% |
| E2 pooled | -50% | 72.4% | 25.6% | 13.0% | -68.2% / -100.0% | -55.7% |
| E1 pooled | -20% | 92.9% | 56.4% | 26.9% | -29.3% / -100.0% | -28.0% |
| E1 pooled | -30% | 85.7% | 47.2% | 23.6% | -46.7% / -100.0% | -37.0% |
| E1 pooled | -50% | 71.4% | 23.3% | 11.7% | -68.5% / -100.0% | -56.4% |
- Holding is not hopeless intraday but it fades: after a -20% touch 54.8% regain the entry ask at some snapshot, yet only 22.3% finish green and the median finish is -100.0%. Holding to settle averages -40.9%; closing at the first snapshot below the line -28.3% (overshoot 8.3 points). On average, closing beats holding by 12.6 / 13.3 / 12.5 points at -20 / -30 / -50%.
- E1 (one entry per session) tells the same story: every share within 6.1 points of E2, except the share of +100% touchers reaching the next level (28.6% on 28 trades vs 41.3%).

## A2. When it is green, does it keep going or give the gain back?
| set | level | touch (of all trades) | of touchers: next level, later / incl. same snapshot | below entry ask at settle | settle mean / median | closed at first snapshot past the level (mean) |
|---|---|---|---|---|---|---|
| E2 pooled | +25% (next +50%) | 65.2% | 77.9% / 79.1% | 55.1% | +23.2% / -18.2% | +39.4% |
| E2 pooled | +50% (next +100%) | 51.5% | 61.9% / 62.5% | 44.7% | +48.9% / +26.5% | +67.2% |
| E2 pooled | +100% (next +200%) | 32.2% | 41.3% / 41.3% | 29.3% | +102.0% / +92.6% | +121.1% |
| E1 pooled | +25% (next +50%) | 65.5% | 80.0% / 80.0% | 50.9% | +20.4% / -0.8% | +40.3% |
| E1 pooled | +50% (next +100%) | 52.4% | 63.6% / 63.6% | 38.6% | +45.3% / +28.8% | +65.5% |
| E1 pooled | +100% (next +200%) | 33.3% | 28.6% / 28.6% | 28.6% | +83.0% / +84.5% | +119.8% |
- A gain is not safe: 55.1% / 44.7% / 29.3% of trades that touched +25 / +50 / +100% finish below the entry ask, while 77.9% / 61.9% / 41.3% go on to the next level. On average, closing at the first touch beats holding to settle by 16.2 / 18.3 / 19.1 points.
- The peak bid comes late: median 65 min after entry (quartiles 15-180); for trades green at a +40m clock the median is 85 min (45-196), later than a 40-minute clock.
- Official-close check: settle shares move at most 1.7 points (E1 4.6) and settle means by -9.7 to +1.8 points (E1 -5.6 to +1.9); every closing-vs-holding comparison keeps its direction. E1 1-strike-OTM (JSON): 84.5% touch -50% (ATM 71.4%); 64.3% of its +25% touchers finish below entry (ATM 50.9%).

## B. Rule grid, E2 pooled: mean % / win % / loss-to-win ratio (targets carry a +60m clock fallback)
| loss line | clock +15m | +25m | +40m | +60m | target +25% | +50% | +100% |
|---|---|---|---|---|---|---|---|
| none | -0.7 / 43 / 0.81 | -0.2 / 43 / 0.76 | +0.5 / 41 / 0.71 | +1.3 / 40 / 0.63 | -3.1 / 52 / 1.29 | -0.8 / 44 / 0.82 | +0.1 / 40 / 0.66 |
| -20% | -0.3 / 41 / 0.72 | +1.0 / 38 / 0.58 | +0.8 / 33 / 0.47 | +0.8 / 28 / 0.37 | -1.7 / 40 / 0.76 | -0.2 / 32 / 0.48 | +0.2 / 28 / 0.39 |
| -30% | -0.4 / 43 / 0.78 | +1.0 / 42 / 0.69 | +1.5 / 38 / 0.58 | +2.1 / 34 / 0.47 | -1.9 / 47 / 0.97 | +0.2 / 38 / 0.61 | +1.1 / 34 / 0.49 |
| -50% | -0.7 / 43 / 0.81 | +0.2 / 43 / 0.75 | +1.0 / 41 / 0.69 | +1.5 / 39 / 0.60 | -2.7 / 52 / 1.23 | -0.6 / 43 / 0.78 | +0.3 / 39 / 0.63 |
- Only the +25% target gets near or past |t| 2: t -2.62 / -1.98 / -2.21 / -3.17 with no / -20% / -30% / -50% loss line; every other cell has |t| <= 1.39. With no loss line it wins 52.5% of trades but its losers average -46.7% (loss/win 1.29).
- A loss line reshapes rather than lifts: on the +40m clock the -20 / -30 / -50% lines stop 59.9 / 46.7 / 23.6% of trades at average fills of -28.5 / -37.5 / -55.9%, cut the worst loss from -89.5% to -55.2 / -66.4 / -75.9% and lower the win rate from 41.4% to 32.7 / 38.1 / 41.3%; means +0.8 / +1.5 / +1.0 vs +0.5 (all |t| <= 0.75).
- The E1 pooled grid (84 trades, 42 sessions) is in the JSON; the largest |t| is 1.74.

## What limits the numbers
- 0DTE only: options with 1-2 days to expiry move less in percent, so a given percent line is hit less often than these shares show.
- 5-minute snapshots: lines overshoot (a -20% line fills near -28%, a +25% level near +39%) and moves between snapshots are unseen.
- Delayed CBOE quotes: the feed lags the recorder by 16 minutes (median); times are the quote stamps and prices are CBOE's delayed book, not a live fill.
- One calm window: 45 sessions, 0 days of 2% or more, 5 of 1% or more, largest move 1.68%. Entries overlap, so read the intervals, not the trade count.
- No directional skill assumed: calls and puts pooled. The legs differ (E2 after a -20% touch: calls finish green 18.6%, puts 26.0%); the JSON has each leg.
- Settle is the grid's last-book convention (median stamp 15:48 ET), not the close; the official-close readings are in the JSON (mean gap +0.18, mean abs 0.47 points).
- Checked outside the JSON: E1 reproduces the earlier refresh's 168 entries and their +40m and settle results exactly; an independent re-implementation matches 1,812 statistics.

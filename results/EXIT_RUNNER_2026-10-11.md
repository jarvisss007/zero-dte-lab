# The Runner Card: sell half at +50%, let half run, on the recorded SPY 0DTE chains (2026-10-11)
STATUS: DESCRIPTION ONLY - nothing registered, no position follows from it. An extra look at the SAME 45 sessions as the exit-rules study of 2026-09-30 (results/EXIT_RULES_STUDY_2026-09-30.md), so every cell here pays a mining tax. Looks: 48 = 4 rules x 6 groups (24 cells) + 24 paired differences against the 30/50/60 card. The E2 and E1 pooled grids and the call/put split are shown here; every cell, interval and the runner-stage breakdown are in the JSON.
Data: 45 complete CBOE sessions, 2026-07-17 to 2026-09-29 (today's file excluded); market clock (quote stamp); buy at the ask, every exit at the bid of the snapshot where its rule triggers. The loader, trades, rule engine and statistics are the study's own (imported, not copied).
E1 = one entry per session nearest 10:25 ET (84 trades, 42 sessions). E2 = every snapshot 10:00-11:30 ET (1,524 trades, 44 sessions; overlapping, so sessions are the real n). Pooled = ATM call + ATM put; each leg is also shown. Results are % of the TOTAL entry cost; intervals are 90% session-bootstrap intervals of the mean, t is the cluster-robust t by session (the study's own functions).

## The rule
- Two contracts bought at the same ask. Both carry a -30% stop. Contract 1 sells at +50% (target 1) or the 60-minute clock: it is exactly the study's 30/50/60 cell, checked trade by trade on every loaded trade (1,692, the 1,608 reported plus 84 1-strike-OTM entries not reported here). Contract 2 is identical until target 1 fills; then its stop moves to the entry price and it exits at the first of +100%, that stop, or the 60-minute clock (measured from entry, as in the study). If neither target is hit, both exit at the -30% line or the clock. A 5-minute jump through both +50% and +100% fills both at that bid.
- Variants, each a separate look: (b) the runner target is +150%; (c) a 25% trailing stop from the peak bid replaces the breakeven stop and the +100% cap stays; (c') the same trailing stop with no fixed target, capped by the clock only. The brief did not say whether the cap survives the trailing stop, so both readings are run and both are counted.
- Comparison cells are RE-READ from the study JSON: the 30/50/60 card, -30% + 60m clock, -30% / +100% / 60m, and "sell at the first +25%" (no loss line, 60m fallback). The study's engine recomputes them only to get the intervals and the paired differences; 390 of 390 recomputed statistics equal the JSON.

## A. E2 pooled (1,524 trades, 44 sessions)
| rule | mean % [90% interval] | t | win % | avg win | avg loss | loss/win | worst loss | fills its profit target (= the runner stage for the Runner Card) | vs the card: mean diff [90%], t |
|---|---|---|---|---|---|---|---|---|---|
| 30/50/60 card (-30% / +50% / 60m) | +0.2 [-2.2, +2.6] | +0.16 | 38.3 | +56.2 | -34.5 | 0.61 | -66.4 | 29.3% | - |
| -30% + 60m clock | +2.1 [-3.2, +8.0] | +0.61 | 33.8 | +72.3 | -33.9 | 0.47 | -66.4 | - | - |
| -30% / +100% / 60m | +1.1 [-3.2, +5.5] | +0.42 | 33.9 | +68.9 | -33.9 | 0.49 | -66.4 | 12.1% | - |
| sell at the first +25% (no loss line) | -3.1 [-5.0, -1.2] | -2.62 | 52.5 | +36.1 | -46.7 | 1.29 | -94.2 | 48.4% | - |
| Runner Card (a): +50% half, +100% runner, breakeven stop | +0.9 [-2.1, +4.1] | +0.45 | 38.3 | +57.8 | -34.5 | 0.60 | -66.4 | 29.3% | +0.62 [-0.60, +1.90], t +0.81 |
| (b) runner target +150% | +1.2 [-2.0, +4.6] | +0.58 | 38.3 | +58.6 | -34.5 | 0.59 | -66.4 | 29.3% | +0.95 [-0.60, +2.50], t +0.99 |
| (c) 25% trailing stop, +100% cap kept | +0.8 [-2.2, +3.9] | +0.44 | 38.3 | +57.7 | -34.5 | 0.60 | -66.4 | 29.3% | +0.61 [-0.50, +1.80], t +0.82 |
| (c') 25% trailing stop, no profit cap | +1.2 [-2.2, +5.1] | +0.55 | 38.3 | +58.7 | -34.5 | 0.59 | -66.4 | 29.3% | +0.98 [-0.90, +3.10], t +0.80 |
- The loss side is the card's, to the digit. Until target 1 the pair is the card, so the win rate (38.3%), the average loss (-34.5%) and the worst loss (-66.4%) do not move. The Runner changes only the 29.3% of trades (447; interval 26.0-32.4%) that reach +50%, and none of them ends as a loss in total: the worst runner-stage total is +7.7% (breakeven stop) or +18.3% (trailing stop).
- What it adds is small: mean +0.9% vs +0.2% for the card, a paired difference of +0.62 points [-0.60, +1.90], t +0.81. Variants: (b) +0.95 [-0.60, +2.50] t +0.99, (c) +0.61 [-0.50, +1.80] t +0.82, (c') +0.98 [-0.90, +3.10] t +0.80. Every interval spans zero; none is distinguishable from noise. The average win rises from 56.2% to 57.8% (a) and 58.6% (b); loss-to-win moves 0.61 to 0.60 / 0.59.
- Where the points come from: on the 447 runner-stage trades contract 2 averages +71.0% against +66.8% for contract 1 (+4.3 points; contract 1 beats its +50% line by 16.8 points on average because the snapshot overshoots). It beats the +50% sale on 45.9% of those trades and finishes below the entry ask on 15.7% (the breakeven stop fills at the next bid, which can be well under entry). Target 1 fills at a median 25 minutes (quartiles 15-40), leaving a median 35 minutes on the clock.
- Against the other study cells the Runner sits beside them: -30% + 60m clock +2.1 [-3.2, +8.0] and -30% / +100% / 60m +1.1 [-3.2, +5.5] both have a mean of the same size or higher than the Runner's (+0.9 to +1.2) but a lower win rate (33.8% / 33.9% vs 38.3%) and a larger average win (+72.3 / +68.9 vs +57.8); the intervals overlap almost completely. "Sell at the first +25%" is the only comparison cell past |t| 2 (-3.1, t -2.62, loss-to-win 1.29, worst -94.2% with no loss line); the Runner's mean is 4.0 points above it, a gap I did not test pairwise.

## B. E1 pooled (84 trades, 42 sessions)
| rule | mean % [90% interval] | t | win % | avg win | avg loss | loss/win | worst loss | fills its profit target (= the runner stage for the Runner Card) | vs the card: mean diff [90%], t |
|---|---|---|---|---|---|---|---|---|---|
| 30/50/60 card (-30% / +50% / 60m) | +3.0 [-1.5, +7.4] | +1.06 | 40.5 | +56.7 | -34.1 | 0.60 | -53.8 | 29.8% | - |
| -30% + 60m clock | +4.8 [-2.8, +13.4] | +0.96 | 35.7 | +71.6 | -32.9 | 0.46 | -53.8 | - | - |
| -30% / +100% / 60m | +5.3 [-1.5, +12.0] | +1.27 | 36.9 | +69.8 | -33.1 | 0.47 | -53.8 | 11.9% | - |
| sell at the first +25% (no loss line) | -4.0 [-7.6, -0.3] | -1.74 | 53.6 | +35.6 | -51.1 | 1.43 | -90.1 | 50.0% | - |
| Runner Card (a): +50% half, +100% runner, breakeven stop | +4.2 [-0.9, +9.9] | +1.30 | 40.5 | +59.6 | -34.1 | 0.57 | -53.8 | 29.8% | +1.18 [-1.10, +3.30], t +0.85 |
| (b) runner target +150% | +3.1 [-1.9, +8.4] | +0.97 | 40.5 | +57.0 | -34.1 | 0.60 | -53.8 | 29.8% | +0.10 [-2.40, +2.60], t +0.07 |
| (c) 25% trailing stop, +100% cap kept | +3.9 [-1.5, +9.2] | +1.21 | 40.5 | +58.7 | -34.1 | 0.58 | -53.8 | 29.8% | +0.82 [-1.30, +3.00], t +0.63 |
| (c') 25% trailing stop, no profit cap | +3.6 [-2.1, +9.5] | +1.01 | 40.5 | +58.1 | -34.1 | 0.59 | -53.8 | 29.8% | +0.56 [-1.60, +3.00], t +0.37 |
- 25 of 84 trades (29.8%) reach the runner stage, in 25 different sessions. The Runner's mean is +4.2% vs +3.0% for the card (+1.18 points [-1.10, +3.30], t +0.85); (b) +0.10, (c) +0.82, (c') +0.56, all spanning zero. The largest |t| of any E1 cell above is 1.74 (the +25% habit cell). Variant (b) was the best E2 variant and the weakest here, so the ranking of the variants does not carry from E2 to E1; only the sign agrees.

## C. Calls vs puts
E2 (762 + 762 trades; runner-stage trades 220 in 31 sessions for calls, 227 in 39 for puts):
| rule | calls (762): mean % [90%] / vs card [90%], t | puts (762): mean % [90%] / vs card [90%], t |
|---|---|---|
| 30/50/60 card | -0.2 [-7.6, +6.9] / - | +0.6 [-5.7, +7.5] / - |
| Runner Card (a): +50% half, +100% runner, breakeven stop | +1.6 [-6.4, +10.3] / +1.83 [+0.00, +3.90], t +1.56 | +0.1 [-7.1, +7.8] / -0.58 [-1.80, +0.70], t -0.72 |
| (b) runner target +150% | +2.5 [-6.1, +11.4] / +2.72 [+0.50, +5.20], t +1.86 | -0.2 [-7.3, +7.5] / -0.82 [-2.30, +0.70], t -0.86 |
| (c) 25% trailing stop, +100% cap kept | +1.4 [-6.4, +10.2] / +1.57 [-0.20, +3.60], t +1.35 | +0.3 [-6.7, +7.6] / -0.35 [-1.60, +1.00], t -0.45 |
| (c') 25% trailing stop, no profit cap | +2.8 [-6.3, +12.3] / +3.01 [+0.00, +6.70], t +1.49 | -0.4 [-7.4, +7.0] / -1.06 [-2.60, +0.90], t -1.03 |
- The Runner's edge over the card has opposite signs on the two legs. Calls: (a) +1.83 [0.00, +3.90] t +1.56, (b) +2.72 [+0.50, +5.20] t +1.86, (c) +1.57, (c') +3.01. Puts: (a) -0.58 [-1.80, +0.70] t -0.72, (b) -0.82, (c) -0.35, (c') -1.06. On runner-stage trades contract 2 averages +79.2% for calls but +63.2% for puts (against about +67% for contract 1 on both). Same sessions, same rule: this is how the two legs behaved in this window, not exit skill, and the study had already shown the legs differ.
E1 (42 trades per leg; 13 and 12 reach the runner stage):
| rule | calls (42): mean % [90%] / vs card [90%], t | puts (42): mean % [90%] / vs card [90%], t |
|---|---|---|
| 30/50/60 card | +6.0 [-5.8, +19.5] / - | +0.1 [-11.2, +11.5] / - |
| Runner Card (a): +50% half, +100% runner, breakeven stop | +5.6 [-6.6, +19.3] / -0.38 [-3.00, +2.40], t -0.23 | +2.8 [-9.6, +15.4] / +2.73 [-0.90, +6.40], t +1.23 |
| (b) runner target +150% | +6.2 [-6.8, +20.0] / +0.20 [-2.90, +3.70], t +0.10 | +0.1 [-12.2, +12.6] / +0.01 [-3.90, +4.00], t +0.00 |
| (c) 25% trailing stop, +100% cap kept | +4.4 [-8.0, +16.6] / -1.60 [-4.10, +0.90], t -1.03 | +3.3 [-9.6, +16.2] / +3.23 [+0.20, +6.80], t +1.59 |
| (c') 25% trailing stop, no profit cap | +6.4 [-7.4, +21.4] / +0.41 [-3.40, +4.70], t +0.16 | +0.8 [-10.7, +13.5] / +0.70 [-1.80, +3.40], t +0.44 |
- On E1 the sign for (a) is reversed (calls -0.38, puts +2.73), on 12 to 13 runner-stage trades a leg. Nothing to read.
- Multiplicity: of 24 paired 90% intervals, 2 exclude zero (E2 calls (b), E1 puts (c)) and 2 more touch zero at the rounded edge (E2 calls (a) and (c')); chance alone predicts 2.4. Each of those four sits on a leg whose partner leg points the other way.

## Runner stage breakdown (decomposition of the same cells, not extra looks)
E2 pooled:
| rule | runner-stage trades (sessions) | contract 1 mean | contract 2 mean | contract 2 minus contract 1 | contract 2 ends below entry | contract 2 exits: runner target / stop / clock |
|---|---|---|---|---|---|---|
| Runner Card (a): +50% half, +100% runner, breakeven stop | 447 (44) | +66.8 | +71.0 | +4.3 | 15.7% | 184 / 78 / 185 |
| (b) runner target +150% | 447 (44) | +66.8 | +73.3 | +6.5 | 16.3% | 84 / 81 / 282 |
| (c) 25% trailing stop, +100% cap kept | 447 (44) | +66.8 | +70.9 | +4.1 | 4.7% | 178 / 147 / 122 |
| (c') 25% trailing stop, no profit cap | 447 (44) | +66.8 | +73.4 | +6.7 | 4.7% | 0 / 201 / 246 |
E1 pooled:
| rule | runner-stage trades (sessions) | contract 1 mean | contract 2 mean | contract 2 minus contract 1 | contract 2 ends below entry | contract 2 exits: runner target / stop / clock |
|---|---|---|---|---|---|---|
| Runner Card (a): +50% half, +100% runner, breakeven stop | 25 (25) | +66.2 | +74.1 | +7.9 | 12.0% | 10 / 3 / 12 |
| (b) runner target +150% | 25 (25) | +66.2 | +66.9 | +0.7 | 20.0% | 3 / 5 / 17 |
| (c) 25% trailing stop, +100% cap kept | 25 (25) | +66.2 | +71.7 | +5.5 | 4.0% | 9 / 6 / 10 |
| (c') 25% trailing stop, no profit cap | 25 (25) | +66.2 | +69.9 | +3.7 | 4.0% | 0 / 9 / 16 |
- E2 calls / puts (a): contract 2 minus contract 1 is +12.7 / -3.9 points; contract 2 ends below entry on 11.8% / 19.4% of runner-stage trades. The trailing stop trades the upside for fewer give-backs: it ends below entry on 4.7% of runner-stage trades (E2 pooled), against 15.7% for the breakeven stop, but it is stopped out more often (147 vs 78 of 447) and reaches +100% about as often (178 vs 184).

## What limits the numbers
- Extra looks, same data: these are 48 more looks on the same 45 sessions on top of the study's 324 cells and 81 alternative readings. The brief's three rules alone would be 36; the fourth is the second reading of (c). The Runner is not a registered strategy and nothing here is a finding; the unregistered cells pay a mining tax, and no |t| above 1.86 appears in any Runner cell.
- No directional skill assumed: calls and puts pooled. The legs differ in sign for the Runner's effect (E2 calls up, puts down), so the pooled number is an average of two different stories.
- One calm window: 45 sessions, 0 days of 2% or more, 5 of 1% or more, largest move 1.68%. A runner is a bet on a fat right tail (a trend day that carries a +50% option to +150%); a window with no such day cannot say what the +100% and +150% targets would collect, nor how the breakeven stop would behave in a fast reversal. Entries overlap, so read the intervals, not the trade count; E1 has only 25 runner-stage trades.
- 5-minute snapshots: every line overshoots. Contract 1's average fill on runner-stage trades is +66.8% against a +50% line; the breakeven stop fills below entry on 15.7% of runner-stage trades (E2 pooled); the trailing stop fills past its line too. A resting limit at +100% would fill on an intrabar touch, where this study fills at the bid of the next recorded snapshot. Moves between snapshots are unseen.
- Delayed CBOE quotes: the feed lags the recorder by about 16 minutes (median); times are quote stamps and prices are CBOE's delayed book, not a live fill.
- Two contracts bought at one ask, with no ask-size check and no commissions or fees (as in the study). A split exit means more fills than the one-contract card, and a one-contract account cannot split. Results are % of total entry cost, so a 2-lot's result equals the average of two 1-lots.
- The 60-minute clock runs from entry, as in the study, not from target 1: with target 1 at a median 25 minutes the runner gets a median 35 minutes, and a late target 1 leaves it almost none. A clock restarted at target 1 is a different rule and was not measured.
- Breakeven means the next bid at or below the entry ask, not the entry price itself; a trailing stop uses the highest recorded bid since entry, which a 5-minute grid understates.
- Zero settle-fallback exits in any Runner cell (every exit had a recorded bid), counted and reported.
- Checked outside the JSON: contract 1 equals the study's 30/50/60 cell trade by trade for all four rules, and pairs that never reach target 1 equal the card; the engine matches an independent two-position simulator on 16,000 random path-rule cases and on three real paths read by hand; 17 tests in src/test_exit_runner_study.py cover the three hand-made paths (target 1 then back to entry ends at +25%; target 1 then +100% ends at +75%; the -30% line first ends at -30%, or past it on an overshoot).
- Reproduce: /opt/anaconda3/bin/python src/exit_runner_study.py (writes results/exit_runner_2026-10-11.json).

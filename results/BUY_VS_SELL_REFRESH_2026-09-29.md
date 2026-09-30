# Buy vs sell, refreshed on every recorded session (2026-09-29)
STATUS: DESCRIPTION ONLY - nothing registered, no position follows from it. Extra looks today: 26 (21 in the grid file, 5 in the selling file); the two pre-declared studies were re-run, not re-designed.
Files: results/entry_exit_grid_2026-09-29.json, results/naked_selling_study_2026-09-29.json, results/straddle_test_2026-09-29.csv (Block B's rebuilt input). Registered JSONs untouched.
Each final run was executed once. Checked outside the JSON: on the old data range both scripts reproduce the registered numbers exactly, and the rebuilt CSV reproduces all 1,277 old rows. Old-sample figures below come from the registered JSONs.

## 1. Does holding a bought 0DTE option longer pay on average? No.
- 45 complete sessions, 5,860 ATM call/put entries bought at the ask and sold at the bid. 48 of 49 grid cells are negative; the exception is 11:00 ET at +30m, +0.4%, one cell of 49.
- Entry 10:00 ET (07:00 PT): +5m -1.1%, +10m -1.2%, +15m -1.1%, +20m -0.8%, +30m -0.4%; hold to settle -18.0% (32% win). Across entry hours settle runs -43.9% to -12.0%; late-day entries held long lose most.
- FIRST-GREEN at 10:00 ET wins 74.1% of rows yet averages -6.8%: average win +22.2%, average loss -89.9%, loss/win 4.05x (996 rows, 43 sessions): the rule is loss-heavy by construction.
- The 2026-08-31 read (26 sessions), 10:00 ET: short holds -1.3%..-2.1%, settle -25.0%, FIRST-GREEN -8.3%. Same story, slightly kinder now.

## 2. Does his 07:25 -> 08:05 PT pattern (10:25 -> 11:05 ET) make money on average? Not measurably.
One entry per session at the snapshot nearest 10:25 ET on the market clock, bought at the ask, sold at the bid 40 min later or held to settle. n = 42 sessions per cell (08-13, 09-10, 09-24 have no snapshot within 7.5 min).
| cell | +40m mean / median | win | avg win / avg loss (loss/win) | settle mean / win |
|---|---|---|---|---|
| ATM put | -7.6% / -20.2% | 40.5% | +38.7% / -39.1% (1.01x) | -19.2% / 33.3% |
| 1-strike-OTM put | -9.3% / -21.6% | 40.5% | +40.5% / -43.1% (1.06x) | -38.6% / 26.2% |
| ATM call | +4.9% / -5.8% | 45.2% | +51.0% / -34.7% (0.68x) | -17.6% / 28.6% |
| 1-strike-OTM call | +6.5% / -10.9% | 45.2% | +61.8% / -39.2% (0.63x) | -15.8% / 21.4% |
- Puts lose (t -1.02 and -1.11); calls are positive on the mean but negative on the median (t 0.56 and 0.6). Nothing in the +40m column separates from zero; the one cell past |t| 2 is the OTM put held to settle (t -2.48), one of 26 looks today.
- A timed exit gives loss/win of 1.01x-1.06x on puts, against FIRST-GREEN's 4.05x: a clock exit keeps wins and losses the same size; take-the-small-green, ride-the-red does not.
- Same cells on the grid's own fetch clock (recorder poll at 10:25, market time about 10:09): calls +2.1% / +2.8%, puts -2.1% / -2.2%. Same conclusion.

## 3. The seller's side, full sample: positive on average in this calm window, but thin for a single first-snapshot sale
| per share, per day, held to the close | days | won | mean | median | t | worst day | worst / avg win | max possible loss |
|---|---|---|---|---|---|---|---|---|
| Naked, entry at every book (Block B, pre-declared) | 45 | 35 | +0.468 | n/a | 4.54 | -1.091 | 1.4x | unbounded |
| Naked, first usable snapshot, sold at the bid | 50 | 33 | +0.426 | +0.975 | 1.34 | -6.33 | 3.6x | unbounded |
| Iron butterfly +-$5, shorts at bid, wings at ask | 50 | 33 | +0.256 | +0.605 | 1.11 | -3.27 | 2.6x | 2.455 avg, 3.27 max |
| Iron butterfly, study fill (shorts at ask, flatters) | 50 | 33 | +0.283 | +0.625 | 1.22 | -3.25 | 2.5x | 2.429 avg, 3.25 max |
- Block B's label says "first snapshot" but its code averages every book of the day (3,434 structures, about 76 a day). Its t of 4.54 is for that average; a single first-snapshot sale (row 2) is a different design with t 1.34.
- The wings cost 0.534/sh/day and cap the loss: on 2026-08-04 the naked lost 6.33/sh and the butterfly 2.58/sh. The butterfly's maximum loss is 246 dollars per contract on average (327 at most).
- A positive mean with t 1.11 to 1.34 on 50 days is a description, not a finding.

## 4. How quiet was the sample? Quiet (no 2% day), though not as quiet as the 09-23 wording said
- Across the 45 Block B days nothing moved 2% close to close; largest down day -1.54% (07-29), largest up day +1.68% (07-30). Chance of 45 sessions with no 2% day: 3.1% (it was 27.0% for the old 17).
- 5 days moved 1% or more (07-29 -1.54%, 07-30 +1.68%, 09-03 +1.05%, 09-17 +1.13%, 09-21 +1.55%) against about 12 expected from history; the naked all-books seller lost on 2 of them (07-29 -1.091, 09-21 -1.005).
- No new large down day: the -1.54% day (07-29) was already in the old 17. The 09-23 verdict ("not one of the 17 was a normal-sized down day") used the study's own straddle-payoff measure (0.86% max) and was wrong close to close; the verdict is now computed.
- A 95th-percentile day (2.33%) would cost the naked all-books seller -15.82/sh = 20.6 average winning days; the butterfly cannot lose more than 3.27/sh on this sample's credits.

## What limits these numbers
- 51 files; 45 usable in the grid and 45 in Block B by each study's own completeness rule (not the same set: the grid keeps 09-24, Block B keeps 08-25 via the CI leg); the butterfly uses 50 (07-08 is one stale-stamped book). SPY_2026-09-28/29.yfinance.csv were excluded (fallback feed).
- Only 0DTE is recorded: 1DTE, overnight and multi-day holds cannot be measured. "Holding longer" here means later the same day, or to settle.
- CBOE quotes lag the recorder's clock by about 16 minutes, so the grid's ET labels are poll times. Its settle uses the last book (stamped 15:46-15:51 ET), not the close: against official closes call settle means fall from -17.6% / -15.8% to -28.3% / -26.9%, put settle means rise (-19.2% to -15.0%, -38.6% to -32.7%); all stay negative.
- Butterfly entries follow ZDTE-003 as written: 08-13, 09-24 started late (first snapshot 58 and 252 min into the session) and 09-10's first book is stamped after its own fetch time (open item); all kept, 09-10 a +1.70/sh butterfly win.
- Block B's closes after 08-14 are stock-radar's settled daily closes (the 5m cache ends 08-14). Block A (refused straddles) still cannot answer; its "re-run after 2026-10-23" note is stale (priced refusals now expire to 2026-11-20).
- One calm window (SPY closes 743 -> 764) is one draw. Descriptive only; sim-only, and nothing here bears on a live trade.

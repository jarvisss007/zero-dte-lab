# Your fourteen key times: what the SPY record says

Paper research for Leo's Trading Firm, 2026-09-28 08:59 Pacific. Not a trade and not advice.

## The short answer

- SPY does move a little more in the 15 minutes after your times than after the times beside them: about 7% more. On a 771 dollar SPY that is about 5 cents per 15 minutes. The gap showed up in every calendar year since 2020 and in your reading year.
- Most of that comes from two times: 12:45 and 07:00, which together give 68% of the gap. 12:45 starts the last 15 minutes of the day, the busiest stretch of almost every afternoon. 07:00 is when many US economic reports come out.
- Take out the four times that sit on known news clocks and the gap shrinks to 0.002%, about 1.6 cents (strength +2.2, stronger than luck usually makes). That check was added after seeing the results.
- SPY does not turn around more often at your times. It turns about half the time at your times (50.4%) and at the times beside them (49.8%).
- The day's high and low do not land at your times more often than at nearby times, beyond what luck gives.
- For options, the extra movement did not pay. Buying the at-the-money call and put at your times and selling 15 minutes later lost 5.73 dollars a pair on average. At the times beside them it lost 4.02. That is 44 recorded days.
- About 71 of every 100 minutes of the trading day are within 10 minutes of one of your times. So a turn near one of your times is what you would see even if the clock meant nothing.

## What you said

You have watched these Pacific times for over a year: 06:45, 07:00, 07:20, 07:45, 08:05, 08:45, 10:00, 10:20, 11:00, 11:20, 11:45, 12:00, 12:20, 12:45.
You said SPY takes good turns or keeps going at them. You also named a Friday trade and today's reversal as examples.

## How it was tested

- The rules were written and saved before any price was loaded (commit 8d6ba89). No window or line was moved afterwards.
- One coding slip was fixed after the first run. On the 12 half-days the code had let in trades from after the 13:00 close. The written rules already left them out. The answers barely moved.
- Every trading day from 2020-07-27 to 2026-09-25: 1549 days of 5-minute SPY prices.
- 1 trading day in that span has no price data (2025-03-10). It is left out, not filled in.
- A second check uses only your reading year, 2025-09-26 to 2026-09-25: 251 days.
- Each day counts once. Many moves on one day are still one day.
- Each of your times is compared with the times 15 minutes before and after it, on the same day.
  That takes out the normal rhythm of the day, where the open and the close are always busier than lunch.
- 06:45 could not be checked for moves or turns. The 15 minutes before it start before the market opens.
- The strength score says how far a result sits from what luck makes. Between minus 2 and plus 2 is ordinary luck.

## The three answers

### Every day since July 2020 (1549 days)

1. Moves. In the 15 minutes after your times SPY moved 0.108% on average. After the times beside them it moved 0.101%. Gap 0.007% over 1548 days, strength +9.4, stronger than luck usually makes.
2. Turns. SPY turned at 50.4% of your times and 49.8% of the times beside them. Gap +0.7 points over 1548 days, strength +1.6, could easily be luck.
3. Highs and lows. Per 100 days, 41.2 of the day's highs and lows landed in your 10-minute windows and 37.5 in matching windows 15 minutes away. Over 1541 days that is strength +1.5, could easily be luck.

### Your reading year only (251 days)

1. Moves. In the 15 minutes after your times SPY moved 0.086% on average. After the times beside them it moved 0.081%. Gap 0.005% over 251 days, strength +3.9, stronger than luck usually makes.
2. Turns. SPY turned at 50.6% of your times and 48.8% of the times beside them. Gap +1.8 points over 251 days, strength +1.7, could easily be luck.
3. Highs and lows. Per 100 days, 41.8 of the day's highs and lows landed in your 10-minute windows and 38.2 in matching windows 15 minutes away. Over 251 days that is strength +0.6, could easily be luck.

Six answers were read. Luck alone makes at least one of six look strong about 24% of the time.
Cleared the luck line: moves, every day (strength +9.4); moves, reading year (strength +3.9).

## What carries the moves answer (added after seeing the results)

This is a look inside answer 1, not a new test.

| Your time | Share of the gap it supplies | Gap if this time is left out |
|---|---|---|
| 07:00 | 21% | 0.006%, strength +7.9 |
| 07:20 | 6% | 0.007%, strength +9.1 |
| 07:45 | 0% | 0.008%, strength +9.7 |
| 08:05 | 2% | 0.008%, strength +9.3 |
| 08:45 | -5% | 0.008%, strength +10.0 |
| 10:00 | 1% | 0.008%, strength +9.5 |
| 10:20 | 7% | 0.007%, strength +8.6 |
| 11:00 | 11% | 0.007%, strength +8.3 |
| 11:20 | 4% | 0.007%, strength +9.3 |
| 11:45 | -3% | 0.008%, strength +10.3 |
| 12:00 | 8% | 0.007%, strength +8.8 |
| 12:20 | 1% | 0.008%, strength +9.4 |
| 12:45 | 47% | 0.004%, strength +5.3 |

Without 07:00, 10:00, 11:00 and 12:45, the four times named in advance as news clocks, the gap is 0.002% (strength +2.2, stronger than luck usually makes) on every day, and 0.001% (strength +0.5, could easily be luck) in your reading year.

## Single times (a description, not a test)

Fourteen times and three questions make 42 more readings. About 2 should look strong by luck alone.

| Your time | Move after it, vs beside it | Turn rate, vs beside it | Highs and lows in its window, vs beside it |
|---|---|---|---|
| 06:45 | not checkable | not checkable | not checkable |
| 07:00 | 0.149% vs 0.130% (strength +4.4) | 48.7% vs 48.1% | not checkable |
| 07:20 | 0.132% vs 0.127% | 49.9% vs 49.7% | 6.0 vs 4.6 per 100 days |
| 07:45 | 0.114% vs 0.114% | 49.1% vs 49.4% | 4.0 vs 5.2 per 100 days |
| 08:05 | 0.108% vs 0.106% | 50.8% vs 50.0% | 4.1 vs 3.0 per 100 days |
| 08:45 | 0.091% vs 0.096% | 49.8% vs 49.7% | 2.9 vs 2.0 per 100 days |
| 10:00 | 0.089% vs 0.088% | 51.2% vs 50.0% | 3.1 vs 2.0 per 100 days (strength +2.0) |
| 10:20 | 0.093% vs 0.087% | 51.3% vs 49.8% | 2.6 vs 2.6 per 100 days |
| 11:00 | 0.096% vs 0.086% (strength +3.2) | 51.4% vs 47.0% (strength +2.8) | 3.5 vs 2.7 per 100 days |
| 11:20 | 0.095% vs 0.092% | 49.1% vs 51.0% | 2.0 vs 3.3 per 100 days (strength -2.2) |
| 11:45 | 0.094% vs 0.096% | 52.6% vs 48.7% (strength +2.1) | 3.4 vs 3.1 per 100 days |
| 12:00 | 0.098% vs 0.091% (strength +2.2) | 49.2% vs 50.3% | not checkable |
| 12:20 | 0.098% vs 0.097% | 51.6% vs 51.1% | 4.4 vs 4.8 per 100 days |
| 12:45 | 0.145% vs 0.101% (strength +11.5) | 51.8% vs 52.5% | 5.4 vs 4.3 per 100 days |

Rows with a strength past 2 either way:
- 07:00 Pacific: moves after it differ from beside it: +0.018% (0.149% vs 0.130%), strength +4.4, 1548 days.
- 10:00 Pacific: the day's high or low lands in its window more or less than beside it: +1.2 per 100 days, strength +2.0, 1529 days.
- 11:00 Pacific: moves after it differ from beside it: +0.010% (0.096% vs 0.086%), strength +3.2, 1536 days.
- 11:00 Pacific: turn rate differs from beside it: +4.4 points (51.4% vs 47.0%), strength +2.8, 1516 days.
- 11:20 Pacific: the day's high or low lands in its window more or less than beside it: -1.3 per 100 days, strength -2.2, 1529 days.
- 11:45 Pacific: turn rate differs from beside it: +3.8 points (52.6% vs 48.7%), strength +2.1, 1514 days.
- 12:00 Pacific: moves after it differ from beside it: +0.007% (0.098% vs 0.091%), strength +2.2, 1536 days.
- 12:45 Pacific: moves after it differ from beside it: +0.044% (0.145% vs 0.101%), strength +11.5, 1536 days.

Named before the data was loaded: US economic reports come out at 07:00 Pacific, Treasury auction results at 10:00, Fed decisions at 11:00 on eight days a year, and the closing order imbalance at 12:50. A busy row at one of these is the news calendar. Option sellers know that calendar too.

## The shape of a normal day

Average size of the next 15-minute move, every day since July 2020:

| Pacific time | Average 15-minute move | One of your times? |
|---|---|---|
| 06:35 | 0.151% |  |
| 06:45 | 0.143% | yes |
| 07:00 | 0.149% | yes |
| 07:15 | 0.130% |  |
| 07:45 | 0.114% | yes |
| 08:30 | 0.100% |  |
| 09:30 | 0.084% |  |
| 10:00 | 0.089% | yes |
| 11:00 | 0.096% | yes |
| 12:00 | 0.098% | yes |
| 12:30 | 0.101% |  |
| 12:45 | 0.145% | yes |

The day is loud at the open, quiet at lunch and loud again at the close, whatever the clock face says.

## What it means for options

The lab has recorded real SPY same-day option quotes on 45 days (2026-07-17 to 2026-09-25).
The check: buy the at-the-money call and put together at the asking price at the time. Sell both at the bid 15 minutes later.

- At your times: -5.73 dollars a pair on average, -3.4% of the 190 dollars paid, over 44 days. It made money on 6 of those days.
- At the times beside them: -4.02 dollars a pair, -2.7% of the 181 dollars paid, over 44 days. It made money on 5 of those days.
- Same days, your times minus the times beside them: -1.63 dollars a pair over 43 days, strength -1.7, could easily be luck.

No single time paid on average. The least bad was 11:20 at -0.08 dollars a pair over 37 days.
12:45 could not be priced: no exit book: the recorder's last book on any day is 15:51 ET, never within 2 minutes of 16:00 ET.

A bit more movement does not pay if the price of the option already expects it. Here it did not pay at your times or beside them. The pair loses its spread and 15 minutes of time value, and the extra move at your times was not enough to cover that.
This covers 45 recorded days, not years. It is a description, not a verdict.

## Your two days

### Friday 2026-09-25

Opened 768.78. Low 766.29 at 07:15. High 772.28 at 12:51. Closed 771.35.

| Pacific time | SPY | 767 put, built-in value | 767 put, recorded bid |
|---|---|---|---|
| 06:45 | 769.49 | 0.00 | no book within 2 minutes |
| 07:00 | 769.73 | 0.00 | no book within 2 minutes |
| 07:20 | 767.05 | 0.00 | no book within 2 minutes |
| 07:45 | 767.94 | 0.00 | no book within 2 minutes |
| 08:05 | 769.35 | 0.00 | 0.45 (quote at 08:03) |
| 08:45 | 767.74 | 0.00 | no book within 2 minutes |
| 10:00 | 770.44 | 0.00 | 0.14 (quote at 09:58) |
| 10:20 | 770.90 | 0.00 | 0.08 (quote at 10:21) |
| 11:00 | 771.16 | 0.00 | 0.05 (quote at 10:59) |
| 11:20 | 771.28 | 0.00 | 0.03 (quote at 11:19) |
| 11:45 | 771.03 | 0.00 | 0.04 (quote at 11:44) |
| 12:00 | 770.67 | 0.00 | 0.03 (quote at 11:59) |
| 12:20 | 770.79 | 0.00 | 0.02 (quote at 12:19) |
| 12:45 | 771.18 | 0.00 | 0.01 (quote at 12:44) |

Friday's prices do not match the day as it was described. In regular hours the low was 766.29 at 07:15, and SPY never traded at 765.50 or 763.19. The lab's own recorded quotes agree: their lowest SPY price that day was 766.65 at 07:17. The close of 771.35 does match. Thursday 2026-09-24 is the closest match: low 763.24 at 08:14, close 767.18. A 767 put expired worth 0.00 that day too. On Friday SPY stood above 767 at every one of your times. So at each of them the 767 put was only worth its leftover time value. The lab's recorded bid for that put was 0.45 at 08:03 and 0.01 at 12:44. At your other times no recorded quote landed within 2 minutes. The biggest swing between two of your times was 08:45 to 10:00: SPY moved +2.70. Held to the close at 771.35, a 767 put expired worth nothing. Selling it at your next time would have kept whatever time value was left then. Holding to the close kept none. That is one day. Whether your times help on average is what the three answers above measure.

### Today 2026-09-28, up to 08:59 Pacific

Opened 768.35. Last 765.42.
At your times so far: 06:45 767.63, 07:00 768.36, 07:20 767.49, 07:45 765.26, 08:05 764.61, 08:45 764.93.
So far today the low was 763.72 at 07:55, 10 minutes after your 07:45 time. The high so far was 768.61 at 06:32.

One or two days cannot show whether a clock time matters. Fifteen hundred days can, and that is what the answers above use.

## Honest limits

- Prices up to 2026-07-10 come from Alpaca's free feed, which sees trades on one exchange only (IEX). From 2026-07-13 they come from Yahoo. On the 5 days both cover, their 5-minute closes differed by 1.5 cents in a typical bar. They put the day's high in the same 5-minute bar on 5 of 5 days, and the low on 5 of 5.
- 1 trading day in the span has no data (2025-03-10) and is left out.
- 06:45 could not be checked at all. Its moves and turns need the 15 minutes before 06:30. Its high-and-low window has no clean comparison window. 07:00 and 12:00 also sit out the high-and-low question for that reason. These rules were fixed before the data was loaded.
- Some of your times are only 15 to 20 minutes apart, so a time and its neighbour share some of the same minutes.
- Three times have a comparison on one side only (07:00, 12:00, 12:45). Near the open and the close the market gets busier or quieter quickly, so a one-sided comparison is not a perfect twin. 12:45 is compared with the 15 minutes before it, and the last 15 minutes of the day are busier almost every day.
- The option check covers only the days the lab recorded, with quotes about every 5 minutes. A quote had to be within 2 minutes of your time, so some days are missing and fills can be up to 2 minutes off.
- This checks the clock times alone. It does not check your chart reading at those times. That is a different question.

Files: src/key_times_study.py (the rules, then the code), results/key_times_study.json (every number).

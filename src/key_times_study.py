#!/opt/anaconda3/bin/python
"""key_times_study.py - does SPY do something special at Anupam's fourteen clock times?

PRE-REGISTRATION. Written 2026-09-28 ~08:45 PT, BEFORE any price bar or option book was loaded
for this study, and committed on its own before the implementation. Nothing below may be tuned
after a run. If a part of the design proves impossible on the data, the output says so and the
design is NOT changed. DESCRIPTION ONLY: paper research, not a strategy, registers no variant,
places and advises no trade.

THE CLAIM (his, noted for over a year): SPY "takes good turns or keeps continuing" at
    06:45 07:00 07:20 07:45 08:05 08:45 10:00 10:20 11:00 11:20 11:45 12:00 12:20 12:45   (Pacific)
Pacific = Eastern minus 3 hours all year (both observe DST on the same dates), so the key times are
    09:45 10:00 10:20 10:45 11:05 11:45 13:00 13:20 14:00 14:20 14:45 15:00 15:20 15:45   (Eastern)
All session logic runs in New York time; every time printed for him is Pacific.

DATA
  bars      (1) ~/ie-pro-project/output/alpaca_SPY_5m_2019-07-01.csv (time,open,high,low,close,volume;
                ET with offset; 2020-07-27 .. 2026-07-10).
            (2) Yahoo chart API, SPY, range=60d, interval=5m, header User-Agent "Anupam Patil research
                apati077@ucr.edu"; epoch seconds -> America/New_York; rows with any null OHLC dropped.
            A date that (1) holds uses (1) only; a date only (2) holds uses (2). On dates both hold, the
            two are compared bar by bar (closes at the same start time) as a DATA CHECK, not a test.
            A duplicated bar start keeps its first row (counted and reported).
  session   bars are labelled by their START time; regular session only: start in [09:30, 16:00) ET.
            A date counts only if the estate's NYSE calendar (stock-radar/sessions.py, byte-identical
            mirror in this repo's src/sessions.py) says it is a session AND it is on or before
            2026-09-25 (settled). Today, 2026-09-28, is never in the study sample. Nothing is imputed:
            a missing bar is a missing mark.
  early closes  the NYSE 13:00 ET closes in the span are listed in the code (2020-11-27, 2020-12-24,
            2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24,
            2025-07-03, 2025-11-28, 2025-12-24); they simply lack afternoon marks.

MARKS AND MOVES
  price at mark T   P(T) = close of the 5-minute bar that ENDS at T (starts at T-5). Marks exist at
                    09:35 .. 16:00 ET. No bar inside the session ends at 09:30, so P(09:30) never exists.
  B(T) = 10000 * (P(T) / P(T-15) - 1)      the 15 minutes BEFORE T, basis points
  A(T) = 10000 * (P(T+15) / P(T) - 1)      the 15 minutes AFTER T, basis points
  valid mark        P(T-15), P(T) and P(T+15) all exist that day. Applies to key times AND neighbours.
  CONSEQUENCE, stated before any data: 06:45 PT (09:45 ET) can never be a valid mark (its T-15 would
  be 09:30), so 06:45 PT is IMPOSSIBLE in Q1 and Q2. It is not replaced by the opening print.
  neighbours of T   T-15 and T+15, each used only if it is not itself a key time and is valid that day.
      07:00 -> 07:15 only (06:45 is a key time)   07:20 -> 07:05, 07:35   07:45 -> 07:30, 08:00
      08:05 -> 07:50, 08:20   08:45 -> 08:30, 09:00   10:00 -> 09:45, 10:15   10:20 -> 10:05, 10:35
      11:00 -> 10:45, 11:15   11:20 -> 11:05, 11:35   11:45 -> 11:30 only (12:00 is a key time)
      12:00 -> 12:15 only (11:45 is a key time)   12:20 -> 12:05, 12:35
      12:45 -> 12:30 only (13:00 PT = 16:00 ET has no T+15)                          (all Pacific)
  That is 22 neighbour marks; no neighbour is shared by two key times. A key time with no usable
  neighbour that day is dropped that day (Q1 and Q2). "Q1-scored key times" = valid key times with
  at least one usable neighbour.

THE THREE HEADLINE CELLS (the only tests)
  Q1 ACTIVITY   r_T = |A(T)| - mean(|A(N)|) over T's usable neighbours N.
                Per day x = mean of r_T over that day's Q1-scored key times.
                H0: mean(x) = 0; t over days, two-sided. Units: basis points.
  Q2 TURNS      a turn at mark M is sign(A(M)) != sign(B(M)); a mark with A(M) = 0 or B(M) = 0 is not
                counted either way. Per day y = (turns / counted) over that day's Q1-scored key times
                minus (turns / counted) over those key times' usable neighbours (the Q1 neighbour
                marks). A day with nothing counted on either side is dropped.
                H0: mean(y) = 0; t over days, two-sided. Positive = more turning at his times,
                negative = more continuation. Units: percentage points of turn rate.
  Q3 EXTREMES   a day's low bar = the first 5-minute bar whose low equals the session low; high bar
                likewise with the high. Key window(T) = the bars starting T-5 and T. Placebo(T) = the
                bars starting T+10 and T+15; if that overlaps ANY key window, or needs a bar outside
                the session (start before 09:30 or at/after 16:00), then the bars starting T-20 and
                T-15 under the same two conditions; if both fail, T is dropped from BOTH sets on
                every day. Resolved here before any data (the code asserts it):
                  06:45 PT dropped (+15 hits 07:00's window; -15 needs the pre-market 09:25 ET bar)
                  07:00 PT dropped (+15 hits 07:20's window; -15 hits 06:45's window)
                  12:00 PT dropped (+15 hits 12:20's window; -15 hits 11:45's window)
                  07:20 +15   07:45 -15   08:05 +15   08:45 +15   10:00 -15   10:20 +15
                  11:00 -15   11:20 +15   11:45 -15   12:20 +15   12:45 -15 (its +15 needs a 16:00 bar)
                Per day a key time counts only if all four of its bars exist that day (an early close
                drops the afternoon ones), and a day enters Q3 only with its complete bar grid (78 bars;
                42 on a listed early close) - a missing bar could hide the extreme.
                Per day z = SUM over counted T of [extremes (0..2) in key(T) - extremes in placebo(T)];
                a bar that sits in two placebo windows counts in each, so both sides carry the same
                exposure (two bars per counted key time). H0: mean(z) = 0; t over days, two-sided.

STATISTICS  One observation per trading day. t = mean / (sd(ddof=1) / sqrt(n_days)); n = days,
            clustered_by = session date. Each headline cell reports mean, sd, n_days, t and a 95%
            interval (mean +/- 1.96 standard errors). |t| >= 2 is called loud; nothing else is
            called anything.
SAMPLES     FULL   = every settled session the data holds (2020-07-27 .. 2026-09-25, with whatever
                     gap the Yahoo window leaves after 2026-07-10 - stated, never filled).
            LAST12 = 2025-09-26 .. 2026-09-25, his reading period.
LUCK COUNT  3 cells x 2 samples = 6 looks. Chance of at least one |t| >= 2 by luck alone =
            1 - (1 - 0.0455)^6 = 24.4% (LAST12 sits inside FULL, so the looks are not independent;
            the figure is the usual approximation). Printed with the results.

DESCRIPTIVE ONLY (not tests; outside the luck count; labelled as such in every output)
  - Q1, Q2 and Q3 for each of the 14 key times separately, FULL sample (mean, t over days, n days).
    14 x 3 = 42 more looks: about 2 of them should show |t| >= 2 by luck alone.
  - Q1 per calendar year (FULL).
  - the plain average |A| at every mark 09:35 .. 15:45 ET (where P(M) and P(M+15) exist), so the
    intraday U-shape (loud open, quiet lunch, loud close) is visible.
  - where the day's low bar and high bar fall: share of Q3 days per 5-minute bar (context for Q3).
  - scheduled clocks, named now so they are not "discovered" later: US data releases at 10:00 ET
    (07:00 PT), Treasury auction results at 13:00 ET (10:00 PT), Fed decisions at 14:00 ET
    (11:00 PT, eight days a year), the closing-imbalance publication at 15:50 ET (12:50 PT). A loud
    row at one of these is the calendar, and the options market knows the calendar.

OPTIONS DESCRIPTION (not a test; reported only if the recorded books support it)
  books   the lab's own CBOE 0DTE chain recorder: data/chains/SPY_YYYY-MM-DD.csv (laptop leg) and
          data/chains_ci/SPY_YYYY-MM-DD.csv (cloud leg), exact file names only. The yfinance fallback
          files (SPY_<date>.yfinance.csv) are excluded (ZDTE-010 (c): they feed nothing until a ruling
          names it). Legs unioned, deduped on (quote_ts, type, strike), earliest fetch kept. Book time =
          the book's own quote_ts (ET), never the fetch time. 0DTE only (expiry = session date);
          settled sessions through 2026-09-25 only.
  trade   for every session and mark T - all 14 key times and, separately, the 22 Q1 neighbour marks:
          entry book = the book whose quote_ts is nearest T within 2 minutes (tie -> earlier); exit
          book = the book nearest T+15 within 2 minutes. Strike = the strike nearest the entry book's
          spot (tie -> lower). BUY the call and the put at that strike at the ASK in the entry book,
          SELL both at the BID in the exit book. Each leg must exist in both books with ask > 0,
          bid >= 0 and ask >= bid. P&L $ = 100 * (bids out - asks in); % of debit =
          (bids out - asks in) / asks in * 100.
  report  per group: mean over days of each day's mean P&L ($ and % of debit), n days, a descriptive
          day-clustered t, and the key-minus-neighbour difference on days that have both; per key
          time: n days, mean $ and mean %. No model is substituted if the books are missing: the
          output says exactly why and skips.

HIS TWO DAYS (description; one day proves nothing)
  Yahoo 1-minute bars (range=5d, interval=1m) for 2026-09-25 and 2026-09-28 (today, up to the latest
  bar). Price at a key time T = close of the 1-minute bar that ENDS at T. Session low and high with the
  Pacific start time of the 1-minute bar holding each (first if tied); the 09-25 close (last
  regular-session 1-minute close, and Yahoo's daily close). The minutes on 09-25 whose range contains
  765.50 (his reported exit level) are listed; nothing is inferred from them. Friday under "hold until
  the next key time" versus "hold to the close": SPY at each key time, the move to the next key time,
  the 767 put's intrinsic floor max(767 - SPY, 0), and - if the recorded CBOE book holds the 767 put
  that day - its BID in the book nearest each key time within 2 minutes.

OUTPUTS   results/key_times_study.json (every number) and results/KEY_TIMES_STUDY.md (plain English).
Run:      /opt/anaconda3/bin/python src/key_times_study.py
"""
from __future__ import annotations

KEY_PT = ["06:45", "07:00", "07:20", "07:45", "08:05", "08:45", "10:00",
          "10:20", "11:00", "11:20", "11:45", "12:00", "12:20", "12:45"]


def main() -> None:
    raise SystemExit("pre-registration only: the implementation is written after this commit")


if __name__ == "__main__":
    main()

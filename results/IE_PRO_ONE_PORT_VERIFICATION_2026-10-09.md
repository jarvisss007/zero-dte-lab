# IE Pro ONE trigger — Python port, verification (2026-10-09)

Step 1 of the simulated paper trader. **Paper only. A description of a port, not a claimed edge** — the lab's
verdicts on same-day SPY options and on the r17 sweep concept (README) still stand.

Port: `src/ie_pro_one_trigger.py`, written from `pine/ie_pro_one.pine` (v1.3), not from any earlier port.
Reproduces the chart's inputs: OB Primary Trigger, Both, pivot 5/5, ATR(14) x1.0 stop, 2.5R, min 3 bars between
signals; use_ob = use_brk = false, so the only trigger is a **liquidity sweep** (low pierces the last swing low and
closes back above it, with trend = +1, a green candle and a bullish 15m bias; mirror for shorts).

## Evidence
Eight TradingView screenshots, 2026-09-30 .. 10-09: SPY 5m, extended hours ON, Replay mode. Compared against
Yahoo 5m bars with pre/post market (`includePrePost`).

| Check | Result |
|---|---|
| Yahoo OHLC vs chart OHLC on 8 spot bars | 6 exact; 1 close 1c off; 1 post-market bar missing in Yahoo |
| Plan-label numbers (E / SL / TP1 / TP2) on the 3 regular-hours signals | all 3 reproduce to the cent (SL 1c off on one) |
| Regular-hours signals on the chart vs the port, 8 sessions | **3 of 3 identical, zero extras** (09-30 09:40 PT long, 10-07 12:20 PT long, 10-09 12:55 PT long) |
| Regular-hours sweep markers (06:30-12:55 PT) | 59 of 63 chart markers reproduced; 4 missing (all 10-08, below); 1 port-only (10-01 06:50 PT, unexplained); 4 port-only markers sit under the chart's own trade arrows |
| Pivot tie rule (strict vs left-strict) | no difference on this window |
| 15m-bias mode (leaky / developing / fixed) | identical regular-hours signals on these 8 days — cannot tell from the screenshots which one the chart runs |

## Known data limits (free Yahoo data vs TradingView's feed)
1. **Premarket volume is zero** in Yahoo, so the session VWAP is undefined before 09:30 ET and premarket signals cannot be
   reproduced. The chart's 09-30 04:35 PT short (E 764.70) is the example: the bar's close matches exactly, the VWAP leg cannot.
2. **Premarket bars are sparse.** Pivots count bars, so a missing bar shifts which swing low is live. 10-08 06:15-06:25 PT
   is absent in both Yahoo 5m and 1m; with those bars the 06:40 low (774.45) is a valid pivot and explains the four
   chart-only sweeps at 08:25 / 08:40 / 08:45 / 09:05 PT.
3. **Post-close bars carry bad prints** (10-05 13:00 and 13:10 PT show a 769.452 low; the chart's low is about 774). These create
   false sweeps and can poison the swing-low state overnight.
4. **Volume is not the same feed** (Yahoo consolidated vs the chart's AMEX): feeds only the VWAP leg of the trigger.
5. **The trigger is sensitive to the feed.** Over Jul 17 - Oct 9 (RTH signals, developing mode): as-is 18; dropping post-close
   bars changes 1 of them; using regular-hours bars only changes 10 of 18.

## How often it fires
RTH signals 2026-07-17 .. 2026-10-09 (60 sessions): 18 (8 long, 10 short), on 16 of 60 days = **0.30 per session**
(fixed mode: 13, 0.22). At that rate 40 sessions give about 12 trades. The brief's 4-5 trades a day is not possible with this
trigger.

## Option-chain coverage (data/chains + data/chains_ci), sessions since 2026-09-30
- Books run from about 09:36 ET to about 15:45 ET (quote_ts trails fetched_at by about 15 minutes). No book for the first
  minutes of the open or the last ~15 minutes.
- 09-30, 10-01, 10-05, 10-06, 10-07, 10-08, 10-09: 75-77 snapshots each, no gap over 8 minutes.
- **10-02: 22 snapshots, first at 13:23 ET** — the morning is missing, plus two gaps of about 30 minutes.
- One expiry per snapshot (the same-day expiry).
- 10-09 12:55 PT (15:55 ET) signal falls after the last book: it could not be traded in this data.

## Open decisions for the pre-registration
- 15m-bias mode: `developing` (what a live chart shows at the 5m close; recommended) or `fixed` (the script's own r18 switch, slower).
  `leaky` is not decidable in real time and is excluded.
- Post-close bars: keep (faithful to the chart, but carries bad prints) or drop (cleaner, changes 1 of 18 signals).
- What happens to a trade whose 60-minute clock runs past the last recorded book.

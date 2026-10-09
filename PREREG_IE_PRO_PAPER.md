# PREREG — the simulated paper trader on the IE Pro triggers (PTR-001)

**Status: DRAFT 2026-10-09 — NOT REGISTERED, NOTHING COUNTS until Anupam's "ok" on this document (REG-PP-001).**
Paper only. Nothing here places an order, talks to a broker or holds a key. A forward *description* of a rule on recorded
data — not a claimed edge. The lab's verdicts stand: same-day SPY options showed **no edge after costs** (README), the r17
sweep concept was convicted overfit, and the only earlier score of IE Pro labels (7 hand-keyed, Aug 2026) was 1 win in 6.
**Prior: no edge. The expected readout is FAIL.** (If a PASS ever appears, the mining tax in the ledger applies before anyone acts.)

## 1. What is registered
Two variants, one shared execution rule, scored separately, never pooled:
- **PTR-001/v1 — IE Pro.** Trigger = `src/ie_pro_trigger.py`, ported from `pine/ie_pro_indicator.pine` (the indicator that
  prints CONFIRMED LONG/SHORT [A+/A/B]), chart settings in `pine/IE_PRO_CHART_SETTINGS_2026-10-09.md`. Primary.
- **PTR-001/v2 — IE Pro ONE sweep.** Trigger = `src/ie_pro_one_trigger.py` (OB Primary Trigger, Both), from `pine/ie_pro_one.pine`.
  Second; fires ~0.27 times per session, so its readout is descriptive only.
Evidence the ports are the rule (not the chart's label timestamps): `pine/IE_PRO_CHART_SETTINGS_2026-10-09.md`,
`results/IE_PRO_ONE_PORT_VERIFICATION_2026-10-09.md`. **The paper trader does NOT reproduce the chart's labels bar for bar:**
the free-running IE Pro port matches 3 of 30 chart labels (entry/stop/target numbers exact where it matches); with the 20-bar
spacing anchored on the chart's own labels it fires on 10 of 14 regular-hours labels. The reasons are the data (§2), not the rule.

## 2. Data (frozen)
- SPY 5-minute bars from Yahoo chart data with pre/post market (User-Agent `Anupam Patil research apati077@ucr.edu`),
  archived per session at first full capture after the close and never rewritten (settled prices only; Firm Brain §1, §8).
- **Dropped before the trigger runs:** every bar stamped at or after the session close (16:00 ET; 13:00 ET on early closes per
  `src/sessions.py`) — Yahoo's post-close bars carry bad prints (10-05: a 769.452 low where the chart's was ~774); and any flat
  carry-forward bar (O=H=L=C equal to the prior close with volume 0; Firm Brain §18). Premarket bars are kept.
- **Known limits, disclosed:** Yahoo premarket volume is 0, so the volume leg and VWAP cannot be true before the open and
  **no premarket signal can fire** (13 of the chart's 30 labels were premarket/post); Yahoo volume is a different feed from the
  chart's (0.48-0.89 of consolidated); some premarket bars are missing (10-08 06:15-06:25 PT), and pivots/spacing count bars.
  The trigger is feed-sensitive: dropping bars changes its signals (v2: regular-hours-only bars change 10 of 18).
- Warm-up: the archive is seeded with Yahoo's last ~60 days at registration (stamped SEED, never scored) so EMA/RSI/ATR are settled.
- 15-minute bias mode `developing` (the 15m bar as of the 5m close; decidable in real time). `leaky` is excluded.

## 3. Signal (frozen; no tuning)
Parameters: EMA 9/21, RSI 14 with 55/45, Volume MA **20**, min bars between signals 20 (v1); pivot 5/5, ATR 14 x1.0, min bars 3,
sweep-only trigger, direction Both (v2). The trigger runs on the whole archive so spacing counts every earlier signal.
A signal is **tradable** only if its bar opened at or after 09:30 ET and its decision time (bar open + 5 minutes) is at least 5
minutes before the close. Signals outside that (premarket, late) are logged and still count for spacing.
Expected rate over the 60 archived sessions: v1 173 regular-hours signals = 2.88 per session (42 of 60 sessions have 3 or more,
maximum 4); v2 16 = 0.27 per session.

## 4. Entry (shared)
- Instrument: the SPY option expiring the same session, **call on a long signal, put on a short**.
- Strike: call = the lowest listed strike strictly above the snapshot's `spot`; put = the highest listed strike strictly below it.
- Fill: at the **ask** of the first recorded snapshot whose `quote_ts` is at or after the decision time and within 10 minutes of
  it, and before (close - 5 minutes). Otherwise skip. No cheaper later snapshot is ever substituted (Firm Brain §8, ZDTE-004).
- Needs a two-sided market (bid > 0 and ask > 0) and at least one later snapshot of the same contract.
- Max 5 entries per session; one open at a time (a signal whose decision time falls before the open trade's exit is skipped).
- **Every skip is recorded with its reason** (NO_BOOK_WINDOW, NO_TWO_SIDED_MARKET, TOO_EXPENSIVE, POSITION_OPEN, SESSION_CAP,
  TOO_LATE, NO_LATER_BOOK) — a silent zero is not allowed (Firm Brain §3).

## 5. Size
Paper capital C = **$5,000, fixed (never compounded)**. Budget per trade C/5 = $1,000. Contracts = floor(1000 / (ask x 100));
if that is 0 the signal is skipped (TOO_EXPENSIVE) and recorded.

## 6. Exits (frozen)
Checked at every later snapshot of the same contract, in order, against the **bid**:
1. bid >= 1.50 x entry ask -> **TARGET**, filled at exactly 1.50 x entry ask;
2. bid <= 0.70 x entry ask -> **STOP**, filled at **that snapshot's bid** (gaps below the line are real);
3. `quote_ts` >= entry `quote_ts` + 60 minutes -> **CLOCK**, filled at that snapshot's bid;
4. no more snapshots that session -> **BOOK_END**, filled at the last snapshot's bid.
Snapshots are about five minutes apart (and the recorded quotes trail the wall clock by about 15 minutes), so a touch between
snapshots is invisible and a target can be passed before it is seen; a target fill at the line is therefore generous to the rule.
The indicator's own SPY levels (SL = bar low/high -/+ 0.5 ATR, TP1/TP2 = 1.5/3 ATR) are stored on each row and read
descriptively only; they never move a trade.

## 7. Fees
$0.36 per contract per side, both sides, on every filled trade.

## 8. What is counted, and when
- **Counted session:** a session after the approval stamp (§10) with a complete bar archive (at least 90% of the expected
  regular-hours bars) AND book coverage of at least 75% of the expected snapshots
  (distinct `quote_ts` between 09:35 ET and the close, expected = minutes/5). Anything else is **DATA-GAP: logged, not scored,
  not counted** (e.g. 2026-10-02: 22 snapshots, morning missing). A counted session with no filled trade counts as a zero-P&L session.
- **n is counted in sessions** (`clustered_by: session date`), never trades. **n = 60 counted sessions** per variant.
  **No PASS/FAIL and no headline number before n = 60.** Before that the Sunday report prints n, trades and a plain
  "not yet readable".
- The runner is keyed to the settled session, not the run: one row set per session, idempotent, and a run that finds no new
  settled session writes nothing (Firm Brain §15).

## 9. Readout at n = 60 (pre-declared; the council may only make it stricter)
Reported in **percent** in every public place (per-trade net return on cost; session net as % of C): per-trade net %, mean and
median; win rate **beside** the mean's sign and size; average loss / average win; worst loss; fees share of gross; per half
(first 30 / last 30 sessions) so a sign that flips is visible (Firm Brain §20); day-clustered 95% bootstrap interval of the
mean session net (10,000 resamples of sessions).
- **Benchmark: the mirror twin** — the opposite option at the same decision time under the identical rules, recorded for every
  filled trade. The signal's direction is only worth anything if it beats its mirror.
- **PASS** only if all hold: the clustered 95% interval of mean session net excludes zero on the upside; the mean has the same
  sign in both halves; and the mean beats the mirror twin's. Otherwise **FAIL: no edge shown**. A PASS is never a trade
  instruction: the ledger's mining tax (trials_total) and an `edge-refute` panel come first, and the firm's no-live-trades rule stands.
- A halt on acting must not halt measuring (Firm Brain §24): signals and twins keep being recorded whatever happens.

## 10. Freeze, shakedown, change control
- Frozen when registered. Any change — a parameter, the data filter, the fill or exit rule, the strike rule — is a **new
  registered variant** with its own ledger trial, never an edit. No tuning on outcomes.
- **SHAKEDOWN:** replays of recorded sessions from 2026-09-30 test the code, not the rule; every row is labelled
  `SHAKEDOWN - NOT COUNTED`, lives in its own file, and is excluded from every statistic and every n.
- **Counting starts with the first session that opens after Anupam's "ok"**, recorded here as an `APPROVED <timestamp>` line;
  the runner refuses to mark any row COUNTED without it.
- Book writes go through `src/atomicio.py` (BOOK-001). The runner is a plain script on launchd at about 13:40 PT on weekdays
  (zero Claude credits); it files one forecast per run as its own unit `ie-pro-paper` (never pooled with the lab's other forecasts).
- Anything comparing the paper track with his live trades lives only in `~/Desktop/Trading/PAPER_VS_LIVE.md`; no live figure is
  ever written into this repo.

## 11. Open items for Anupam to correct before "ok"
Capital $5,000; n = 60 sessions; the PASS conditions in §9; the 10-minute fill window and the 90% / 75% coverage thresholds
(my proposals, set before any outcome exists); whether v2 is worth registering at all (it will not reach a readable n).

APPROVED: _(not yet)_

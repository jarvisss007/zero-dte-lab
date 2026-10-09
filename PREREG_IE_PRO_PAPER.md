# PREREG — the simulated paper trader on the IE Pro trigger (PTR-001)

**Status: REGISTERED 2026-10-09 (Anupam's "ok" on this document, after the prereg-reviewer pass; see the APPROVED stamp at the
end). Frozen: any change is a new registered variant (REG-PP-001).** Paper only: nothing here places an order, talks to a broker or holds a key. It is a forward
*description* of a rule on recorded data, not a claimed edge. The lab's verdicts stand: same-day SPY options showed **no edge
after costs** (README); the only earlier score of IE Pro labels (7 hand-keyed, Aug 2026) was 1 win in 6.
**Prior: no edge. The expected readout is FAIL.** It is **not THE ACCOUNT** and never counts toward the Rule 7 gate; its
per-trade risk (a 30% stop on up to $1,000 = $300 = 6% of C, more on a gap) is three times Rule 2's 2%, so it must never be read
as a sizing guide.

## 1. What is registered
**One variant: PTR-001 — IE Pro.** Trigger `src/ie_pro_trigger.py`, ported from `pine/ie_pro_indicator.pine` (the indicator that
prints CONFIRMED LONG/SHORT [A+/A/B]); chart settings in `pine/IE_PRO_CHART_SETTINGS_2026-10-09.md`.
**Declined for now: the IE Pro ONE sweep trigger.** It is the r17 sweep concept the README convicted (t = -2.9 on true-OHLC bars;
Firm Brain §7: a convicted idea does not return in new clothes), and at 0.27 tradable signals per session it makes about 16 trades
in 60 sessions, which can never be readable. Its port stays in the repo as a tool; registering it later is a new variant by Anupam's ruling.
**What this does not deliver:** the 4-5 trades a day asked for. The rule fires **2.89 tradable signals per session** (§3).
Because signals sit at least 100 minutes apart and the clock is 60 minutes, POSITION_OPEN and SESSION_CAP can never fire for
this variant (Firm Brain §23: a clause that cannot bind is stated, not hidden).
**It does not reproduce the chart's labels bar for bar.** The free-running port matches 3 of the 30 transcribed chart labels
(entry/stop/target numbers exact where it matches); with the 20-bar spacing anchored on the chart's own labels it fires on
10 of 14 regular-hours labels. 16 of the 30 labels are premarket or post-market, where free data cannot fire (§2).

## 2. Data (frozen)
- **Bars:** Yahoo chart data, SPY 5-minute with pre/post market (`src/paper_bars.py`), archived per session at first full
  capture after the close and never rewritten (settled prices only, Firm Brain §1/§8). Seeded with the last 60 days
  (`data/paper/bars_seed_2026-10-09.csv`, stamped SEED: warm-up, never scored).
- **Frozen drops** (`paper_bars.clean`): bars stamped at or after the session close (16:00 ET; the early-close time from
  `src/sessions.py` otherwise: 2026-11-27 and 12-24 are inside the window) — Yahoo's post-close bars carry bad prints (10-05: a
  769.452 low where the chart's was ~774); flat carry-forward bars (O=H=L=C = prior close, volume 0; §18); bars on non-sessions.
- **Disclosed limits:** Yahoo premarket volume is 0, so the volume leg and VWAP are false before the open and **no premarket
  signal can fire**; its volume is another feed from the chart's (0.48-0.89 of consolidated); some premarket bars are missing
  (10-08 06:15-06:25 PT), and pivots/spacing count bars. The trigger is feed-sensitive: on the sweep trigger, regular-hours-only
  bars changed 10 of 18 signals.
- **Option book source:** the CBOE-only recorded files `data/chains/SPY_<date>.csv` unioned with `data/chains_ci/`, deduped on
  `quote_ts` as `src/merge_chains.py` does. The `*.yfinance.csv` fallback files never feed this book (ZDTE-011).
  `quote_ts` is naive exchange time (ET). A book timestamp is **valid** only if it was fetched 10 to 25 minutes after its
  `quote_ts` (a forward-stamped or stale quote is dropped; the lag is normally ~15 minutes).

## 3. Signal (frozen; no tuning)
IE Pro, `htf_mode = developing`, pivot tie rule `left_strict` (the helpers live in `ie_pro_one_trigger.py`), Volume MA 20, EMA 9/21,
RSI 14 55/45, min bars 20. The trigger runs on the whole archive so spacing counts every earlier signal, including SEED sessions
and DATA-GAP sessions (§8), which are never repaired afterwards.
**Freeze identity (SHA-256, recorded 2026-10-09; any change before approval is re-shown to Anupam, any change after is a new variant):**
`ie_pro_trigger.py` 1f0d40c39ac28d8b…7ecd; `ie_pro_one_trigger.py` 4d4f7532a5f8190e…cfef; `paper_bars.py` 0946e318a8653c90…2e7c;
`sessions.py` edb23f43966e8613…bad6; `pine/ie_pro_indicator.pine` e8afb597613ccb43…64fc; seed `bars_seed_2026-10-09.csv`
60b3cab507b38fe4…4c2c (full hashes: `results/PTR-001_FREEZE_HASHES.txt`). The runner **refuses to run on a mismatch**, stores
every signal **append-only**, and a recompute that disagrees with a stored signal **fails loud** (it never rewrites it; BENCH-002).
A signal is **tradable** only if its bar opened at or after 09:30 ET and its decision time (open + 5 min) is at least 5 minutes
before the close; others are logged and still count for spacing.
**Rate** (committed script `src/ie_pro_signal_rates.py`, output `results/IE_PRO_SIGNAL_RATES_2026-10-09.txt`, 55 sessions after a
5-session warm-up): **159 tradable signals = 2.89 per session**; sessions with 0/1/2/3/4+ signals: 0/1/15/28/11; maximum 4.
Reconciliation of the earlier "18" for the sweep trigger: 18 (as-is bars incl. the 15:55 bar) -> 17 (post-close dropped) -> 15
tradable (after warm-up, decision at least 5 minutes before the close).

## 4. Entry (ordered; the first rule that fails writes the skip, so two implementers get one book)
Signals are processed in time order. For each tradable signal:
1. **SESSION_CAP** — 5 entries already taken this session? skip. 2. **POSITION_OPEN** — the open trade's exit `quote_ts` is later
than this decision time (strictly)? skip. 3. **NO_BOOK_WINDOW** — no valid book timestamp with decision time <= `quote_ts` <=
decision time + 10 minutes (both ends inclusive), and `quote_ts` earlier than close - 5 minutes? skip. The **first** such timestamp
is used; a later, cheaper one is never substituted (Firm Brain §8, ZDTE-004). 4. **NO_TWO_SIDED_MARKET** — the contract below has
no row there, or bid <= 0 or ask <= 0 or bid > ask? skip. 5. **TOO_EXPENSIVE** — floor(1000 / (ask x 100)) = 0? skip.
6. **NO_LATER_BOOK** — no valid later snapshot of the same contract? skip.
- Contract: the SPY option expiring the same session; **call on a long signal, put on a short**; call strike = the lowest listed
  strike strictly above the snapshot's `spot`, put strike = the highest listed strike strictly below it.
- Fill at the **ask**. Every skip is recorded with its reason and the session (a silent zero is not allowed, §3).

## 5. Size
Paper capital C = **$5,000, fixed, never compounded**; $1,000 per trade; contracts = floor(1000 / (ask x 100)). **No premium
floor and quoted size is ignored** (asks run from $0.05; late in the day a trade can be ~200 contracts where fees dominate), so
each row stores `ask_size` and the readout counts trades with contracts above `ask_size`.

## 6. Exits (frozen)
At each valid later snapshot of the **same contract** in time order, against its **bid**: 1. bid >= 1.50 x entry ask -> **TARGET**,
filled at exactly 1.50 x entry ask; 2. bid <= 0.70 x entry ask -> **STOP**, filled at **that snapshot's bid** (a bid of 0 is valid
and fills at 0); 3. `quote_ts` >= entry `quote_ts` + 60 minutes (inclusive) -> **CLOCK**, filled at the bid; 4. none left that
session -> **BOOK_END**, filled at the last valid snapshot's bid. A row with a NaN, missing or crossed (bid > ask) quote is skipped,
not used. The target fill is **capped at the line while a stop fills at the (gapped) bid**, so the exit is asymmetric *against* the
rule; snapshots are about five minutes apart, so touches between them are invisible. The indicator's own SPY levels (SL = bar
low/high -/+ 0.5 ATR, TP1/TP2 = 1.5/3 ATR) are stored on each row and read descriptively only.

## 7. Fees
$0.36 per contract per side, both sides (Anupam's own Schwab rate, stated by him 2026-10-09). The readout also prints the same
trades at $0.65 per contract per side (the estate's registered rate, PACK-006) as a sensitivity, descriptively.

## 8. What is counted, and when
- **Counted session:** its 09:30 ET open is after the `APPROVED` timestamp (§10); the bar archive holds at least 90% of the expected
  regular-hours bars ((close - 09:30)/5); and valid book timestamps are at least 75% of the expected ((close - 09:35)/5). Otherwise
  **DATA-GAP: logged, not scored, not counted** (e.g. 2026-10-02: 22 snapshots, the morning missing). A counted session with no
  filled trade is a counted zero-P&L session.
- **n is counted in sessions** (`clustered_by: session date`), never trades. **n = 60 counted sessions AND at least 100 filled trades.**
  No PASS/FAIL and no headline number before both; until then the Sunday report prints n, trades and "not yet readable".
- Keyed to the settled session, not the run (Firm Brain §15): one row set per session, idempotent. The books write nothing on a
  run with no new session; a separate `heartbeat.csv` row says whether the run happened and why it wrote what it wrote, so a dead
  runner and a quiet one are distinguishable.

## 9. Readout at n = 60 (pre-declared; after approval it changes only by Anupam's written ruling)
In **percent** in every public place (per-trade net return on cost; session net as % of C): per-trade mean/median net %; win
rate **beside** the mean's sign and size; average loss / average win; worst loss; fees share of gross; each for the first and last
30 sessions (a sign that flips is visible, §20); the day-clustered 95% bootstrap interval of mean session net (10,000 resamples of
sessions). **Benchmark: the mirror twin** (the opposite option at the same decision time under identical rules; a signal whose twin
cannot fill is dropped from both arms and counted). The comparison is the **paired per-trade difference (trade minus twin),
session-clustered, shown separately for long and short signals** so a market drift that favours calls cannot pass as skill.
**PASS only if all hold:** the clustered 95% interval of mean session net excludes zero upward; the mean has the same sign in both
halves; the pooled paired difference (trade minus twin) has a session-clustered 95% interval that excludes zero upward, and its
point estimate is positive for long signals and for short signals separately. Otherwise **FAIL: no edge shown.**
A PASS is never a trade instruction: the mining tax (trials_total), an `edge-refute` panel and the no-live-trades rule come first.
**The only splits allowed are those above, plus an entry-premium split (ask under / over $0.20) printed descriptively.**
No post-hoc slice by grade, hour or side is a finding.
**KILL:** cumulative net P&L at or below -$1,500 (30% of C) retires the variant (it stops adding counted sessions); signals and
twins keep being recorded (a halt on acting must not halt measuring, §24). *(My proposal; Anupam may change it before "ok".)*

## 10. Freeze, shakedown, scheduling
- Frozen when registered. Any change — a parameter, the data filter, strike/fill/exit rule, the readout — is a **new registered
  variant**, never an edit and never a tuning on outcomes.
- **SHAKEDOWN** replays recorded sessions from 2026-09-30 to test the code, not the rule. **No option P&L has been computed
  from the recorded chains as of this draft**, and the shakedown keeps it that way: it runs entries and skips on recorded days with
  exit reason, exit price and P&L **redacted** (invariants such as exit later than entry are checked); the exit path is tested on
  synthetic fixtures. Every shakedown row is labelled `SHAKEDOWN - NOT COUNTED`, in its own file, excluded from every statistic.
- **APPROVED stamp:** written only after (a) Anupam's "ok" on this document and (b) the runner's launchd job is registered
  and proven under `env -i` (EVO-010 / §27: a variant is not registered until its writer appears in a scheduler). The first counted
  session is the first whose 09:30 ET open is after the stamp. The runner refuses to mark any row COUNTED without it.
- Runner: a plain script on launchd at about 13:40 PT on weekdays (zero Claude credits); book writes via `src/atomicio.py`
  (BOOK-001). It files **no forecast**: it claims no probability, and a constant-p forecast cannot be scored (§14); if the council
  requires one it is a separate registered unit.
- Anything comparing this track with his live trades lives only in `~/Desktop/Trading/PAPER_VS_LIVE.md`; no live figure is ever
  written into this repo.

## 11. Further disclosures
- Quotes are CBOE-delayed (~15 minutes behind the fetch): the book is a simulation from the feed's own stamps, filled at the first
  quote stamped at or after the decision, which a person at the screen could not have seen until ~15 minutes later.
- The 30/50/60 numbers come from the Exit Card (set 2026-09-30) and a 324-cell look at 45 recorded sessions (2026-07-17 to
  09-29; `results/EXIT_RULES_STUDY_2026-09-30.md`, DESCRIPTION ONLY): they are not out-of-sample for those sessions; the forward
  sessions are new. The ledger charges one trial (PTR-001) and this look is disclosed in its `deflation_context`.
- The sweep trigger's 0.27 per session is both directions on extended-hours bars; README Finding 5's "1 signal in 17 sessions" is the
  short-only config on regular-hours bars with the older port. Different bases, not a contradiction.

## 12. Open items for Anupam to correct before "ok"
Capital $5,000; n = 60 sessions and 100 trades; the PASS conditions (§9); the KILL line; the 10-minute fill window, the 25-minute lag
guard and the 90% / 75% coverage thresholds (my proposals, set before any outcome exists); dropping the sweep variant.

APPROVED: 2026-10-09 15:30 PT (18:30 ET) - Anupam's "ok" on this document, given 2026-10-09 in chat.
Approved text = git commit 6e96e6f, sha256 392835c0c6c57526e35a5604abe23eeabac5f871292cc9d92620c1630979cd76. Runner pinned: src/paper_runner.py sha256 4f1193584e68144488cf46903e7c0bb3e1bd030b1009f063062e909fa580d8d2. Machine copy: data/paper/APPROVED.json.
Only the two status sentences at the top were edited at the stamp. Counting starts with the first session whose 09:30 ET open is after this stamp.
RE-PIN 2026-10-09 15:31 PT (before any counted session): src/paper_runner.py sha256 d7330cef1297b3cd4a92566dc99bbae82b56076f38390a8fda0837b50eed3c1f. Reason: the runner now catches up every unprocessed settled session in order, and an older day whose bars can no longer be captured is written as a DATA_GAP row; the registered rule text above is unchanged.
ADDENDUM 2026-10-09 16:14 PT (before any counted session): the section 9 readout is implemented in src/paper_report.py (sha256 965e296f645b8f097d44a176908df33f9f538547b5151cdf4762baaf9e7f540a), tested on invented books, run Sundays 12:30 PT by launchd com.anupam.ie-pro-paper-weekly. The registered rule is unchanged.

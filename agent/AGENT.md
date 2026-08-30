# Zero-DTE Lab — Session Agent Instructions

You are the 0DTE session agent. Your job is observation, scoring, and
self-calibration — NOT trade recommendations. Anupam's standing rule applies:
no claim of edge without validation. This lab has already convicted r17 three
times and shown the timing U-shape is priced in until proven otherwise; the
ledger exists to prove or disprove whether anything readable in the morning
chain predicts the session. It feeds the 60+-session verdict — it does not
pre-empt it.

## The falsifiable unit

One per-session prediction made from the morning chain snapshot, scored
same-day at the close. Two allowed metrics, both deterministic:

- `implied_move`: call `inside` or `outside` — will SPY's close-to-close move
  land inside the ATM-straddle implied move from the morning snapshot?
- `max_pain`: call `holds` or `breaks` — will SPY close within ±0.25% of the
  morning max-pain / peak-OI strike?

## Run order (do all steps, in order)

> **AMENDED 2026-08-29 (ZDTE-004, ruled by Anupam). THE CALL IS MADE BEFORE ANYTHING
> READS A LIVE PRICE.** Scoring reaches a price endpoint that returns the live intraday
> bar, and it used to run first: on 2026-08-26 it handed over 770.46 against the 09:45
> snapshot spot of 768.47 — +0.259%, about 63% of the day's ±0.41% implied band already
> consumed — before the call step ran at all. The lab refused to call that day on exactly
> that ground: "logging inside now would record where price already is."
>
> The council's proposed chain-side fix (first-snapshot-only loader plus a `read_path`
> column) would have hidden the later CHAIN rows, left the PRICE leak fully intact, and
> stamped the row `read_path: snapshot-only` — turning an admitted leak into a CERTIFIED
> one. The lab argued against its own convenience and was right.
>
> The steps below are PHYSICALLY reordered, not merely renumbered. Renumbering alone
> would leave an agent reading top-to-bottom still scoring first, which is the same
> defect wearing a new label.

1. **Check today's chain data**: look for
   `data/chains/SPY_YYYY-MM-DD.csv` (today). The recorder
   (`src/chain_recorder.py`) may not be scheduled and launchd doesn't wake a
   sleeping Mac — if there is no snapshot for today, say so in the brief,
   make ZERO calls, and skip to step 4 (scoring). Never predict from stale chains.

2. **Read the shared lessons**: re-read `agent/lessons.md` in full before
   making today's call. It is the SHARED brain — any coach/grader writes
   there too. Do not repeat a pattern already flagged as underperforming
   without noting the conflict.

3. **Make today's calls (max 2, zero is fine)**: run
   `/opt/anaconda3/bin/python /Users/anupampatil/zero-dte-lab/src/implied_density.py data/chains/SPY_YYYY-MM-DD.csv --time HH:MM`
   with `--time` set to the earliest post-open snapshot (ET) in today's chain
   file, to get the ATM-straddle implied move and the OI landscape. Append at most one `implied_move` row
   and one `max_pain` row to `agent/ledger.csv`
   (columns: date,metric,call,thesis,value_at_call,check_date,value_at_check,outcome —
   `check_date` = today, `value_at_call` = the implied move in % or the pin
   strike, thesis under 15 words STARTING with `[0dte]`, last two fields
   empty). Do not manufacture conviction: if the snapshot is stale-quoted or
   pre-open-only, log nothing.

4. **Score due calls**: open `agent/ledger.csv`. For every row where
   `check_date <= today` and `outcome` is empty: get SPY's official daily
   open/close for `check_date` from Yahoo's free chart endpoint
   (`https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=1mo&interval=1d`).
   Fill `value_at_check` with the realized quantity (realized close-to-close
   move in % for `implied_move`; closing price for `max_pain`) and set
   `outcome` to `right` or `wrong` strictly by the rule in the row's call:
   - `inside` right iff |realized move| <= implied move in `value_at_call`;
     `outside` right iff strictly greater.
   - `holds` right iff close within ±0.25% of the strike in `value_at_call`;
     `breaks` right iff outside.
   No excuses, no "almost", no "the pin held until 12:55". A halted or
   holiday session voids the row: set outcome to `void` (the only exception,
   and only for no-trading days). Never edit or delete old rows otherwise.

5. **Update lessons**: if you scored anything, append dated, blunt takeaways
   to `agent/lessons.md` — hit rate per metric, any visible bias (always
   calling `inside`, over-trusting pins on trend days). Sign entries `[0dte]`.

6. **Write the brief**: create `agent/briefs/YYYY-MM-DD.md` (short):
   - **Chain state** (2 lines): snapshots recorded today, spot, implied std,
     straddle move, skew — from implied_density output.
   - **Today's calls** (or "no call" and why).
   - **Session count**: recorded sessions so far vs the 60-session gate for
     the straddle-underpricing verdict. This number is the project's real
     progress bar; the calls are side calibration.
   - **Scorecard line**: hit rate per metric and pending count.

## Hard rules
- Never present a call as a trade, and never suggest buying or selling 0DTE
  options off this. The README verdict stands: elevated realized movement is
  NOT an edge until shown to exceed what the options market charges — that
  test needs 60+ recorded sessions, and this agent doesn't shortcut it.
- If a metric's hit rate after 20+ scored calls is statistically
  indistinguishable from its base rate (note: `inside` is expected to win
  ~55-70% of the time by construction — the straddle usually overprices; the
  bar is beating THAT base rate, not 50%), say so and stop calling that metric.
- Keep the brief under ~25 lines.


---

## MANDATORY forecast — exactly one, every run, no exceptions

Append one row to `agent/forecasts.csv`. **This is not a trade call and not
advice.** Skipping a trade is free; skipping a forecast destroys the only
record that can ever prove whether your reads are worth anything. There is no
"no forecast today". If nothing is interesting, forecast the dull thing at 55%.

Why this is mandatory when trade calls are not: a hit-rate test needs tens of
thousands of observations to detect a real edge. A *probabilistic* forecast
carries information on every observation, so calibration becomes measurable in
hundreds. Abstention is correct risk management and fatal data policy — the
distinction is the whole point.

Format: `date,instrument,horizon_days,question,p,check_date,outcome,notes`

- `instrument` — SPY.
- `question` — a **binary that resolves mechanically** from this lab's own
  refreshed data files, with zero judgement at check time. Good: "closes above
  today's close on <check_date>". Bad: "looks constructive".
- `p` — honest probability the question resolves YES, in (0,1). Never exactly
  0 or 1. Genuinely no view? Write 0.5; that is real information about your
  uncertainty and it scores fine.
- Prefer questions you are actually unsure about. Forecasting 0.99 on a
  near-certainty scores well and teaches nothing.

**Scoring:** on each run, resolve every row whose `check_date <= today` by
setting `outcome` to 1 (YES) or 0 (NO), mechanically. Then run:

```
/opt/anaconda3/bin/python ~/bin/score_forecasts.py --lab zero-dte-lab
```

You are graded on **calibration, not on being right.** Saying 60% and being
wrong is fine. Saying 90% and being wrong repeatedly is not.

## ANUPAM DECISION 2026-08-08 — implied_move specification (unfreezes the metric)
The council escalated the mis-specification (straddle quoted off morning spot was being
scored against close-to-close, charging it for an overnight gap it never priced). Decision,
delegated by Anupam ("make these work") and applied: **score the straddle against the move
it actually prices — morning-spot to close, intraday only.** Rationale: the instrument's
quote window defines its claim; subtracting gaps from close-to-close reconstructs the same
number with more steps and more ways to be wrong. The single historical implied_move row
(07-17, scored wrong under the old spec) is marked "rescored under new spec at next sweep —
if the verdict flips, both verdicts stay in lessons.md with the spec change noted."
Metric is UNFROZEN as of this note; resume logging.

## RATIFIED — Review #2, 2026-08-09
The 2026-08-08 delegated decision above (intraday spec: morning-spot to close) was put to
Anupam explicitly at Review #2 and CONFIRMED as his ruling. The metric is unfrozen under
that definition; this note closes ZDTE-001 in the desk register.

## Call timestamp — the 09:47 snapshot (Anupam, 2026-08-12, ZDTE-002)

**Stamp every call to the 09:47 ET snapshot, not to the sweep that fires at 11:36.**
The chain recorder captures from 09:29 every 5 minutes, so the data already exists.

Why this is a correctness rule and not a convenience. The sweep runs ~2h into a
6.2h session, so both metrics are pre-loaded by the time the lab sees them: on
2026-08-11 SPY had already consumed 76% of the +/-0.34% implied band and sat
inside the max-pain band, and the lab correctly refused to log either — "only
because I can see two hours I shouldn't."

The cost was never the missing row. It is that the ledger then fills up ONLY on
mornings that happen to be quiet, so the sample is conditioned on a small morning
move and `inside` is biased upward by selection rather than skill. At 4/4 that is
invisible. At the lab's own 20-scored bar it would be a wrong answer wearing a
clean number.

Rows logged under the old fire-time regime are a SEPARATE pre-fix stratum and are
never blended with post-fix rows. Report them with their own n.

## AMENDED 2026-08-13 (ZDTE-003) — stamp the FIRST snapshot, not a clock time

ZDTE-002 was ruled 2026-08-12 as "stamp the call to the 09:47 ET snapshot", on a
premise I supplied and never checked: *"the chain recorder captures from 09:29
every 5 min, so the data already exists."* **It does not.** The lab checked and
was right. First snapshots on record: 10:05 (08-06), 09:45 (08-07), 09:45 (08-10),
09:47 (08-11 — coincidence), 09:45 (08-12), **10:27 (08-13)**.

Two causes stack, and neither is fixable by scheduling:

1. **CBOE's free delayed feed does not publish a fresh book until ~09:45 ET.**
   Before that the recorder correctly skips on stale quotes — 08-12's log shows
   skips at 09:30 and 09:35 against a `2026-08-11T16:00:00` stamp.
2. **The Mac sleeps.** On 08-13 there are no skip lines at all before 10:27, so
   the recorder was not invoked. The cloud leg does not rescue this either: its
   first run landed 10:06 (08-12) and 10:13 (08-13), because GitHub runs the
   `*/10` cron about once every 50 minutes.

So no fixed clock time is reliably available, and a rule naming one silently
fails on the days it matters most.

**THE RULE, amended:** stamp the call to the **FIRST SNAPSHOT OF THE SESSION,
whatever time it lands**, and record that time on the row as
`snapshot_et` plus `minutes_into_session`.

This keeps everything ZDTE-002 was for. The purpose was never the clock — it was
to stop the ledger filling only on quiet mornings, because a call made two hours
in is conditioned on a small morning move and biases `inside` upward by selection.
Taking the earliest available bar every session removes that selection whether it
arrives at 09:45 or 10:27.

It also does something the original could not: it **discloses the leak instead of
pretending there is none**. A row stamped 57 minutes into the session is more
contaminated than one stamped 15 minutes in, and now says so in a field the
analysis can stratify on. Rows must never be blended across widely different
`minutes_into_session` without reporting the split.

## CALIBRATION (2026-08-20) — read your own scorecard before you file
Before filing any probabilistic forecast, read `~/command-center/council/calibration_table.json`
and find this lab's entry. It is written by `~/bin/score_forecasts.py` (Brier skill + Murphy
decomposition: reliability, resolution) from your own resolved forecasts.
- If your probability falls in a bin marked `actionable: true` (n≥30 AND |gap|>0.10), say so in
  the forecast note ("my 0.6–0.7 bin has run 0.55") and move the filed probability **halfway**
  toward what actually happened in that bin. That is the only adjustment permitted.
- Below n=30 in a bin, file as usual. Do not tune on noise — that is curve-fitting with extra steps.
- Spread forecasts across days. Ten forecasts stacked on one morning are one observation.
- You are graded on calibration (saying 70% and being right 70% of the time), never on being
  right today. A well-calibrated 0.55 beats a lucky 0.90.

## STANDING CONDITION — resolution latency (SCHED-001, ruled (c) 2026-08-20)
This lab's daily horizon unit closes AFTER this lab fires (a UTC day read at ~15:30 UTC; an
ET session read at 11:29 ET), so no daily row can resolve on its own check_date. The desk
accepts one day of resolution latency as the honest cost and does NOT move the fire time or
the pre-registered horizon unit. Therefore: every daily row states on its face, in `notes`,
`resolves check_date+1 (standing, SCHED-001)`. This is a permanent condition, not a
deferral — never file it as a deferral, and the council grades it PASS by design. Rows
already written are not moved.

## OFF-MACHINE COPY (BAK-001, 2026-08-21) — push the chains every run
`data/chains/` is tracked in git since 2026-08-21: GitHub is the recorder's off-machine copy,
because the laptop's rsync backup is blocked by macOS permissions on days the Claude app is
closed. At the END of every run: `git add data/chains data/session_count.json && git commit -m
"chains: <today>" && git push origin HEAD`. If the push fails, say so in the brief — a failed
push is a day with no off-machine copy, and that is a fact to report, not to absorb.

# Lessons — the 0DTE session agent's self-calibration log

2026-07-15: File created. The agent appends dated, blunt takeaways here after
scoring its own per-session calls in `ledger.csv`, and must re-read this file
in full before every brief. This is the SHARED brain — every agent or coach
that writes here signs its entries with a tag (`[0dte]`, `[coach]`, ...).
Empty sections mean no scored history yet — earn the opinions.

## Standing priors (set at file creation, 2026-07-15)
- [0dte] Default assumption: my session calls are noise until the ledger
  proves otherwise. This lab convicted r17 three times; my commentary gets
  the same bar.
- [0dte] `inside` wins most days by construction (straddles usually
  overprice). Beating 50% with `inside` calls proves nothing; the bar is
  beating the inside base rate.
- [0dte] The 60+-session straddle-underpricing test is the project's real
  verdict. Nothing in this file or the ledger substitutes for it.

## Scored-call takeaways
- 2026-07-17 (scored late, 2026-07-25 catch-up): [0dte] implied_move `inside`
  WRONG — realized -0.99% vs ±0.63% implied; the "quiet low-VIX Friday"
  base-rate bet lost to a real down move. max_pain `breaks` RIGHT — close
  743.29 vs pin 747 (0.50% away). Running: 1/2 overall; inside 0/1, which is
  worse than its own favorable base rate — one call means nothing, but note
  the losing call was the one leaning on the base rate, not reading the tape.
- 2026-07-25: [0dte] Process: the scoring sweep was dead 2026-07-17→07-25;
  calls sat unscored for 8 days. Late scoring is still honest scoring, but the
  feedback loop only works if it runs — verify the sweep task is alive.

## Process lessons
(none yet)

## Process lessons (appended 2026-08-03)
- [0dte] TODAY'S SESSION IS LOST. The recorder ran its full schedule on
  2026-08-03 and every single fetch returned
  `URLError(gaierror(8, 'nodename nor servname provided'))` — a DNS failure,
  i.e. no network, not a bad endpoint. 84 consecutive errors, no
  `SPY_2026-08-03.csv` written. Zero calls made, correctly: the rule is never
  predict from a chain you do not have.
- [0dte] This is the second occurrence, not the first: 2026-07-23 hit the same
  DNS error mid-session and left a truncated 147KB file (vs ~1.6MB for a full
  day). So the failure mode is "Mac loses network / sleeps while launchd keeps
  firing", and it costs whole sessions silently — the log is the only place it
  shows up. Worth a guard that alerts when a session ends with 0 rows written.
- [0dte] Session count reality check: 12 chain files exist, but 07-08 (22KB),
  07-21 (194KB) and 07-23 (148KB) are partial captures against ~1.6MB for a
  full session. That is ~9 usable sessions, not 12, against the 60-session
  gate. At the current loss rate the verdict is months away, and pretending
  otherwise would be the same self-flattery this lab exists to prevent.

2026-08-04 [0dte] — Nothing scored (both ledger rows closed 07-17; the open
forecast checks 08-05). Abstention logged against a named bar, per the council
rule. Three things worth carrying forward, none of them market reads:

(1) **The session count has been overstated.** 13 chain files exist but only
**9** carry usable intraday coverage (>=10 snapshots). 07-08, 07-21, 07-23 and
08-04 hold 1, 9, 7 and 1 snapshots. The gate is 60 sessions of *recorded
session*, not 60 files, so the real progress bar reads **9/60**, not 13/60.
Counting files instead of coverage flatters this project by a third.

(2) **Recorder down two days running.** 08-03 recorded nothing; 08-04 got 4
fetches and 69 DNS failures (`gaierror(8)` on cdn.cboe.com, 69 consecutive to
the close). `cdn.cboe.com` resolves normally now, so this is the Mac losing
network mid-session, not a bug in chain_recorder.py. Per the council's "flag
stale collectors instead of scoring around them" — flagged, not worked around.
At the current attrition the 60-session gate is not months away, it is
indefinite.

(3) **Timing makes this lab unrunnable from the evening sweep.** Every metric
here has check_date = today and is scored at today's close. This run fired
23:43 ET, after the close. Logging a call at that hour is not a prediction, it
is transcription of a known outcome. So on any post-close run the correct
output is zero calls regardless of data quality — and that should be treated
as a scheduling fact about this lab, not as a judgement call to re-make each
time. If 0DTE calls are wanted, the sweep has to reach this lab before 09:45 ET.

Recorded unscored, because the 60-session study is retrospective measurement
rather than forecasting: the 09:32 straddle implied +/-0.39% and realized
close-to-close was +1.80% (757.67 -> 771.33), a 4.6x underprice. Single thin
session, near-zero evidentiary weight, and deliberately kept out of ledger.csv.

2026-08-05 [0dte] — Nothing scored (ledger has 0 pending). Abstention logged against a
named bar, and the bar is worth stating precisely because it is not a market judgement.

THE SCHEDULE MAKES THIS LAB'S FALSIFIABLE UNIT IMPOSSIBLE TO PRODUCE HONESTLY.
The parent sweep fires at 8:20 PDT = 11:20 ET, about 1.8 hours after the US open. The unit
at the top of AGENT.md is a prediction made from the MORNING chain and scored at the same
day's close. Today I had a clean 09:47 snapshot (spot 776.05, straddle implied +/-0.63%,
skew -0.34) and could also see the tape through 11:12 ET (773.43 against an 08-04 close of
771.33, roughly +0.27% realized). Calling `inside` off that is not a prediction, it is
reading 30% of the answer first. Declined. This will recur on EVERY run at this schedule,
so it needs a decision from Anupam or `[coach]`, not a judgement call each morning: either
a separate ~06:35 PDT trigger for the 0DTE calls, or the ledger stops accepting same-day
calls and the lab's unit is redefined. Recording it as a blocker rather than quietly
skipping, which is how 07-31's and 08-04's schedule faults went two runs before anyone
named them.

Two other things worth carrying:
(1) THE RECORDER IS FINE — the last three runs' failures were DNS, not design. Today: 21
snapshots on a clean 5-minute cadence from 09:32 ET, still writing. 08-03 got zero
snapshots and 08-04 got exactly one, both DNS. Distinguishing infrastructure failure from
schedule failure matters, because they have different fixes and today separates them:
same code, working data, still no honest call available.
(2) THE SESSION GATE IS FURTHER AWAY THAN THE FILE COUNT SUGGESTS. 14 chain files exist,
but only 9 have full intraday coverage (>=70 snapshots); 2 are partial (07-21: 9, 07-23: 7)
and 2 are single-snapshot stubs (07-08, 08-04). So the honest count toward the 60-session
straddle-underpricing verdict is ~10, not 14. Attrition is 4 of the last 14 calendar
attempts lost to DNS or a sleeping Mac. Anyone reading progress off `ls | wc -l` will
overstate it by 40%. Count snapshots, not files.

A forecast row was DUE today (08-03 row, checks 08-05) and was deliberately left pending:
the 08-05 close does not exist yet at 11:28 ET. Resolving it off an intraday mark would be
exactly the fabrication the hard rules forbid. It resolves on the next run.

2026-08-06 [0dte] — Ledger: nothing due, nothing scored. Both rows in agent/ledger.csv
closed on 2026-07-17 and there have been no open rows since. That is not a market
observation, it is a consequence of the schedule block below, and it has now cost this
lab three weeks of ledger data.

BLOCKED BY SCHEDULE — day 2 of stating it in the sweep output, per the council directive.
This run fires 11:28 ET. Today's earliest usable snapshot is 10:05 ET and the falsifiable
unit is scored at TODAY'S CLOSE. Making that call now means ~2 hours of the session is
already visible to me while I "predict" it. The call would score well and mean nothing.
Zero calls logged. The fix is a cron change on Anupam's desk — the recorder needs to run
the morning snapshot and the agent needs to make the call from it BEFORE the session has
meaningfully moved, or the metric has to change to a next-session horizon. Until one of
those happens this lab produces forecasts and no ledger units.

Forecast resolved: the 08-03 row ("SPY closes above 757.67 on 2026-08-05", p=0.52)
resolved YES — SPY closed 769.79. Brier 0.2304 at n=1, skill undefined. Worth nothing yet
except that the pipeline runs.

Two infrastructure notes:
(1) RECORDER FULLY HEALTHY, second clean day. 12 snapshots today at a clean 5-minute
cadence, 0 failures, live quotes tracking spot 769.78 -> 770.47. The DNS failures that ran
through 08-03 and 08-04 (and left those two forecasts with no chain information at all)
are gone. The three-day infrastructure escalation stays closed.
(2) BUT THE RECORDER STARTS LATE. First snapshot today was 10:05:28 ET — 35 minutes after
the 09:30 open. The opening range is exactly the part of the session a morning-chain
prediction should be reading, and it is missing. Whether that is the launchd trigger time
or the Mac waking late, it is a second, independent schedule fault from the one above, and
it will still be there even if the agent's own trigger gets moved earlier. Worth checking
the plist before assuming a single fix covers both.

Session count: 15 recorded of the 60 the straddle-underpricing verdict needs. That is the
real progress bar and it moved by one today.

Today's chain, recorded for the archive and NOT used for a call: spot 771.38 at 10:05,
implied close std 5.27 (0.68%), skew -0.89, ATM 771 straddle mid 3.33 => implied move
+/-0.43% by the close.

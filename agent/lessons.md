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

2026-08-07 [0dte] — Nothing scored. Both ledger rows closed 07-17. The 08-04
forecast has check_date 2026-08-07 = TODAY and CANNOT be resolved on this run:
the run fires 11:35 ET and the question asks for a CLOSE. Left pending
deliberately; it resolves on the next run. Recording that because a future run
must not read a skipped resolution as a lost one — this is the catch-up rule
working, not failing.

No calls. Blocked by schedule, NOT flat — and today the block is sharper than
usual, so it is worth writing down exactly why.

(1) THE LOOKAHEAD IS NOW MEASURABLE, not theoretical. Morning snapshot (09:50 ET,
the earliest usable one) gave an ATM 771 straddle mid of 3.46 => implied move
+/-0.45% by the close. SPY's prior close was 768.56; at 11:31 ET spot was 772.98,
a realized close-to-close move of +0.58%. The move is ALREADY outside the implied
band. Logging `outside` right now would score right with near-certainty and would
be worth precisely nothing as calibration, because it is an observation wearing a
prediction's clothes. The council's KEEP line — never fabricate a call to fill the
coverage line — is exactly this case, and this is the first run where I can put a
number on what the fabrication would have been worth.

(2) A REAL METHODOLOGY DEFECT IN THE `implied_move` METRIC, found while checking
the above. The straddle implies +/-0.45% FROM THE MORNING SPOT (771.49). The
scoring rule in AGENT.md compares it against the realized CLOSE-TO-CLOSE move,
measured from the prior close (768.56). Those two are not the same quantity: the
overnight gap of +0.38% was already banked before the session started, and it is
charged in full against `inside` while the straddle never priced it. On a gappy
morning `inside` is being asked to cover a distance the option it is quoted from
never sold. The single closed `implied_move` row (07-17: implied +/-0.63%,
realized -0.99%, scored wrong) is plausibly the same defect and not a bad read.
n=1 so that is a hypothesis, not a finding. Either the call must be scored
open-to-close, or `value_at_call` must be the implied move re-based to the prior
close. This is a [coach]/Anupam decision — I am not changing a scoring rule
mid-flight, and I am not logging more rows into a metric I now believe is
mis-specified until it is settled.

(3) RECORDER IS ALIVE and the data is good: 22 snapshots by 11:31 ET, ~5-minute
cadence, real greeks. One caveat for whoever writes the density code — the FIRST
snapshot of the day (09:45:55) had iv == 0 on all 146 rows, completely unusable,
while 09:50:56 was clean. "Earliest post-open snapshot" must mean earliest USABLE
snapshot; taking the literal first would have produced a straddle price of zero.

2026-08-10 [0dte] — Scored today: the 07-17 rescore (verdict FLIPPED) and the
overdue 08-04 forecast. Two new calls logged, the first since the metric was
frozen. Recorder alive, 21 snapshots 09:45-11:26 ET, so this lab is NOT blocked
today for the first time in weeks.
Four findings:
(1) THE MIS-SPECIFICATION WAS REAL, AND IT COST A VERDICT. The 07-17 implied_move
row is rescored under the ratified intraday spec: morning spot 741.17 (09:49 ET
snapshot) to close 743.29 = +0.29% against an implied +/-0.63% -> `inside` RIGHT.
Under the old close-to-close spec the same row read -0.99% and scored WRONG. Both
verdicts stay on this record, as the ZDTE-001 note required. The 08-07 entry filed
this as "plausibly the same defect and not a bad read, n=1 so a hypothesis". It was
the defect. The read was fine and the ruler was broken — and note which one this
lab blamed first. A metric that punishes a call for an overnight gap the instrument
never sold does not produce a hit rate, it produces noise with a sign.
(2) NEW STRUCTURAL DEFECT: EVERY CALL THIS AGENT MAKES NOW CARRIES 1.7 HOURS OF
LOOKAHEAD. The 08:20 PDT trigger puts the run at 11:28 ET, ~1.7h into a 6.2h
session, while the call is priced off the 09:45 snapshot. Today SPY printed 773.78
at run time — +0.10% off morning spot, inside the +/-0.37% band and 0.62% above the
769 pin. Neither call was decided, so unlike 08-07 (outcome already locked, call
correctly refused) logging is defensible. But this is now a CONSTANT bias, not an
incident: the metric will look better than a clean 09:45 forecast would. Disclosed
in the brief and in this file so the eventual hit rate is read with it. The fix is
a call timestamped to the snapshot, not another change to the metric — a
[coach]/Anupam decision, and I am not changing a rule mid-flight twice.
(3) THE iv==0 DEFECT IS INTERMITTENT, NOT FIRST-SNAPSHOT-ONLY. The 08-07 entry
recorded the first snapshot as unusable (all 146 rows iv==0) and inferred
"earliest post-open" must mean "earliest USABLE". Today the counts are 09:45 -> 23
of 144 zero, 09:50 -> 10 of 144, 09:55 -> 27 of 146. So it is scattered across the
morning at 7-18%, not a clean first-snapshot artifact, and 09:45 was usable today.
Both timestamps agreed anyway (+/-0.37% vs +/-0.35%), which is the useful part: the
straddle read is not sensitive to which early snapshot you take.
(4) MAX PAIN IS NOT PEAK OI, and reading it as such would have produced a garbage
call. Raw peak OI today is the 740 strike (19,763), 4.3% below spot — a leftover
far-OTM put wall, and calling `breaks` against it would have been a certainty
dressed as a prediction. Computed max pain (the strike minimising total payout) is
769.0, 0.52% below spot, which is an actual question. AGENT.md says "max-pain /
peak-OI strike" as if they were interchangeable. On this chain they are 29 points
apart. Compute the pain, never grab the peak.

Session count: 16 recorded of 60.

2026-08-11 [0dte] — Scored 2 overdue rows, both from 08-10, both `right`. Ledger
now 4/4. NO CALLS TODAY, and the reason is the point of this entry.
(1) BOTH 08-10 ROWS RESOLVED, AND ONE OF THEM RESOLVED ON A KNIFE EDGE THAT THE
NEW SPEC HANDLED CORRECTLY. implied_move `inside`: morning spot 773.01 -> close
773.03, a realised intraday move of **+0.0026%** against a +/-0.37% band. Under the
old close-to-close spec the same session would have been scored on 773.26 -> 773.03
= -0.030%, still inside, so the verdict does not flip — but it is worth recording
that the first row under the ratified spec landed almost exactly on the morning
spot, which is the cleanest possible demonstration that the two specs measure
different quantities. max_pain `breaks` at 769: close 773.03 sits well outside the
767.08-770.92 band, right. 4/4 is n=4 and means nothing; the AGENT.md bar is 20+,
and `inside` is expected to win 55-70% by construction anyway.
(2) NO CALL TODAY — THE LOOKAHEAD BECAME DECISIVE RATHER THAN MARGINAL, SO I
REFUSED BOTH. The 08-10 entry recorded the 11:28 ET lookahead as a CONSTANT bias
that makes the metric look better than a clean 09:47 forecast. Today it stops being
a tilt and becomes the whole call. Morning spot 773.96, straddle prices +/-0.34%,
and SPY is trading 771.96 at run time — **-0.258%, i.e. 76% of the band already
consumed with roughly 4.4 of 6.2 session hours left**. A clean 09:47 forecast would
say `inside` off the 55-70% base rate; from where I am sitting `inside` is clearly
worse than that and `outside` is clearly better, and I know this only because I can
see two hours I was not supposed to see. Same story on max_pain: computed pain is
771.0 and SPY at 771.96 is already INSIDE the 769.07-772.93 band, so `holds` would
be pre-loaded. Logging either direction today contaminates the record; logging
`inside`/`holds` would be a knowingly worse call and logging `outside`/`breaks`
would be a knowingly better one. Neither is a forecast. This is the 08-07 precedent
extended: that day the outcome was already locked and the call was refused; today
the outcome is not locked but the information is decisive, and the same refusal
applies. The fix remains a call timestamped to the snapshot rather than to the
sweep — a [coach]/Anupam decision, not something I change mid-flight.
(3) MAX PAIN VS PEAK OI, CONFIRMED AGAIN AND WORSE THAN LAST TIME. Computed max
pain today is 771.0, 0.38% below spot. Raw peak OI is the **796 strike** (47,996
contracts), 2.8% ABOVE spot — a far-OTM call wall. The two are 25 points apart and
on opposite sides of spot, so AGENT.md's "max-pain / peak-OI strike" phrasing would
have produced not just a worse call but a call in the wrong direction. Second
consecutive session this has bitten; the phrasing in AGENT.md should be fixed to
say "computed max pain" outright.

Session count: 18 recorded of 60.

## 2026-08-12 [0dte]
Nothing scored today (all four ledger rows are already resolved, 4/4 right, and no
forecast checks before 08-13). Two calls logged — the first rows written under
ZDTE-002 — and three findings, one of which corrects ZDTE-002 itself.

(1) ZDTE-002'S FACTUAL PREMISE IS WRONG AND THE RULE SURVIVES ANYWAY. The note
says "the chain recorder captures from 09:29 every 5 minutes, so the data already
exists." It does not. Actual first snapshots: 08-06 10:05:28, 08-07 09:45:55,
08-10 09:45:55, 08-11 09:47:07, 08-12 09:45:35. The recorder starts 16-36 minutes
after the open, and the "09:47 snapshot" the rule is named after existed on 08-11
by coincidence. Today there is no 09:47 bar at all, and the 09:45:35 one carries 0
usable OTM quotes (smile unfit). Both rows are therefore stamped to **09:50:36**,
the earliest usable post-open snapshot, spot 773.06. The rule's INTENT — stamp to
the morning, not to the sweep — is intact and was followed. Its stated mechanism
is not, and a rule that names a timestamp the data does not reliably contain will
mis-fire the moment someone automates it. Rewrite it as "earliest usable post-open
snapshot" or fix the recorder's start time; do not leave it naming 09:47.

(2) THE CALLS WERE DERIVED MECHANICALLY BECAUSE THIS RUN COULD NOT AVOID HINDSIGHT.
The sweep fired 11:26 ET, and refreshing the other four labs put SPY's intraday
print (771.89, later 772.44) in front of me before the 0DTE step ran. That is
exactly the contamination ZDTE-002 was written to remove, and stamping a row to
09:50 does not remove it from the agent's head. So both calls were taken from
rules fixed before looking: implied_move = `inside` (AGENT.md's own stated base
rate), max_pain = `holds` iff the 09:50 spot is within +/-0.25% of max pain, else
`breaks` — 773.06 vs max pain 771.0 is 0.267% away, outside, so `breaks`. Neither
call used a post-09:50 number. Recording the exposure rather than claiming it
didn't exist.

(3) A CONSTANT `inside` CALL CARRIES ZERO INFORMATION, AND AT 2/2 IT LOOKS LIKE
SKILL. AGENT.md is explicit that `inside` wins ~55-70% by construction and that
the bar is beating THAT, not 50%. A rule that says "always inside" cannot beat its
own base rate — it IS the base rate, and every right answer it produces is the
straddle's overpricing being recorded, not a read. The metric needs a discriminator
(implied move vs trailing realized, or vs the same weekday's realized) that is
pre-registered before it is used, or its rows will keep accumulating a clean-looking
hit rate that means nothing. Flagging now at n=2, not at the 20-scored bar.

Session count: 7 sessions recorded (08-05, 06, 07, 10, 11, 12 plus earlier), still
far short of the 60+ the straddle-underpricing verdict needs. That gate is the
project; these calls are side calibration and do not shorten it.

## 2026-08-13 [0dte] The first max_pain miss, and an hour of chain that never got recorded

Scored the two overdue 08-12 rows. Results split.

(1) `max_pain` HAS ITS FIRST WRONG, AND IT IS THE INFORMATIVE KIND. Called `breaks`
off a 09:50 spot of 773.06 sitting 0.27% above the 771 pin — i.e. already outside the
±0.25% band at call time — and SPY closed 772.49, back INSIDE the band (769.07–772.93).
The call was not merely unlucky: the thesis was "already outside and drifting away",
which is momentum reasoning applied to a mean-reverting quantity. A pin band that spot
has just left is the setup where reversion is most likely, not least. `max_pain` is now
2/3. Do not read that as a hit rate; read it as the first evidence that "outside the
band now" is not a reason to call `breaks`.

(2) `implied_move` WENT 3/3, AND THAT IS EXPECTED, NOT SKILL. Realized morning-spot-to-
close was -0.07% against a ±0.41% straddle. The straddle usually overprices; `inside`
is expected to win 55–70% by construction, so the standing bar is beating THAT, not 50%.
Three rows cannot. Noting it before the number starts looking like a result.

(3) THE RECORDER LOST THE FIRST HOUR OF TODAY'S SESSION. First snapshot 2026-08-13
10:27:39 ET, against 09:45:35 on 08-12 and 09:47:07 on 08-11. 64 fetches, 0 failed —
so this is not a fetch error, the recorder simply started ~58 minutes late. That
matters more than a missing row: ZDTE-002 mandates that calls be stamped to the 09:47
snapshot precisely so the ledger is not conditioned on quiet mornings, and today there
was no 09:47 snapshot to stamp. Zero calls logged, for that reason and because a 20:22
PDT run can already see the outcome. If the late start repeats, the 60-session gate is
counting sessions that cannot produce a compliant call — check the launchd/wake timing
before assuming the count is healthy.

Session count: 20 of the 60+ gate. Forecast book: the 08-06 row resolved YES (SPY
777.88 > 769.79), making it 3/3 YES — the same degenerate all-YES streak the India lab
had, and today's row is the mirror fix (SPY closes BELOW 777.88 on 08-20, p=0.45).
Third lab today to break the "closes above" monoculture; the finding is India's, not
this lab's.

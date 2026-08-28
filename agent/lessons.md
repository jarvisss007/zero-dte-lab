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

## 2026-08-14 [0dte] Two named-bar abstentions, and the ZDTE-003 columns that were never actually built

Nothing was due; nothing was scored. Zero calls logged, for two reasons that are
both properties of the metric specs rather than of today's tape.

(1) THE 08-12 DISCRIMINATOR REQUIREMENT IS STILL UNMET, SO `implied_move` IS BARRED
BY THIS LAB'S OWN LESSON. That entry said a constant `inside` call carries zero
information — it IS the 55-70% base rate rather than a read of it — and that the
metric needs a discriminator pre-registered BEFORE it is used. Two sessions later no
discriminator exists. Logging a fourth `inside` today would have taken the record to
4/4 and made the problem harder to see, not easier. An unmet requirement that keeps
getting written down and never acted on eventually becomes decoration; naming the
deadline instead: either a discriminator is pre-registered before the next
`implied_move` row, or the metric stops accumulating rows.

(2) A 1.05% DISTANCE FROM THE PIN IS NOT A CALL, IT IS ARITHMETIC. Spot 778.09 vs
max pain 770, against a +/-0.25% band (768.08-771.92) and an implied std of 0.49% —
`holds` would need a 2.1-sigma downside close. This is the exact mirror of the 08-13
finding. That day taught that "already outside the band" is no reason to call
`breaks` at a MARGINAL 0.27% distance, because reversion is most likely right where
spot has just left. The same reasoning says a TRIVIAL 1.05% distance is not a read
either: it is a free win, and a metric sitting at 2/3 does not need free wins, it
needs informative ones. Both bars are session-independent, so declining on them
introduces no selection bias — which is the whole point of ZDTE-003 and had to be
checked before abstaining.

(3) ZDTE-003 WAS RATIFIED ON 08-13 AND WAS NEVER ACTUALLY IMPLEMENTED. The rule
mandates `snapshot_et` and `minutes_into_session` on every logged row. The ledger
header did not have those columns — because 08-13 logged no rows, so nobody hit the
code path, so the rule lived only in AGENT.md prose. A rule that only exists on the
first day someone happens to use it is not a rule. Columns added today, blank for the
five pre-rule rows, no recorded value touched. Added a THIRD column at the same time:
`minutes_visible_at_call`. `minutes_into_session` discloses how contaminated the
PRICE was; nothing disclosed how contaminated the CALLER was. Today those numbers
would have been 20 and 94 — the 09:50 snapshot versus a run that fired 11:24 ET — and
only the first was ever going to be recorded.

(4) THE RECORDER RECOVERED. First snapshot 09:50:19 ET against 08-13's 10:27:39, so
the late start was not the beginning of a trend. Session count 21 of the 60+ gate.
Today's band is +/-0.30%, the tightest this lab has recorded (prior 0.63, 0.37, 0.41).

Forecast: the due 08-05 row could NOT be resolved — the run fired mid-session and the
08-14 close does not exist yet. Resolves next run from the settled close; recorded here
so it does not read as a skipped catch-up. Today's new row is the first in this book to
ask the lab's own question (realized morning-spot-to-close vs the first-snapshot
straddle band, p=0.38) instead of a generic SPY-close question any lab could write.

## 2026-08-17 [0dte]

THE OVERDUE ROW RESOLVED, AND THE CATCH-UP WORKED EXACTLY AS 08-14 SAID IT WOULD.
The 08-05 forecast ("SPY closes above 771.33 on 2026-08-14", p=0.55) was left unresolved
on 08-14 because that run fired mid-session and the close did not exist yet. It is now
scored off the settled bar: SPY closed 776.34 on 08-14 → YES. The note written on 08-14
predicted this resolution path and it held. Four findings:

(1) THE SAME WALL IS HIT AGAIN TODAY AND WILL BE HIT EVERY SINGLE RUN. The 08-10 row
("SPY closes above 773.26 on 2026-08-17", p=0.56) is due TODAY and cannot be resolved:
this run fires 11:25 ET and today's close does not exist. It resolves tomorrow. This is
not an occasional inconvenience — a sweep that fires mid-session can NEVER resolve a
same-day check_date, so every row this lab writes with a same-day horizon is
structurally one day late. Insider-radar hit the identical wall this morning on seven
30-day rows. It is one problem with one owner, and it is not this lab's to fix.

(2) BRIER SKILL IS `nan` AND THAT IS INFORMATION, NOT A BUG. Four resolved, all four
YES, so the base rate is 1.000 and climatology Brier is exactly 0.0000 — dividing by it
is undefined. The lab has never once been wrong and therefore cannot yet be measured;
"+nan no skill vs base rate" means *unmeasurable*, not *no skill*. The 0.50-0.60 bucket
reading "+0.462 underconfident" across all four rows is the same artifact: a forecaster
who says 0.54 and is right four times running looks timid and is indistinguishable from
lucky at n=4. Nobody may quote either number.

(3) NO CALL AGAIN, AND THE DISCRIMINATOR DEADLINE NAMED ON 08-14 HAS NOW LAPSED.
`implied_move` stays barred: the 08-12 lesson requires a discriminator pre-registered
BEFORE another row, 08-14 named that as a deadline, and three sessions later none
exists. A fourth `inside` would take the record to 4/4 on a call carrying zero
information. `max_pain` is barred for a different and more basic reason — **today's
chain file has no open-interest column at all** (fields: fetched_at_et, quote_ts, spot,
expiry, type, strike, bid, ask, bid_size, ask_size, last_trade_price, iv), and
implied_density printed no OI landscape. There is no pin strike to call. That is a data
gap, not a judgement, and it should be checked: the metric is unusable while it persists.

(4) RECORDER HEALTHY, GATE AT 22. First snapshot 09:49:37 ET — 19.6 minutes into the
session, the second-earliest on record after 08-07/08-10's 09:45 — and 21 snapshots
through 11:29. Session 22 of the 60+ gate. Today's band is +/-0.28% off spot 775.77,
tighter than 08-14's +/-0.30% and now the tightest recorded; implied std 0.42%, skew
-1.04.

Today's forecast asks the lab's own question about TOMORROW, not today: with 21
snapshots and two hours of the move already on disk, any forecast about this session
would be contaminated in exactly the way ZDTE-003 was written to prevent. Same question
and same p=0.38 as the 08-14 row, on purpose — repeating an uncontaminated question at
an untilted base rate is how the 60-session sample gets built.

## 2026-08-18 [0dte]

THE OVERDUE ROW RESOLVED, BUT NOT FROM THE BAR IT WAS SUPPOSED TO. The 08-10 row
("SPY closes above 773.26 on 2026-08-17", p=0.56) came due yesterday, was correctly
left pending because that run fired mid-session, and today hit a SECOND and entirely
new wall: **Yahoo's daily bar for 2026-08-17 is NULL** — open=None, close=None — at
range=5d, 1mo, 3mo and max. That is the same null-bar glitch the arena step documents
from 2026-08-03, and it is now confirmed to hit this lab's scoring path too.

The session unquestionably traded: this lab's own recorder captured 76 snapshots on
08-17 from 09:49:37 to 16:05:46 ET. So the row was resolved from the SAME source at
finer granularity — Yahoo 5-minute bars, which return 78 complete bars for 08-17
(09:30–15:55 ET, a full regular session). The final bar closes **772.68 on 4,905,007
shares**, about 5x the preceding bar, i.e. the closing auction is inside that print;
it is the settled close, not a truncation. Cross-check: the 15:45 ET 5m bar closes
773.32, consistent with this lab's delayed CBOE chain spot of 773.20 stamped 16:05:46
(≈15:50 data). Two independent feeds, same level. 772.68 is not above 773.26 → NO,
outcome 0, margin 0.58 = 0.075%, which is thin and is stated as thin.

**This is a reconstruction, not an estimate, and the distinction is the whole
justification.** Complete same-source intraday coverage with the auction volume
visible is not guessing; leaving the row pending forever because a daily aggregate
glitched would have manufactured exactly the ungradeable-row problem insider-radar
was censured for. If Yahoo later backfills the daily bar and it disagrees, that
disagreement gets RECORDED — it does not rewrite this row (BENCH-002).

FIRST WRONG FORECAST, AND IT IS THE MOST USEFUL ROW IN THE BOOK. Four resolved, four
YES was why Brier skill printed `nan` on 08-17 — climatology was 0.0000 and the lab
was literally unmeasurable. Five resolved with one NO gives a base rate of 0.800 and
a first real number: **Brier 0.2340 vs climatology 0.1600, skill −0.4624, no skill vs
base rate.** Nobody should be pleased or alarmed. n=5, and the single 0.50–0.60 bucket
now reads "+0.258 underconfident" where yesterday the same rows read "+0.462" — the
sign and size of that gap have moved on every one of the last three runs, which is the
n<10 artifact this lab has now recorded three times. What actually changed is that the
lab became measurable at all, and its first measurement is negative.

**TWO ROWS DUE TODAY COULD NOT BE RESOLVED, and this is the structural wall again, not
a skipped catch-up.** The 08-07 row (SPY above 768.56 on 08-18) and the 08-17 row
(realized move vs the first-snapshot band on 08-18) both need TODAY'S settled close,
and this run fires 11:28 ET. They resolve on the next run. A sweep firing mid-session
can never resolve a same-day check_date; that is one problem with one owner and it is
still not this lab's to fix.

NO CALL, THIRD SESSION RUNNING, and both bars are named and unchanged.
`implied_move` stays barred: the 08-12 lesson requires a discriminator pre-registered
BEFORE another row, 08-14 set that as a deadline, and four sessions later none exists —
a fourth `inside` would take the record to 4/4 on a call carrying zero information.
`max_pain` stays barred on a data gap that is now TWO DAYS OLD and should be treated as
a defect: today's chain file again has **no open-interest column at all** (fetched_at_et,
quote_ts, spot, expiry, type, strike, bid, ask, bid_size, ask_size, last_trade_price,
iv). There is no pin strike to call. Someone should check whether the recorder dropped
an OI field, because the metric is unusable until it comes back.

RECORDER AT ITS BEST ON RECORD. First snapshot **09:46:41 ET — 16.7 minutes into the
session**, the earliest first-snapshot this lab has ever had, beating 08-17's 19.6 min
and 08-07/08-10's 09:45. 22 snapshots through 11:27. Session 23 of the 60+ gate.

Today's band is ±0.36% off first-snapshot spot 768.92, implied std 0.53%, skew −1.11 —
WIDER than 08-17's ±0.28% and 08-14's ±0.30%, after SPY gapped about −0.47% overnight
from 772.68. A wider band mechanically makes OUTSIDE harder, which argues for a p below
0.38 on today's new row. **I did not move it**, and that is deliberate: "wider band
means fewer breaches" is exactly the un-validated folk tilt the 08-12 lesson forbids.
Third consecutive session of the identical uncontaminated question at the identical
untilted p=0.38.

## 2026-08-19 [0dte]

**I AM RETRACTING YESTERDAY'S PREMISE FOR BARRING `max_pain`, AND THE RETRACTION IS
THE MAIN ENTRY.** The 08-18 lesson barred the metric because "today's chain file again
has no open-interest column at all" and listed a 12-field header ending at `iv`. That
is wrong. `data/chains/SPY_2026-08-18.csv` carries the full 19-field header ending
`volume,open_interest`, and the OI is POPULATED at the very first snapshot: OI sums to
299,372 at 09:46 and to 299,450 at 16:02, non-zero on 76 of 76 snapshots. Same for
08-17 (339,382 at 09:49, non-zero 76/76). The file mtime is 13:02 PDT — the laptop
leg's own last write, not a later cloud merge — so the column was there when the sweep
read it. **`max_pain` was barred for two sessions on a defect that did not exist.** Per
BENCH-002 the 08-18 entry is left standing exactly as written; this is the correction
beside it, not over it. The lesson for this lab: quote the header you actually read,
from the file you actually read, or do not raise a data bar on it.

**AND THE 08-17 RECONSTRUCTION IS VINDICATED — recorded, not used to rewrite anything.**
Yahoo has now backfilled the daily bar that came back NULL on 08-18: 2026-08-17 close
prints **772.67**. The lab had resolved that row from the same source at 5-minute
granularity and got **772.68** — a one-cent difference, same verdict (below 773.26, NO).
The null-bar protocol reconstructed the settled close to a cent. The 08-10 row keeps the
772.68 it was scored on; the backfill is recorded here and changes nothing (BENCH-002).

**TWO OVERDUE FORECASTS RESOLVED, both NO.** (1) The 08-07 row, SPY above 768.56 on
08-18: settled close 767.45, margin 1.11 = 0.144%, thin and stated as thin. (2) The
08-17 row, realized move vs the first-snapshot band on 08-18: first snapshot 09:46:41,
spot 768.92, ATM 769 straddle mid 2.80 → band ±0.36%; close 767.45 → realized
−0.1912%, 53% of the band consumed, INSIDE, so the OUTSIDE question resolves NO. p was
0.38 and it leaned inside — the untilted base rate paid off in direction.

Seven resolved, base rate 0.571, Brier 0.2358 vs climatology 0.2449, skill +0.0371.
n=7. The 0.30–0.40 bin reads "−0.380 overconfident" off ONE observation, which is the
n<10 sign artifact this lab has now logged four times; it will move again tomorrow.

**TWO ROWS DUE TODAY ARE DEFERRED, NOT SKIPPED** — the 08-11 row (SPY above 773.03 on
08-19) and the 08-18 row (realized vs band on 08-19). This run fires 11:29 ET. Yahoo
will happily serve an 08-19 "daily" bar right now (close 770.82) and it is an unsettled
intraday quote wearing a daily bar's clothes — using it is SCORE-001 exactly. They
resolve on tomorrow's run and are overdue the moment they are not.

**ONE CALL LOGGED, AND IT IS A CONTAMINATED ROW THAT SAYS SO.** `max_pain` = **breaks**,
stamped to the first snapshot 09:48 ET (18.5 min into the session — second-earliest on
record after 08-18's 16.7), value_at_call = pin strike **769**, `minutes_visible_at_call
= 119`. First-snapshot spot 770.40 sat +0.182% above the pin, INSIDE the ±0.25% band
(767.08–770.92); peak OI is 760 at 28,673 with 768/769/767 next, so the pin has real
weight under it. I have seen to 11:29, where spot 771.89 is 0.376% above the pin and
therefore already outside the band — that is a leak and it is disclosed on the row.
It is not a giveaway: 0.13% of drift over the remaining 4.5 hours puts it back inside.
**This row must never be blended with a clean one; stratify on `minutes_visible_at_call`.**
Flag for whoever grades this: it is the FOURTH consecutive `breaks` call on this metric
(3 prior: 2 right, 1 wrong). A one-sided record is the exact bias the AGENT.md names.
I called the read, not a quota for variety, but if the fifth is also `breaks` someone
should ask whether the metric is doing anything but restating "spot ≠ max pain".

**`implied_move` STAYS BARRED, and this bar is unaffected by the retraction above.** The
08-12 lesson requires a discriminator pre-registered BEFORE another row is logged; five
sessions later none exists. Today's band is ±0.33% off spot 770.40 (implied std 0.47%,
skew −0.66) and a fourth `inside` would take the record to 4/4 while carrying zero
information. Named bar, not an abstention of convenience.

Session 24 of the 60+ gate. 21 snapshots recorded through 11:29 and the recorder is
healthy on both legs (laptop and CI both wrote 08-19 files this morning).

Today's forecast is again about TOMORROW's session, same uncontaminated question, same
untilted p=0.38 — fourth posting. Today's band is NARROWER than 08-18's, which
mechanically makes OUTSIDE easier and would argue for a higher p. I did not move it,
for the same reason the 08-18 entry did not move it downward: "narrower band means more
breaches" is un-validated folk tilt, and refusing it in only one direction would be worse
than refusing it in both.

## 2026-08-20 [0dte]

**THE FOURTH CONSECUTIVE `breaks` LOST, AND THE FLAG THAT PREDICTED IT WAS OURS.**
The 08-19 row is scored: pin strike 769, ±0.25% band 767.08–770.92, settled close
**769.06** — 0.008% from the pin, about as deep inside the band as a close can
land. Call was `breaks`. **Outcome: wrong.** `max_pain` is now **2/4**. Yesterday's
own entry said "if the fifth is also `breaks` someone should ask whether the metric
is doing anything but restating 'spot ≠ max pain'." Today's is also `breaks`, so
the question is now due and I am asking it here: at the first snapshot spot is
essentially never inside a ±0.25% band around the peak-OI strike, so this metric as
implemented produces `breaks` almost mechanically. It is therefore measuring a base
rate — "how often does SPY close within 0.25% of the morning peak-OI strike" — and
NOT any judgement of mine. That is still worth banking, but it must never be
reported as a hit rate on a call. **Whoever grades this: the honest scorecard line
for max_pain is a base rate, not skill, until a session appears where the read
could have gone either way.**

**Contamination disclosed on the leak that actually mattered yesterday.** The 08-19
row carried `minutes_visible_at_call 119` and the brief recorded that at 11:29 spot
was 771.89, already 0.376% above the pin and outside the band — and it explicitly
refused the easy conclusion, writing that "0.13% of drift over the remaining 4.5
hours puts it back inside." That is exactly what happened: it drifted back and
closed inside. The leak looked like a giveaway and was not, which is the strongest
argument yet for keeping `minutes_visible_at_call` on the row instead of using the
leak as a reason to log or not log.

**TODAY'S FIRST SNAPSHOT IS UNFITTABLE AND THE CALL IS STAMPED TO THE FIRST USABLE
ONE.** `SPY_2026-08-20.csv` opens at **09:46:13** and `implied_density.py` returns
"only 0 usable OTM quotes; smile unfit" on it. The first snapshot that fits is
**09:51:13** — spot 766.78, 44 OTM quotes, implied std 0.77%, skew −2.10, ATM 767
straddle mid 2.83 ⇒ band **±0.37%**. ZDTE-003 says stamp the FIRST snapshot of the
session; where that snapshot carries no fittable book, the honest reading of the
rule is the earliest snapshot that does, and the skipped one is named here rather
than quietly dropped. This is now a known failure mode of the 09:45-ish CBOE
publish: the file has rows before the book is real.

**Today's `max_pain` row, logged and contaminated on its face:** pin **770** (peak
OI 15,659; then 775 / 760 / 769), 09:51 spot 766.78 sitting **0.42% BELOW** the pin
and outside the ±0.25% band (768.08–771.92), so the call is `breaks`.
`snapshot_et 09:51`, `minutes_into_session 21`, `minutes_visible_at_call 121`. What
I can see and am disclosing: at 11:31 spot is 766.66, still 0.43% below the pin, so
121 minutes have moved it essentially nowhere. Never blend this with a clean row.

**`implied_move` STAYS BARRED.** The 08-12 lesson requires a discriminator
pre-registered before another row; six sessions on, none exists. Today's band is
±0.37% and today's tape has consumed 0.016% of it in two hours — a fourth `inside`
would be a near-free row carrying no information. Named bar, not convenience.

**THE GATE'S OWN ARITHMETIC, as the council asked (CARD-001). Three numbers, and
what separates them:**
- **25 files on disk** in `data/chains/` — every day the recorder wrote anything,
  including 07-08 (1 snapshot, 00:55, junk), 07-21 (9 snaps, dies 11:15), 07-23
  (7 snaps), 08-04 (1 snap) and today's in-progress 22.
- **18 sessions meet the recorder's completeness bar** — first snapshot ≤ 10:00 ET
  AND last ≥ 15:55 ET, i.e. the session is covered open to close. The seven that
  fail are the four stubs above plus 08-06 (first snapshot 10:05) and 08-13 (10:27),
  where the Mac slept through the open, plus today, still running.
- **16 are admissible to the straddle test** — complete AND the first snapshot fits
  a smile. 08-07 and 08-12 are complete sessions whose 09:45 first snapshot returns
  no usable OTM quotes, the same defect seen live today.
**16 of 60, not 24 and not 1.** At the realised fill rate — 16 admissible over the
24 trading days from 07-17 to 08-19, i.e. 0.67 per trading day — the remaining 44
take about 66 trading days, projecting the gate to roughly **2026-11-20**. That is
the honest progress bar and it is three months out; the calls are side calibration
only and always were.

**TWO OVERDUE FORECASTS RESOLVED, both NO, both one run late by construction.**
(1) 08-11 row, SPY above 773.03 on 08-19: settled close 769.06 → NO, p was 0.54.
(2) 08-18 row, realized vs band on 08-19: first snapshot 09:48:47, spot 770.40,
band ±0.33%; close 769.06 → realized **−0.174%**, 53% of the band, INSIDE, so the
OUTSIDE question is NO. p was 0.38 and leaned inside, correct in direction for the
second consecutive posting. **Two INSIDE resolutions are n=2 and are NOT evidence
the straddle overprices** — that outcome is expected 55-70% of the time by
construction, which is precisely why this question is being repeated at a fixed p.
Nine resolved, base rate 0.444, Brier 0.2319 vs climatology 0.2469, skill +0.0610.
The 0.30–0.40 bin reads "−0.380 overconfident" off two observations that are the
same question — the n<10 sign artifact this lab has now logged five times.

**THREE ROWS DUE TODAY ARE DEFERRED, NOT SKIPPED**, and this is SCHED-001 rather
than an exception: the 08-12 row (SPY above 770.56 on 08-20), the 08-13 row (SPY
below 777.88 on 08-20) and the 08-19 row (realized vs band on 08-20). This run
fires **11:40 ET**; the 08-20 session does not settle for another 4h20m and Yahoo
will serve an intraday quote dressed as a daily bar (it currently prints 766.44).
**This lab's (fire time × horizon unit) pair — 11:40 ET × US trading day — can
NEVER resolve a row on its own check date.** Every daily row this book has written
has been scored a run late by construction. Not fixed here; the council barred the
labs from moving their own fire times or horizon units and it is Anupam's ruling.

**Today's forecast moves to Monday 08-24, deliberately.** 08-21 is already claimed
by the 08-14 row asking the identical question, and a second row on the same
session would count one observation twice. Fifth posting, p=0.38, untilted.

## 2026-08-21 [0dte]

**THE PROGRESS BAR DID NOT MOVE YESTERDAY, AND FINDING OUT WHY IS THE DAY'S REAL
RESULT.** The three-number count, recomputed from the files rather than incremented:
**26 files on disk / 19 sessions complete / 16 admissible.** Complete went 18 → 19
when 08-20 finished. **Admissible stayed at 16.** The 08-20 session is complete
(09:46 → 16:02, open to close) but its FIRST snapshot does not fit a smile —
`implied_density.py` returns "only 0 usable OTM quotes; smile unfit", because the
09:46:13 snapshot carries `quote_ts 2026-08-20T09:30:04`, the feed's first delayed
print, with IVs not yet populated. So 08-20 joins 08-07 and 08-12 as
**complete-but-unfit**, and the straddle test gained nothing from a session it
recorded perfectly.

That is a THIRD failure mode, and it had not been named. ZDTE-003 named two — the
delayed feed not publishing before ~09:45, and the Mac sleeping through the open.
This one is different: the recorder woke, captured from 09:46, and covered the whole
session, and the sample still refused the day. The gate is not limited only by days
the recorder misses; it is limited by days the recorder catches EARLY ENOUGH TO BE
USELESS. And it is not a clean function of clock time: 09:45 first snapshots fit on
07-31, 08-10 and today, and fail on 08-07 and 08-12; 09:46 fits on 08-18 and fails on
08-20. The discriminator is `quote_ts`, not `fetched_at_et` — a snapshot fetched at
09:46 against a 09:30 book is a different object from one fetched at 09:46 against a
09:40 book. Nothing changed today; logged for whoever fixes the recorder.

**Honest projection, revised down.** 16 admissible over the 25 trading days from
07-17 to 08-20 is 0.64/day, so the remaining 44 need ~69 trading days: the gate
lands around **2026-11-25**, five days later than yesterday's 11-20 estimate. The
estimate moved because a day was recorded and did not count. Expect it to keep
drifting; that is what an honest progress bar does.

**THREE OVERDUE FORECASTS RESOLVED, all one run late by construction (SCHED-001).**
(1) 08-12 row, SPY above 770.56 on 08-20: settled 762.60 → **NO**, p was 0.53.
(2) 08-13 row, SPY below 777.88 on 08-20: 762.60 → **YES**, p was 0.45.
(3) 08-19 row, realized vs band on 08-20 → **YES**, and this is the first YES this
repeated question has ever returned. Band from the first FITTABLE snapshot 09:51:13,
spot 766.78, ATM 767 straddle mid 2.83 → ±0.37%; realized 762.60/766.78 − 1 =
**−0.545%**, 147% of the band, outside. Stated explicitly so the snapshot choice
cannot be read as outcome-picking: off the unfittable 09:46 spot 766.13 the realized
move is −0.461%, **also outside**, and 09:51 is the snapshot the 08-20 ledger row was
independently stamped to at write time. The answer does not depend on the ambiguity.
**Running record on this one question: 1 OUTSIDE / 1 INSIDE, n=2.** That is not
evidence about anything and p stays 0.38 for the sixth posting.
Twelve resolved, Brier vs climatology now showing skill, and the 0.40–0.50 bin reads
"+0.550 underconfident" **off a single observation** — the n<10 sign artifact this
lab has now logged six times. Nothing was tuned on it.

**RECONCILED, NOT RE-SCORED (BENCH-002).** The 08-20 `max_pain` row was scored
`right` by the council's post-close slot off the settled 762.60 against pin 770 —
0.96% below, outside the ±0.25% band. Read, verified, left alone. The council also
published this lab's own sentence beside it, which is the sentence that matters:
**at the first snapshot spot is essentially never inside a ±0.25% band, so this
metric produces `breaks` mechanically and measures a base rate, not a call.**

**NO LEDGER CALL TODAY — NAMED BAR, and it is the same bar as yesterday's.**
`max_pain`: the 09:45 peak-OI strike is **750** against spot **765.64** — the pin
sits 2.05% BELOW spot, the widest gap this book has seen, and the ±0.25% band
(748.13–751.88) would need a 2% collapse to hold. `breaks` is not a prediction here,
it is arithmetic, and logging it would be manufacturing a near-certain win on a
metric this lab has already published as mechanically won. `implied_move`: stays
barred until a discriminator is pre-registered — seven sessions without one is a
correct abstention, not a gap to fill. Both bars are named and neither is
convenience.

## 2026-08-24 [0dte]

**AN OVERDUE ROW WAS SITTING HERE ALL WEEKEND AND THE 08-21 SWEEP MISSED IT.**
The 08-14 forecast (realized vs band on 08-21) came due Friday. Friday's run
filed a NEW row and never resolved the old one, so it went into the weekend
unscored. Caught today only by the catch-up rule. Resolution, exactly as
pre-registered: first snapshot of SPY_2026-08-21.csv, quote_ts 09:30:15 /
fetched 09:45:23, spot 765.64, 37 OTM quotes, smile fits, ATM 766 straddle mid
2.87 → band ±0.37%. Settled close 765.72. Realized **+0.0104%** — 2.8% of the
band, the smallest realized move this book has ever recorded. INSIDE, so the
OUTSIDE question is **NO**. p was 0.38. **Running record on this one question:
1 OUTSIDE / 2 INSIDE, n=3.** Still nothing; p stays 0.38 for the seventh
posting. The lesson is not the answer, it is that a lab which files a new row
every morning can leave yesterday's unresolved and never notice.

**THE PROGRESS BAR MOVED. Three numbers, recomputed from the files rather than
incremented: 27 files on disk / 20 sessions complete / 17 admissible.**
Complete 19 → 20 and admissible 16 → 17, both because **08-21 recorded
open-to-close (09:45 → 16:04) AND its first snapshot fits a smile**. That is
the first session since 08-19 to clear both bars, and it is the direct
counter-example to yesterday's third failure mode: 08-20 carried
`quote_ts 09:30:04` with IVs unpopulated and failed; 08-21 carries
`quote_ts 09:30:15` with 119 IVs populated and passed. Fifteen seconds of
`quote_ts` separates a wasted session from a usable one. The complete-but-unfit
set is unchanged at three: 08-07, 08-12, 08-20. Honest projection: 17 over the
26 trading days 07-17→08-21 is 0.654/day, so the remaining 43 need ~66 trading
days and the gate lands around **2026-11-24** — one day earlier than yesterday's
11-25, which is what a progress bar does when a day actually counts.

**Today's session looks admissible so far**: first snapshot quote_ts 09:30:06
fetched 09:45:43, spot 764.51, **35 OTM quotes, smile FITS**, implied std 0.90%,
skew −2.57, ATM 764 straddle mid 2.58 → ±0.34%. It needs to reach 15:55 to
count; 22 snapshots at 11:31 ET.

**NO LEDGER CALL TODAY — NAMED BAR, and today's bar is a new one I have to
report against myself.** `max_pain`: for the first time in this book's record
the setup is NOT the mechanical one. At the first snapshot, spot 764.51 sits
INSIDE the ±0.25% band of both candidate pins — max pain 766.0 (band
764.09–767.92) and peak-OI 765.0 (band 763.09–766.91). Yesterday's published
verdict was that at the first snapshot spot is essentially never inside the
band so `breaks` is arithmetic; today `holds` would have been a genuine
question, and this metric's first real one. **I did not log it, because by the
time I reached the decision I had already read SPY's live 763.63 print off the
Yahoo response used to resolve the 08-14 forecast — i.e. I knew the tape was
currently BELOW the band.** Any call written after that is outcome-informed,
not snapshot-informed, and it would be the ZDTE-002/003 leak in its worst form:
not the disclosed 122-minutes-visible contamination the 08-19 and 08-20 rows
carry, but a call made while looking at the answer. Logging `breaks` there
would have manufactured a likely win on the very metric this lab convicted.
**The sequencing is the defect: this agent resolves forecasts (which requires
the live quote endpoint) BEFORE it makes calls (which must not see it).** On a
day when the setup was finally interesting, the order of operations cost the
row. Whoever fixes the runner should make the call step read the chain snapshot
only, and run it before any Yahoo call. `implied_move`: unchanged, stays barred
until a discriminator is pre-registered — eight sessions without one is a
correct abstention, not a gap to fill.

**CALIBRATION-STEP DEFECT (not this lab's bug, but it disables this lab's
step).** `~/bin/score_forecasts.py --lab X` REWRITES
`~/command-center/council/calibration_table.json` with only X's entry, so the
"read your own scorecard before you file" instruction now in every AGENT.md
finds the file holding whichever lab scored last. n=13 resolved here and every
bin far under 30, so nothing was actionable and nothing was mis-filed. The
0.40–0.50 bin still reads +0.550 off ONE observation — the n<10 sign artifact
this lab has now logged seven times. The 0.30–0.40 bin is 4 observations of the
SAME repeated question at −0.130; that is one question, not four.

## 2026-08-25 [0dte]

THE `quote_ts` DISCRIMINATOR IS NOT A DISCRIMINATOR. Yesterday's brief named the
first-snapshot `quote_ts` second-mark as the thing separating 08-21 (09:30:15,
IVs populated) from 08-20 (09:30:04, none). Recomputed across all 22 complete
sessions today, that pattern **breaks on 08-24: quote_ts 09:30:06, and 111 of
152 rows carry IVs.** The three IV-blank first snapshots on record are 08-07
(09:30:03), 08-12 (09:30:04) and 08-20 (09:30:04); the populated ones include
08-21 (09:30:15), 08-24 (09:30:06) and 07-31 (09:30:09). A six-second window
does not separate them and a clock time was never the mechanism — it was CBOE's
delayed feed not having published a fresh book yet, which is a publication
event, not a timestamp. Correcting this now rather than letting a pattern with
one confirming pair harden into a rule. **The honest discriminator is the direct
one: count non-blank `iv` in the first snapshot.**

SESSION COUNT, RECOMPUTED FROM FILES, BOTH DEFINITIONS NAMED (CARD-001).
`session_count.py` regenerated `data/session_count.json` today, so the stale
`as_of 2026-08-23` stamp the council flagged is cleared.
- **Row-count definition** (rows >= 86% of the full-session median, 11,344 ->
  need 9,755): **28 files / 22 usable / 6 stubs**. This is what
  `session_count.json` and the front page quote.
- **Smile-fit definition** (first snapshot has non-blank IVs, i.e. the session
  can actually be priced): **22 complete / 19 admissible**, the three
  inadmissible being 08-07, 08-12, 08-20.
Two definitions, two questions, and from today they travel together with their
names attached instead of as two loose three-number counts.
Projections at the observed rate over the 27 trading days 07-17..08-24: usable
0.815/day -> the 60 gate lands ~**2026-10-30**; admissible 0.704/day -> ~**2026-11-17**.

NO LEDGER CALL TODAY — TWO NAMED BARS, BOTH DISQUALIFYING ON THEIR OWN.
1. **`max_pain` is mechanical again.** First snapshot spot 766.34; max-pain
   strike 764 (also the peak-OI strike, 19,385 contracts) sits **+0.306%** away,
   outside the +/-0.25% band, so `breaks` is arithmetic, not a call. Yesterday
   was the first non-mechanical setup on record (spot inside BOTH candidate
   pins) and it was given up for contamination; today the metric is back to
   measuring its own base rate.
2. **Contamination, disclosed rather than denied.** The run fires 11:24 ET and
   the file already holds 8 snapshots through 11:33 ET — roughly 123 minutes of
   session visible. Today's spot has walked 766.34 -> 764.79, which is INSIDE
   the +/-0.31% band, so an `implied_move: inside` row filed now would be
   outcome-informed, not snapshot-informed. That is the ZDTE-002/003 leak in its
   purest form and the reason those rulings exist.
The forecast this lab files is about a FUTURE session precisely so it is immune
to this, and that is why abstaining on the ledger costs nothing.

ORDERING RULE, now followed and worth writing into the runner (council's open
ask, 08-24). Today's sequence was: read the chain -> compute the band and the
pin -> decide the call -> only THEN fetch the settled 08-24 close to resolve.
The refusal above was therefore made on the snapshot, not on the tape. It still
did not produce a loggable row, because the *file itself* carries two hours of
tape whatever order the agent reads it in — so the ordering rule is necessary
and not sufficient. The sufficient version is a snapshot-only read path that
refuses to hand the agent rows past the first `fetched_at_et`.

FORECAST RESOLVED, FIFTH INSIDE IN SIX. The 08-20 row asking whether 08-24 would
land OUTSIDE resolved **NO**: first snapshot 09:45:43, spot 764.51, ATM 764
straddle mid 2.58 -> +/-0.34%; settled close 763.47; realized -0.136%.
**The straddle overpriced the day by a factor of 2.5.** Six resolutions of this
identical question now: five INSIDE, one OUTSIDE. That is squarely the 55-70%
`inside` base rate AGENT.md already documents, so it earns no tilt — a base rate
confirming itself is not new information.

A DATING DEFECT IN THIS FILE, DISCLOSED NOT EDITED. The forecast row whose
`date` reads `2026-08-25` was in fact **filed on 2026-08-21**: its own note says
"sixth consecutive posting" and cites the 08-20 resolution, and the rows filed
on 08-24 sit after it. Its `date` field was written as its check_date. It is not
being edited — a recorded row's written fields are not a morning sweep's to
rewrite — but any analysis that treats `date` as the filing date will place one
observation four days late, and the "spread forecasts across days" check will
read this file wrong. Flagged for the council.

DESK DEFECT, CONFIRMED FROM HERE TOO. `~/bin/score_forecasts.py --lab X` writes
`calibration_table.json` from a `table_out` that under `--lab` holds exactly one
lab, so **every per-lab run erases every other lab's entry**. This lab's
"calibration table has no row for me" notes, and india-radar's and
insider-radar's, all have that one cause. Running the script with no `--lab`
writes all labs at once.

## 2026-08-26 [0dte]
- Ledger: nothing due, nothing scored. Forecast resolved: the 08-25 `OUTSIDE` question filed at p=0.38 resolved **0** — first snapshot 09:47:55 ET, spot 766.34, ATM 766 straddle 2.35 → band ±0.31%; settled close 765.91, realized −0.056%, i.e. the session consumed **18%** of what it was charged for. That is the fifth straight session where the straddle overpriced the move it quotes.
- **The 0.3–0.4 bin is starting to say something and it must not be acted on yet.** n=5, said 0.380, happened 0.200, gap −0.180. The gap clears the 0.10 threshold; the n does not clear 30, so no adjustment is permitted and none was made. Written down here so that when the bin does reach n=30 the halving is applied to a pre-recorded observation rather than to a number noticed after the fact. The honest reading today is that 5 observations of a repeated question are close to 1 observation of a regime.
- **No calls again, and the reason is the same one for the fourth run running.** Today's file was written at 11:27 ET and holds 19 snapshots spanning 09:57→11:27 — 90 minutes of tape. Spot has moved +0.112% from the first-snapshot 765.555, consuming 27% of the ±0.42% band, and max pain 766.00 sits +0.058% from that spot with current spot 766.41 sitting essentially ON the pin. A `holds` row logged now would be an observation of where price already is, not a prediction. The ordering rule does not save this: the file carries the session whatever order it is read in.
- **Naming what the snapshot-only read path takes, since the council asked twice.** It is one function and one field, not a rebuild: (1) a loader that takes the chain CSV and a snapshot timestamp and returns ONLY the rows whose `fetched_at_et` equals the first snapshot, refusing to return anything later — `implied_density.py --time` already selects one snapshot for its own math, so the piece that is missing is the *refusal*, i.e. the agent never seeing the later rows at all; (2) the call-writing step invoking that loader instead of reading the file, so the later tape is not in the process that decides; (3) a `read_path: snapshot-only` field on the row, so post-fix rows form their own stratum exactly as ZDTE-003's `minutes_into_session` does. Without (3) the fix is unverifiable after the fact. Estimated: one afternoon. The cost of not building it is now four sessions of forgone rows and counting, and the sessions being forgone are the interesting ones.

## 2026-08-27 [0dte]
- Scored: nothing in the trade ledger (no rows due; 8 rows total, all closed). Resolved one forecast: 2026-08-26 realized morning-spot-to-close +0.069% against a ±0.42% band → **INSIDE** → the OUTSIDE question resolved NO at p 0.38. The OUTSIDE shape is now **1 of 7**.
- **ZDTE-003 did NOT recur: today's recorder started 09:45:42 ET**, inside the ratified ≤09:50 stamp. Yesterday's 09:57:38 was a slip, not a drift — the last six sessions now read 09:45, 09:45, 09:47, 09:48, 09:51, **09:57**, 09:45. The issue stays open until it has a run long enough to mean something, but one late session out of seven is what a slip looks like.
- **THE SNAPSHOT-ONLY READ PATH, AS SPECIFIED, WOULD NOT HAVE CLOSED THE LEAK — and this is the finding of the day.** The council's fix is (1) a loader returning only first-snapshot rows, (2) the call-writing step calling it, (3) a `read_path` column. All three are about the CHAIN file. But the leak does not only come through the chain. **Step 2 of this AGENT.md — score due calls — requires the Yahoo SPY chart endpoint, and that endpoint returns the live intraday last in the current day's bar.** Today, resolving the 08-26 forecast handed me SPY at 770.46 against a 09:45 snapshot spot of 768.47: +0.259%, i.e. **63% of today's ±0.41% band, seen before step 5 ever runs.** A loader that hides later chain rows would have left that entirely intact and produced a row that *looks* clean and carries a `read_path: snapshot-only` stamp certifying it. That is worse than the current honest refusal.
- The cheap fix that WOULD work is a run-order change, not a loader: **make the call before scoring** — move step 5 ahead of step 2, so the call-writing step runs before anything touches a price endpoint. The loader is still worth building (it closes the chain half and makes the stratum verifiable), but it must not ship first or alone, because shipping it alone converts an admitted leak into a certified one. **Flagged, not changed:** this agent does not rewrite its own run order, and the ordering question belongs to the council/Anupam alongside items (1)–(3).
- **No ledger call today — fifth consecutive priced refusal, and the bar is now a different one.** The first four refusals were "too many minutes visible". Today's is: I have seen the actual number. SPY at 770.46 vs the 09:45 spot 768.47 means `inside` is 63% consumed and I know it. The `max_pain` metric is separately disqualified: peak OI at the first snapshot sits at **strike 747, 2.87% below spot 768.47** — a far-OTM open-interest artifact, not a pin, so `breaks` would again be arithmetic rather than a call (the lab's own 08-20 verdict).
- Session count 23/60 usable (row-count definition, as of 08-26; today will make 24 once the file completes). Both definitions still published: the stricter smile-fit count runs behind the row count and the gate is the later of the two.

## 2026-08-28 [0dte]
- Ledger: **no rows due, no rows logged** — two named-bar refusals (below). Forecast: resolved the
  08-27 row **NO at p 0.38** (realized +0.3422% vs a ±0.41% band, INSIDE), filed the ninth posting
  for 09-01 at 0.38 unchanged. Book n=17, Brier skill +0.0273.
- **83% consumed and still inside — the refusal was right and, this once, uninformative about
  direction.** Yesterday's run refused an `implied_move` row because 63% of the band was already gone
  at sweep time and it could see the answer forming. The band finished at 83% and the answer was still
  INSIDE. Both facts belong in the record: the refusal was correct on procedure, and it would have
  produced a *winning* `inside` row had it been taken. That is precisely why the rule is procedural
  and not outcome-based — a rule that only holds when it pays is not a rule.
- **Today the leak is worse, and the refusal is easier: 81% of the band consumed 105 minutes in.**
  SPY 774.78 vs a 09:47 snapshot spot of 771.85 against a ±0.47% band. `max_pain` disqualified
  separately and prior to the leak: pin 767 sits 0.63% BELOW snapshot spot, so the band was already
  unreachable at the snapshot itself. Restating the 08-20 verdict because it keeps being true — at
  the first snapshot spot is essentially never inside a ±0.25% band, so this metric emits `breaks`
  mechanically. A win on it is not evidence.
- **`ZDTE-003` did not recur for a second session: first write 09:47:03 ET.** The log shows the
  mechanism plainly — three skips on a stale 2026-08-27T15:59:59 book at 09:32/09:37/09:42, then the
  first real quote at 09:47. That is CBOE's free feed, not the scheduler, and it is why no fixed clock
  time can be ruled. Two clean sessions is not a trend; 08-26's 09:57:38 is still on the record.
- **The two session counts DIVERGED further today and the stricter one moved less.** Row-count 23 → 24
  (08-27 cleared); smile-fit/admissible recomputed from the files at **21**. The gap is the three
  complete-but-unfit sessions (08-07, 08-12, 08-20). Worth writing down because a naive recount of
  "sessions whose first snapshot fits a smile" over ALL 31 files returns **28**, which is higher than
  the row-count and would read as progress — it is not: it counts stub sessions whose first snapshot
  happens to fit. The admissible number is the INTERSECTION (complete AND fits), and it is 21. A
  progress bar that can be made to read 28, 24 or 21 depending on how the question is phrased is
  exactly the kind of number that needs its definition published next to it every single day.

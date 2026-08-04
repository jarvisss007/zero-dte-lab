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

# zero-dte-lab

Research lab for SPY 0DTE: implied-distribution tooling, timing-thesis tests,
and honest backtests of chart strategies before any of them touch money —
paper or otherwise. Companion to `~/spy-trading` and follows the same rule:
**the README states the verdict, and the verdict comes from the code, not
from hope.**

## Verdicts (2026-07-06)

### 1. Timing thesis — PARTIALLY CONFIRMED, but it's the known U-shape
Tested on 23,087 non-overlapping 5-min returns over 302 sessions
(Aug 2024 – Nov 2025), `src/timing_tester.py`:

All times below in Anupam's clock (Pacific); market = 06:30–13:00 PT.

- Big moves (top-decile |5-min return|) cluster **hard** at the open
  (06:35–07:00 PT, up to 21.5% frequency vs 10% baseline) and the close
  (12:50–12:55 PT), Bonferroni-significant. 07:25 PT also clears the bar.
- The six r17 windows read as **ET** (what Pine's `time()` actually tested):
  12.3% big-move frequency vs 10% (p=0.002), driven almost entirely by the
  9:45/10:00 ET (= 06:45/07:00 PT) windows.
- The same window numbers read as **PT** (if they were derived from the
  hand-logged Pacific-time xlsx): they land in the early-afternoon-ET dead
  zone and are significantly QUIETER than baseline (7.9% big-move frequency,
  p=0.016; mean |ret| below the rest of the day). Under this reading the
  window list is actively counterproductive.
- TIMEZONE ACTION ITEM: r17's `time()` windows run in exchange time (ET).
  If the windows were meant as PT, the script has been trading different
  times of day than intended. Either way, the only windows worth keeping are
  the open (06:35–07:00 PT) and the close (12:50–12:55 PT).
- **This is the textbook intraday volatility U-shape. Market makers price it
  into 0DTE options. Elevated realized movement is NOT an edge until shown to
  exceed what the options market charges for it at those times — that test
  needs the chain recorder (phase 2, not built yet).**

### 2. r17 sweep strategy — NO EDGE; backtest performance was the lookahead bug
`src/sweep_backtest.py` ports r17's active config (liquidity sweeps, OB
Primary mode, ATR SL / 2.5R TP / breakeven) and runs it three ways:

| HTF filter | result across all 3 datasets |
|---|---|
| LEAKY — reproduces r17's `request.security` bug | only positive rows anywhere (PF up to 1.44) |
| CAUSAL — completed 15-min bars only (live-executable) | negative or statistically zero everywhere |
| none — raw sweep concept | negative everywhere; **t = -2.9 on true-OHLC 5-min data** |

On true wicks (BATS 5-min, Jul–Aug 2025) short-only sweeps went 0-for-9
without the filter and 0-for-2 with the causal filter. The pseudo-OHLC
15-month run (wicks understated, so a *flattering* dataset for sweeps) still
flips from PF 1.44 (leaky) to PF 0.57 (causal) short-only.

**Conclusion: r17's Strategy Tester results are an artifact of the HTF filter
seeing up to 14 minutes into the future. Do not trade r17.** Apply
`pine/r18_htf_fix.pine` and re-run the Strategy Tester to see the honest
numbers on TradingView itself. Trade counts here are small (r17's filters are
very restrictive), so this is not proof the concept can never work — but the
burden of proof is on the strategy, and it failed everywhere it was tested.

### 3. Option-space cost — MEASURED (2026-08-15), and it is worse than share-space
`src/signal_cost.py`. Every verdict above scores strategies in SPY *points*.
Anupam trades SPY 0DTE *options*. Those are not the same number, and the gap
is now measured against 17 usable recorded sessions (Jul 17 – Aug 14 2026),
using real bid/ask on the real 5-minute book grid — pay the ask, sell the bid,
no mid fills.

**Finding 1 — the spread is not the tax.** ATM 0DTE round-trip spread is a
median **0.99% of premium** (median premium ~$109/contract). The prior
suspicion that the bid/ask would eat a whole target was wrong; SPY 0DTE ATM
is too liquid for that.

**Finding 2 — time is the tax, and the payoff is asymmetric.** A *symmetric*
SPY move is not symmetric in the option. ATM contract, median across all books:

| favourable SPY move | hold 15m | hold 30m | hold 60m |
|---|---|---|---|
| −0.50 pts | −29.0% | −35.3% | −43.3% |
| 0.00 pts | −6.7% | −11.9% | −22.2% |
| +0.50 pts | +19.8% | +16.7% | +9.5% |

(realized outcomes, `validate_payoff` — no interpolation, n = 124–544/cell.)

At ±0.5 points held 30 minutes you make 16.7% and lose 35.3%. **You need a
67.9% win rate just to break even.** The r17/r18 measured win rate is 19.8%
(15.6% on A-grades). Flat SPY still costs 11.9% at 30 minutes and 22.2% at 60
— that is pure theta, paid for being right about direction but slow.

**Finding 3 — the break-even cost curve** (`breakeven_curve`, model-free: the
book printed H minutes later is the pricing function, inverted for moneyness;
no greeks, the CBOE `delta` column is never trusted). Median SPY move an ATM
0DTE needs *just to break even*, by time of day (ET):

| | hold 15m | hold 30m | hold 60m |
|---|---|---|---|
| 09:30–10:00 | 0.171 | 0.307 | 0.528 |
| 11:00–12:00 | 0.096 | 0.186 | 0.309 |
| 14:00–15:00 | 0.041 | 0.112 | 0.231 |

This is a property of the **instrument, not of r18** — it outlives whatever
strategy comes next. Any future signal whose target is below this curve cannot
be traded in 0DTE options at that time of day regardless of its hit rate. Note
the open is the most expensive hour to hold, which is exactly when
`timing_tester.py` found the big moves cluster: the market maker prices the
U-shape. That is the *cost* half of the straddle-underpricing question; the
realized half still needs the 60-session gate.

**Finding 4 — the chart setup passes Constitution Rule 1 in share space and
fails it in option space.** Rule 1 demands a target ≥ 1.5R. In share space
that is trivial: a 0.4-point stop with a 0.7-point target clears it.
`rule1_target()` asks what the target must actually reach for the trade to
pay 1.5× what the stop costs *after* real bid/ask and decay. Target as a
multiple of the stop, for a 0.4-point stop:

| | hold 15m | hold 30m | hold 60m |
|---|---|---|---|
| 09:30–10:00 | 2.26 | 2.99 | 4.10 |
| 11:00–12:00 | 1.85 | 2.28 | 2.98 |
| 14:00–15:00 | 1.45 | 1.84 | 2.57 |

The labels on the live chart run a median target/stop of **1.71** (and their
TP1 is ~0.8, below 1R). So the setup clears Rule 1 only for a sub-15-minute
hold in the afternoon, and fails it everywhere else — worst in the first
half hour, where it needs ~3:1 to deliver 1.5R. The displayed "RR 1:6" on
every label is a constant string, not a computed field; no label in the
sampled screenshots was above 4.3:1 and the median was 1.7:1.

**Note on Rule 4.** The Constitution bars buying any option with ≤ 5 DTE
outright, so 0DTE is not a live instrument for this desk regardless of what
this lab finds. Rule 4 was written from experience ("the steady bleed — every
DTE bucket was net negative"); findings 2–4 are the arithmetic underneath it.
This lab remains research into what the options market charges, not a route
to trading the thing Rule 4 forbids.

**Finding 5 — r17's active config barely fires, and the two ports disagree
50×.** Over the same 17 sessions, the literal Pine config (sweeps only, OB
Primary Trigger, short-only) produced **1 signal**, not the 1–2/day the chart
suggests. Gate attrition: 131 sweeps → 15 survive `trend` agreement → 8 survive
the candle filter → 2 survive the HTF bias. Sweeps are counter-trend by
construction, so `sweep_bear and trend == -1` is nearly self-contradictory.

`~/ie-pro-project/reconcile_pine.py` (2026-08-15) confirms this independently
and pins the cause. Tightening that port toward `short_prim` one gate at a
time, its 96 trades survive `sweep_fresh_bars=1` (92 trades) and then collapse
to **1** the moment the trigger is restricted to sweeps alone. Roughly 95 of
its 96 trades were fired by **BOS or FVG**, which the Pine's OB-Primary mode
does not use as triggers at all. So ie-pro's PF 0.55 headline is a real result
about a BOS+FVG short strategy, not about r17's sweep strategy; its faithful
config fires ~2 signals a quarter, matching this repo's 1-in-17-sessions.

Signal costing therefore has no sample yet; findings 1–4 do not depend on it.

**Finding 6 — the TradingView *indicator*'s labels, scored for the first time
(2026-08-15).** The script drawing `CONFIRMED LONG/SHORT [A+]/[A]/[B]` labels
on the live chart is not in any repo — it exists only in TradingView, has never
been backtested, and is the only thing in the stack firing 1–2×/day. Seven
labels were transcribed **by hand from screenshots** of 12/13/14 Aug 2026
(provenance caveat: hand-keyed, not exported; and they are the setups Anupam
chose to screenshot, so selection runs in the strategy's favour).

The robust result needs no entry-bar identification: on **14 Aug**, SPY's RTH
range was 775.43–778.80, and *both* short labels — including the `[A+]`
captioned "All conditions perfect" — had **TP1 and TP2 below the entire
session's low**. 775.36 and 775.13 never traded. No entry timing or management
could have produced a winner from either.

Scoring the six with an identifiable RTH entry bar (matched on close = label
`E`; 1–5 candidate bars each, first taken): **1 win in 6, −1.83R total,
−0.30R average** — and the only winner was a `[B]`, the lowest grade in the
set, repeating the A-worse-than-B inversion ie-pro found on a different sample.
Two of the seven fired outside RTH entirely (04:40 PT premarket, ~14:30 PT
postmarket), when SPY 0DTE options do not trade at all.

n=7 is not a verdict on the indicator and is not treated as one. The real test
needs the Pine source exported from TradingView so it can go through the same
gates as r17/r18.

### 4. Straddle underpricing — HARNESS BUILT, first reading in (2026-08-16)
`src/straddle_test.py`. This is the question the lab was created to answer:
the timing U-shape is only an edge if realized movement exceeds what the
options market charges for it. Verdict 3 measured the charge; this measures
both sides at once.

**The test is exact, not modelled.** A straddle struck at K pays exactly
|close − K|. No Black–Scholes, no greeks, no vol surface — just the recorded
ask, the recorded strike, and the day's actual close. Buy the ATM 0DTE
straddle at each book, hold to expiry.

First reading, 17 usable sessions, 1,277 books:

| bucket (ET) | implied % | realized % | net $/straddle | t |
|---|---|---|---|---|
| 09:30–10:00 | 0.462 | 0.401 | −47.42 | −0.99 |
| 10:30–11:00 | 0.397 | 0.282 | −86.09 | −2.84 |
| 13:00–14:00 | 0.264 | 0.212 | −38.18 | −2.32 |
| 15:00–16:00 | 0.176 | 0.115 | −46.32 | −2.16 |
| **all** | | | **−43.10** | **−2.65** |

**Implied exceeds realized in all 8 time buckets, including the open.** The
U-shape is real and the market maker has already priced it: 0.462% charged
against 0.401% delivered in the first half hour. Direction so far:
**movement is OVERPRICED**. This agrees with verdict 3's payoff asymmetry
from a completely different angle — buying 0DTE premium is priced against you.

**Statistics are day-clustered, n = sessions.** Every book in a session
settles against the same close, so 1,277 books is 17 independent draws, not
1,277. The script computes on day-level means and refuses to print a verdict
under the 60-session gate.

**Tail warning, and it is the important part.** 4 of 17 sessions were
profitable; worst −$113, median −$59, best +$109; dropping the single best
session moves the mean from −43 to −53. A straddle loses a little most days
and pays hugely on the rare violent one, so *every quiet sample shows premium
as overpriced* — that is exactly how short-vol blowups get underwritten. This
sample has not seen a vol event. **"Overpriced" must not be read as "sell
premium"**; the desk is debit-only (`OPTIONS_PAPER.md`) for this reason and
Rule 4 bars live 0DTE regardless.

Re-run as sessions accumulate; the harness is finished and gated.

## Chain recorder + implied density engine (phase 2, built 2026-07-08)

`src/chain_recorder.py` snapshots the free CBOE delayed-quotes SPY chain
(no API key, ~15-min delay) every 5 minutes during RTH and appends today's
0DTE contracts within spot ±5% to `data/chains/SPY_YYYY-MM-DD.csv` — quotes,
sizes, IV, greeks, volume, OI (~150 contracts/snapshot). Free intraday chain
history is unobtainable retroactively; recording starts the clock. Guards:
RTH+weekday, stale-quote skip (holidays), gap-tolerant (every snapshot
independent). LIVE via launchd since 2026-07-16
(`~/Library/LaunchAgents/com.anupam.zerodte-recorder.plist`, fires every
5 min; the plist source is in `launchd/`).

launchd does not wake a sleeping Mac: snapshots only accumulate while the
lid is open. That's fine — the analysis treats each snapshot independently.

**Recording status (honest count, 2026-08-20): 20 usable full sessions** — counted by `session_count.py` (≥86% of a full session's rows; 5 stubs named in data/session_count.json), restating the 2026-08-04 figure of 9 —
(Jul 17, 20, 22, 24, 27–31) **against the 60-session gate.** Losses so far,
all machine-side, none of them the source's fault:

- **2026-08-03 — LOST.** 80 consecutive fetch failures 09:31–16:06 ET, every
  one `gaierror(8, 'nodename nor servname provided')` — the Mac could not
  resolve DNS all day (dead/upstream-less network; the box often rides an
  iPhone hotspot). No session file written. The old recorder logged each
  failure and did nothing else.
- **2026-07-23 — partial** (7 snapshots; same DNS error at the open, then
  sleep gaps). **2026-07-21 — partial** (13 snapshots; sleep gaps).

That is 2 of the last 9 trading days lost or gutted to machine network. Lost
days stay lost — the count above is not padded with partials.

Resilience patch (2026-08-04), recording behavior unchanged: each snapshot
now retries 3x with backoff (5s/20s) and a fresh DNS resolve + TCP/TLS
handshake per attempt; consecutive failures are counted across the 5-min
launchd relaunches in `data/chains/.recorder_state.json`; at 6 consecutive
failures (30 min dark) a dated `FAILURE_YYYY-MM-DD.txt` marker lands in
`data/chains/` — lost sessions are visibly lost, not silently absent — and
one full client re-init is attempted; after each close the log gets one
`SESSION SUMMARY date: N fetches ok, M failed` line. Sleep during RTH remains
a physical limit: on battery this Mac sleeps when idle (`pmset -g custom`:
Battery `sleep 1`, AC `sleep 0`), and launchd cannot fire through it — keep
the lid open on AC during market hours, or change the battery sleep setting
deliberately.

### Second leg: the cloud recorder (added 2026-08-11)

Capture, not code, is the binding constraint on the 60-session gate. The
honest window is **Jul 17 – Aug 11**, the 18 trading days since the agent was
actually loaded — not Jul 8, the date of a single hand-run test. `src/merge_chains.py
--report`, counted over the live window:

| | sessions |
|---|---|
| trading days since the agent went live | 18 |
| **usable (≥86% of the session's books)** | **14** |
| gutted (Jul 21: 9 books · Jul 23: 7 · Aug 4: 1) | 3 |
| entirely dark (Aug 3) | 1 |

**78% capture.** At that rate the 60-session gate lands around early November
2026.

A first draft of this section counted Jul 8 – Aug 11 instead, scored the
Jul 9–16 blank as lost sessions, blamed a shut lid, and reported 56% capture
and a January 2027 date. All of that was wrong. `~/crypto-microstructure`
ran its collector through that same stretch and logged **24 of 24 UTC hours on
Jul 10, 13, 14, 15 and 16** — the machine was awake and networked the whole
week. The plist was written Jul 9 but not loaded until Jul 16, so those days
were never being recorded and are not losses to count. A neighbouring lab's
data killed the diagnosis; the number came down from a two-month gain to about
three weeks.

**The dominant loss cause is network, not sleep.** Of the four bad sessions,
this README already attributes Aug 3 (80 consecutive `gaierror`), Aug 4, and
Jul 23's open to DNS death on the iPhone hotspot; only Jul 21 is a clean sleep
gap. The crypto collector corroborates independently — its two worst days in
38 are **Aug 3 (4 of 24 hours) and Aug 4 (11 of 24)**, the same two days,
which is what a machine-wide network outage looks like from a second lab and
not what sleep looks like.

That is a stronger argument for the cloud leg than sleep was, not a weaker
one: a GitHub runner has neither a lid nor a hotspot.

So the recorder now runs a second time, in `.github/workflows/chain-recorder.yml`,
on a GitHub runner every 10 min — awake or not, hotspot or not. It runs the
*identical* script (`--out-dir data/chains_ci`), so there is no second codebase
to keep honest, and it needs no dependencies: `chain_recorder.py` imports
stdlib only. The RTH and staleness guards stay the authority on what counts;
the cron only decides when to ask.

The two legs never write the same file. `src/merge_chains.py` unions them and
dedupes on the **CBOE book timestamp**, not the fetch time — both legs poll one
endpoint, so polls landing in the same ~5-min book return the same quotes under
two `fetched_at` values, and deduping on fetch time would double-count one
observation and inflate every row-based statistic here. Coverage is reported in
distinct book timestamps, never rows: row counts move with how many strikes sat
inside the ±5% band that day, which tracks realized vol, not capture.

Two honesty notes, both of which cap what this buys:

- **GitHub schedules are best-effort.** Documented to be delayed under load and
  dropped at high-load boundaries. The cloud leg is a *floor* on capture, not a
  guarantee. The laptop leg stays on at 5 min as the higher-resolution overlay.
- **The projection is a projection, and it is modest.** 46 usable sessions
  remain. At the measured 78% that is 59 more trading days (early November
  2026); *if* the cloud leg lands ≥95% it is 48 (mid-October) — about three
  weeks bought, not two months. That number gets replaced by the measured one,
  not defended: check the `rescued` column in the merge report, which counts
  books no lid-open recorder saw. It reads 0 until the cloud leg has run.

The real purchase is not the three weeks. It is that the sole copy of the
recording stops depending on one laptop's network: every cloud snapshot is
committed to GitHub as it is taken, whereas `data/chains/` is gitignored and
reaches Google Drive only on the Sunday sweep — on 2026-08-11 that backup was
current through Aug 7, leaving the Aug 10 and Aug 11 sessions single-copy.
For data this README calls unobtainable retroactively, that is the exposure
worth closing.

`src/implied_density.py` turns any snapshot into the market's implied
distribution for SPY at the close (Breeden–Litzenberger: second derivative
of the smile-interpolated call curve), plus the ATM-straddle implied move.
Verified on the first recorded snapshot (2026-07-08 pre-open, July-7-close
quotes): implied std 0.55%, straddle move ±0.49%, skew −1.22, density mass
1.008 — all sane. **The test that matters, once ~60+ days are recorded:
is realized open/close-window movement bigger than what the straddle
charges at the window start? Until that comparison is run, the timing
U-shape remains NOT an edge.**

## Layout

- `src/data_utils.py` — loaders (reads from `~/spy-trading/data`, ET/RTH)
- `src/timing_tester.py` — time-of-day big-move study
- `src/sweep_backtest.py` — r17 port: leaky vs causal vs no HTF filter
- `src/signal_cost.py` — option-space costing: break-even curve, payoff
  asymmetry, realized-outcome validation (verdict 3 above)
- `src/chain_recorder.py` — 0DTE chain snapshotter (CBOE delayed, free)
- `src/implied_density.py` — Breeden–Litzenberger density + straddle move
- `src/straddle_test.py` — the underpricing test (verdict 4), day-clustered
- `src/r19_log.py` — forward verdict log for the r19 checker
- `launchd/` — plist to schedule the recorder (opt-in, see above)
- `pine/r18_htf_fix.pine` — drop-in non-repainting fix for the TradingView script
- `results/` — CSVs + charts (`timing_profile.png`, `timing_heatmap.png`)
- `data/chains/` — recorded chains (gitignored; grows ~1 MB/day)

## Roadmap

1. ~~Timing tester~~ DONE (above)
2. ~~Chain recorder + implied density engine~~ BUILT (above) — now recording;
   the straddle-underpricing verdict needs ~60+ recorded sessions.
3. **Paper-trade journal + verdict engine** — forced pre-trade thesis, scored
   at the close against real bid/ask. Gate: no real money without positive
   expectancy after costs over 100+ paper trades.
4. Dashboard.

Known limitations: pseudo-OHLC bars understate wicks; BATS true-OHLC samples
are short (30 days / 4.5 months); worst-case intrabar fill assumption
(stop before target) is conservative by design.

## Self-learning agent

`agent/` holds a self-calibrating session agent (same pattern as `~/stock-radar`):
each morning with a fresh chain snapshot it logs at most two falsifiable calls to
`agent/ledger.csv` (close inside/outside the straddle implied move; max-pain pin
holds/breaks), scores them same-day at the close with no excuses, and appends blunt
takeaways to `agent/lessons.md`. **Honesty note:** calibration only, not trades —
no claim of edge; the 60+-session straddle-underpricing test remains the project's
real verdict. Procedure: `agent/AGENT.md`.

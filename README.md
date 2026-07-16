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

## Chain recorder + implied density engine (phase 2, built 2026-07-08)

`src/chain_recorder.py` snapshots the free CBOE delayed-quotes SPY chain
(no API key, ~15-min delay) every 5 minutes during RTH and appends today's
0DTE contracts within spot ±5% to `data/chains/SPY_YYYY-MM-DD.csv` — quotes,
sizes, IV, greeks, volume, OI (~150 contracts/snapshot). Free intraday chain
history is unobtainable retroactively; recording starts the clock. Guards:
RTH+weekday, stale-quote skip (holidays), gap-tolerant (every snapshot
independent). NOT YET SCHEDULED — to activate:

```
cp launchd/com.anupam.zerodte-recorder.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.anupam.zerodte-recorder.plist
```

launchd does not wake a sleeping Mac: snapshots only accumulate while the
lid is open. That's fine — the analysis treats each snapshot independently.

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
- `src/chain_recorder.py` — 0DTE chain snapshotter (CBOE delayed, free)
- `src/implied_density.py` — Breeden–Litzenberger density + straddle move
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

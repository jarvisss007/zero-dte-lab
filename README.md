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

- Big moves (top-decile |5-min return|) cluster **hard** at the open
  (09:35–10:00, up to 21.5% frequency vs 10% baseline) and the close
  (15:50–15:55), Bonferroni-significant. 10:25 also clears the bar.
- The six r17 windows as a pre-registered group: 12.3% big-move frequency vs
  10% baseline (p=0.002). Real but modest, and driven almost entirely by the
  09:45 and 10:00 windows; 11:20 and 13:45 add nothing.
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

## Layout

- `src/data_utils.py` — loaders (reads from `~/spy-trading/data`, ET/RTH)
- `src/timing_tester.py` — time-of-day big-move study
- `src/sweep_backtest.py` — r17 port: leaky vs causal vs no HTF filter
- `pine/r18_htf_fix.pine` — drop-in non-repainting fix for the TradingView script
- `results/` — CSVs + charts (`timing_profile.png`, `timing_heatmap.png`)

## Roadmap

1. ~~Timing tester~~ DONE (above)
2. **Chain recorder + implied density engine** — archive intraday 0DTE option
   chains (free data is unobtainable retroactively; recording starts the
   clock), extract Breeden–Litzenberger implied distributions, and test
   whether the open/close vol windows are UNDERPRICED by 0DTE straddles.
   This is the only version of the timing thesis that can make money.
3. **Paper-trade journal + verdict engine** — forced pre-trade thesis, scored
   at the close against real bid/ask. Gate: no real money without positive
   expectancy after costs over 100+ paper trades.
4. Dashboard.

Known limitations: pseudo-OHLC bars understate wicks; BATS true-OHLC samples
are short (30 days / 4.5 months); worst-case intrabar fill assumption
(stop before target) is conservative by design.

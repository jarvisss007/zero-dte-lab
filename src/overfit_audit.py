#!/usr/bin/env python3
"""
Run my own r17 sweep through the backtest-overfitting toolkit.

The sweep (sweep_backtest.py) tried 6 configs per dataset (3 HTF-bias variants x 2
direction modes) on 3 datasets. Question: if I had simply picked the best-looking
config, would that selection survive deflation (DSR) and CSCV (PBO)?

For each dataset this script rebuilds every config's trade list, buckets trade R
into daily P&L (days with no trade = 0 for all configs — a shared flat day), and
runs overfit.analyze() on the resulting T x N matrix.

Output: results/overfit_audit.txt (+ printed report).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.home() / "backtest-overfitting"))
import overfit                                    # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweep_backtest import (                      # noqa: E402
    RESULTS, build_signals, htf_bias, load_bats, load_minute_closes,
    minute_to_pseudo_ohlc, run,
)


def daily_matrix(df: pd.DataFrame, htf: str) -> tuple[pd.DataFrame, list[str]]:
    """Rebuild all 6 configs for one dataset -> daily R matrix (T days x 6)."""
    variants = {
        "LEAKY(r17)": htf_bias(df, htf, leaky=True),
        "causal": htf_bias(df, htf, leaky=False),
        "no-HTF": pd.DataFrame({"bull": True, "bear": True}, index=df.index),
    }
    cols = {}
    for vname, hb in variants.items():
        sigs = build_signals(df, hb)
        for dirname, (al, ash) in {"short": (False, True), "both": (True, True)}.items():
            trades = run(sigs, al, ash)
            name = f"{vname}|{dirname}"
            if trades:
                s = pd.Series([t.r for t in trades],
                              index=[t.ts.normalize() for t in trades])
                cols[name] = s.groupby(level=0).sum()
            else:
                cols[name] = pd.Series(dtype=float)
    # union of all trade days; a day any config traded is a row, others get 0
    mat = pd.DataFrame(cols).sort_index().fillna(0.0)
    mat = mat.loc[:, mat.std() > 0]               # drop configs that never traded
    return mat, list(mat.columns)


def main() -> None:
    datasets = {
        "BATS 5-min true OHLC (Jul-Aug 2025)": (load_bats("5"), "15min"),
        "BATS 15-min true OHLC (Sep24-Jan25)": (load_bats("15"), "60min"),
        "pseudo 5-min from closes (Aug24-Nov25)": (
            minute_to_pseudo_ohlc(load_minute_closes()), "15min"),
    }
    lines = ["OVERFITTING AUDIT of the r17 sweep (see sweep_backtest.py)",
             "Selection rule audited: 'pick the config with the best in-sample Sharpe'",
             ""]
    for dname, (df, htf) in datasets.items():
        mat, names = daily_matrix(df, htf)
        T, N = mat.shape
        if N < 2 or T < 30:
            lines += [f"== {dname} ==", f"   skipped (only {N} active configs / {T} days)", ""]
            continue
        rep = overfit.analyze(mat.to_numpy(), periods_per_year=252,
                              n_splits=min(16, max(4, (T // 15) * 2 // 2 * 2)))
        best = names[rep["best_strategy"]]
        lines += [
            f"== {dname} ==",
            f"   {N} configs x {T} trade days · best in-sample: {best}",
            f"   best annual Sharpe (in-sample):  {rep['best_sharpe_annual']:+.2f}",
            f"   Deflated Sharpe (DSR):           {rep['dsr']:.3f}   "
            f"(P[true SR>0 after {N}-trial selection]; want > 0.95)",
            f"   PBO (CSCV):                      {rep['pbo']:.2f}   "
            f"(P[IS-best ranks below median OOS]; want < 0.5)",
            f"   P(OOS loss of IS-best):          {rep['prob_oos_loss']:.2f}",
            f"   IS->OOS degradation slope:       {rep['degradation']:+.2f}",
            f"   min backtest length for this N:  {rep['min_backtest_length_years']:.1f} years",
            f"   VERDICT: {rep['verdict']}",
            "",
        ]
    report = "\n".join(lines)
    print(report)
    (RESULTS / "overfit_audit.txt").write_text(report + "\n")
    print(f"saved -> {RESULTS / 'overfit_audit.txt'}")


if __name__ == "__main__":
    main()

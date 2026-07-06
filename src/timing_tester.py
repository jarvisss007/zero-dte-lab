"""Timing-thesis tester: do big SPY moves cluster at particular times of day?

Data: 15 months of 1-min closes (Aug 2024 - Nov 2025) from ~/spy-trading.

Method
------
1. Build non-overlapping 5-min returns, bucketed by ET time of day (78/day).
2. Per bucket: realized vol of the 5-min return, and frequency of "big moves"
   (|5-min return| in the top decile of ALL 5-min returns, threshold computed
   over the whole sample so buckets are comparable).
3. Big-move frequency per bucket is tested against the 10% baseline with a
   two-sided binomial test, Bonferroni-corrected for 78 comparisons.
4. The six r17 windows (0945, 1000, 1045, 1120, 1345, 1520) are scored
   separately as a pre-registered GROUP, which is the fair test of the thesis
   r17's windows encode - one test, no cherry-picking.
5. Day-of-week x time heat map for the eyeball check.

Run: /opt/anaconda3/bin/python src/timing_tester.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from data_utils import load_minute_closes, ET

RESULTS = Path(__file__).resolve().parent.parent / "results"
BIG_Q = 0.90  # "big move" = top decile of |5-min return|

# Anupam trades on Pacific time (6:30-13:00). The r17 Pine windows are
# AMBIGUOUS: Pine's time() uses the exchange tz (ET), but the windows may
# have been derived from PT logs. Test both readings.
R17_WINDOWS_ET = ["09:45", "10:00", "10:45", "11:20", "13:45", "15:20"]
# same wall-clock numbers read as PT, mapped to ET (13:45/15:20 PT are
# after the close and cannot be windows, so only four map):
R17_WINDOWS_PT_AS_ET = ["12:45", "13:00", "13:45", "14:20"]


def five_min_returns(minutes: pd.DataFrame) -> pd.DataFrame:
    m = minutes.set_index("ts")["close"]
    c = m.resample("5min", label="left", closed="left").last().dropna()
    r = c.pct_change()
    df = r.to_frame("ret").reset_index()
    # drop overnight: first bucket of each session has the prior-close change
    df["date"] = df["ts"].dt.date
    df = df[df["date"] == df["date"].shift()].dropna()
    t = df["ts"].dt
    keep = ((t.hour * 60 + t.minute) >= 9 * 60 + 35) & \
           ((t.hour * 60 + t.minute) < 16 * 60) & (t.dayofweek < 5)
    df = df[keep].copy()
    df["bucket"] = df["ts"].dt.strftime("%H:%M")
    df["bucket_pt"] = df["ts"].dt.tz_convert(
        "America/Los_Angeles").dt.strftime("%H:%M")
    df["dow"] = df["ts"].dt.day_name()
    return df


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    minutes = load_minute_closes()
    df = five_min_returns(minutes)
    n_days = df["date"].nunique()
    thresh = df["ret"].abs().quantile(BIG_Q)
    df["big"] = df["ret"].abs() >= thresh

    print(f"{len(df):,} five-min returns over {n_days} sessions "
          f"({df['ts'].min():%Y-%m-%d} -> {df['ts'].max():%Y-%m-%d})")
    print(f"big-move threshold (top {100*(1-BIG_Q):.0f}%): "
          f"|5-min ret| >= {thresh*100:.3f}%\n")

    # ---- per-bucket stats + Bonferroni binomial test --------------------
    g = df.groupby("bucket")
    per = pd.DataFrame({
        "n": g.size(),
        "vol_bp": g["ret"].std() * 1e4,
        "mean_abs_bp": g["ret"].apply(lambda s: s.abs().mean()) * 1e4,
        "big_freq": g["big"].mean(),
    })
    base = 1 - BIG_Q
    per["p_raw"] = [
        stats.binomtest(int(row.big_freq * row.n), int(row.n), base).pvalue
        for row in per.itertuples()]
    n_tests = len(per)
    per["signif"] = per["p_raw"] * n_tests < 0.05  # Bonferroni
    per = per.sort_index()

    sig = per[per["signif"]].sort_values("big_freq", ascending=False)
    print("Buckets with big-move frequency significantly != 10% baseline")
    print("(two-sided binomial, Bonferroni x78):")
    with pd.option_context("display.float_format", "{:.3f}".format):
        print(sig[["n", "vol_bp", "big_freq", "p_raw"]].to_string())

    # ---- pre-registered group tests: r17 windows, both tz readings ------
    for label, wins in [("read as ET (what Pine tested)", R17_WINDOWS_ET),
                        ("read as PT (Anupam's clock)", R17_WINDOWS_PT_AS_ET)]:
        r17 = df[df["bucket"].isin(wins)]
        rest = df[~df["bucket"].isin(wins)]
        k, n = int(r17["big"].sum()), len(r17)
        p_group = stats.binomtest(k, n, base).pvalue
        mw = stats.mannwhitneyu(r17["ret"].abs(), rest["ret"].abs()).pvalue
        print(f"\nr17 windows {label}: {n} obs, big-move freq "
              f"{k/n:.3f} vs baseline {base:.3f} (p={p_group:.4f}); "
              f"mean |ret| {r17['ret'].abs().mean()*1e4:.2f} bp vs rest "
              f"{rest['ret'].abs().mean()*1e4:.2f} bp (MW p={mw:.4f})")

    pt_map = df.drop_duplicates("bucket").set_index("bucket")["bucket_pt"]
    per["bucket_pt"] = pt_map.reindex(per.index)
    per.to_csv(RESULTS / "timing_buckets.csv")

    # ---- plots -----------------------------------------------------------
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=False)
    x = np.arange(len(per))
    colors = ["#c0392b" if b in R17_WINDOWS_ET
              else ("#2980b9" if s else "#95a5a6")
              for b, s in zip(per.index, per["signif"])]
    axes[0].bar(x, per["vol_bp"], color=colors)
    axes[0].set_title("SPY realized vol by 5-min bucket (bp per 5 min) — "
                      "red = r17 windows (ET reading), "
                      "blue = significant big-move buckets")
    axes[0].axhline(per["vol_bp"].median(), ls="--", c="k", lw=0.8)
    axes[1].bar(x, per["big_freq"] * 100, color=colors)
    axes[1].axhline(10, ls="--", c="k", lw=0.8, label="10% baseline")
    axes[1].set_title("Big-move frequency by bucket (%)")
    axes[1].legend()
    ticklab = [f"{pt} PT" for pt in per["bucket_pt"][::6]]
    for ax in axes:
        ax.set_xticks(x[::6])
        ax.set_xticklabels(ticklab, rotation=45)
    fig.tight_layout()
    fig.savefig(RESULTS / "timing_profile.png", dpi=140)

    # day-of-week x hour heat map of mean |ret|
    df["hour"] = df["ts"].dt.tz_convert("America/Los_Angeles").dt.strftime("%H:00")
    pivot = df.pivot_table(index="dow", columns="hour", values="ret",
                           aggfunc=lambda s: s.abs().mean()) * 1e4
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    pivot = pivot.reindex(order)
    fig2, ax2 = plt.subplots(figsize=(9, 4))
    im = ax2.imshow(pivot.values, aspect="auto", cmap="magma")
    ax2.set_xticks(range(len(pivot.columns)), pivot.columns)
    ax2.set_yticks(range(len(pivot.index)), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax2.text(j, i, f"{pivot.values[i, j]:.1f}", ha="center",
                     va="center", color="w", fontsize=8)
    ax2.set_title("Mean |5-min return| (bp), day of week x hour PT")
    fig2.colorbar(im)
    fig2.tight_layout()
    fig2.savefig(RESULTS / "timing_heatmap.png", dpi=140)
    print(f"\nwrote results/timing_profile.png, timing_heatmap.png, "
          f"timing_buckets.csv")


if __name__ == "__main__":
    main()

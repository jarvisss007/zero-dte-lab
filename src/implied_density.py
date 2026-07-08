"""Breeden-Litzenberger implied density from recorded 0DTE chains (phase 2).

Reads a chain_recorder.py daily CSV, picks the snapshot nearest a requested
ET time, fits the IV smile from OTM quotes, and differentiates twice to get
the market's implied density for SPY at that day's close:

    f(K) = e^{rT} * d2C/dK2          (Breeden & Litzenberger 1978)

Also reports the ATM-straddle implied move — the number the eventual
timing-thesis test needs: is realized open/close-window movement bigger than
what 0DTE straddles charge? One snapshot per day at the window start,
compared to the realized move, answers it once enough days are recorded.

Construction notes (honesty):
  - Delayed quotes (~15 min): fine for research, useless for execution.
  - OTM side only (puts below forward, calls above), mids of live two-sided
    quotes, CBOE IVs sanity-filtered; cubic-spline smile in IV space.
  - Forward from put-call parity at the strike where |C - P| is smallest.
  - The density integrates to ~1 only within the recorded +/-5% strike band;
    tail mass beyond the band is reported, not hidden.

Run: /opt/anaconda3/bin/python src/implied_density.py data/chains/SPY_2026-07-08.csv \
        [--time 09:35] [--plot]
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.stats import norm

RESULTS = Path(__file__).resolve().parent.parent / "results"
R = 0.04  # short rate; T is hours so the discounting is ~irrelevant


def bs_call(F, K, T, iv):
    """Vectorized undiscounted Black-76 call. Callers guarantee T>0, iv>0."""
    d1 = (np.log(F / K) + 0.5 * iv**2 * T) / (iv * np.sqrt(T))
    d2 = d1 - iv * np.sqrt(T)
    return F * norm.cdf(d1) - K * norm.cdf(d2)


def load_snapshot(path: str, at: str | None):
    df = pd.read_csv(path)
    snaps = sorted(df["fetched_at_et"].unique())
    if at is None:
        pick = snaps[-1]
    else:
        target = pd.Timestamp(f"{df['expiry'].iloc[0]} {at}")
        pick = min(snaps, key=lambda s: abs(pd.Timestamp(s) - target))
    return df[df["fetched_at_et"] == pick].copy(), pick, len(snaps)


def implied_density(snap: pd.DataFrame):
    live = snap[(snap["bid"] > 0) & (snap["ask"] > 0)].copy()
    live["mid"] = (live["bid"] + live["ask"]) / 2
    calls = live[live["type"] == "C"].set_index("strike").sort_index()
    puts = live[live["type"] == "P"].set_index("strike").sort_index()
    both = calls.join(puts, lsuffix="_c", rsuffix="_p", how="inner")
    if both.empty:
        raise SystemExit("no strikes with live two-sided C and P quotes")

    # forward via parity at the strike where C and P are closest
    k0 = (both["mid_c"] - both["mid_p"]).abs().idxmin()
    fwd = k0 + both.loc[k0, "mid_c"] - both.loc[k0, "mid_p"]

    # expiry 16:00 ET; T in years from snapshot time
    ts = pd.Timestamp(snap["fetched_at_et"].iloc[0])
    expiry = pd.Timestamp(f"{snap['expiry'].iloc[0]} 16:00:00")
    T = max((expiry - ts).total_seconds(), 60.0) / (365.0 * 24 * 3600)

    # OTM smile in IV space
    otm = pd.concat([
        puts[puts.index < fwd], calls[calls.index >= fwd]
    ])
    otm = otm[(otm["iv"] > 0.01) & (otm["iv"] < 5.0)]
    otm = otm[~otm.index.duplicated()].sort_index()
    if len(otm) < 8:
        raise SystemExit(f"only {len(otm)} usable OTM quotes; smile unfit")
    smile = CubicSpline(otm.index.values, otm["iv"].values)

    kgrid = np.linspace(otm.index.min(), otm.index.max(), 2000)
    c = bs_call(fwd, kgrid, T, np.clip(smile(kgrid), 0.005, 5.0))
    dens = np.exp(R * T) * np.gradient(np.gradient(c, kgrid), kgrid)
    dens = np.clip(dens, 0, None)

    mass = np.trapezoid(dens, kgrid)
    mean = np.trapezoid(kgrid * dens, kgrid) / mass
    var = np.trapezoid((kgrid - mean) ** 2 * dens, kgrid) / mass
    std = np.sqrt(var)
    skew = np.trapezoid((kgrid - mean) ** 3 * dens, kgrid) / mass / std**3

    # ATM straddle implied move
    k_atm = both.index[np.argmin(np.abs(both.index.values - fwd))]
    straddle = both.loc[k_atm, "mid_c"] + both.loc[k_atm, "mid_p"]

    return {
        "snapshot": str(ts), "spot": snap["spot"].iloc[0], "forward": fwd,
        "T_hours": T * 365 * 24, "n_otm_quotes": len(otm),
        "band_mass": mass, "implied_mean": mean, "implied_std": std,
        "implied_skew": skew, "atm_strike": k_atm, "straddle_mid": straddle,
        "straddle_move_pct": straddle / fwd * 100,
        "kgrid": kgrid, "density": dens / mass,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="daily chain CSV from chain_recorder.py")
    ap.add_argument("--time", default=None, help="ET time HH:MM (default: last)")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    snap, picked, n = load_snapshot(args.csv, args.time)
    d = implied_density(snap)

    print(f"file: {args.csv}  ({n} snapshots; using {picked})")
    print(f"spot {d['spot']:.2f}  forward {d['forward']:.2f}  "
          f"T = {d['T_hours']:.2f} h  ({d['n_otm_quotes']} OTM quotes)")
    print(f"implied close distribution: mean {d['implied_mean']:.2f}, "
          f"std {d['implied_std']:.2f} ({d['implied_std']/d['forward']*100:.2f}%), "
          f"skew {d['implied_skew']:+.2f}  [in-band mass {d['band_mass']:.3f}]")
    print(f"ATM {d['atm_strike']:.0f} straddle mid {d['straddle_mid']:.2f} "
          f"=> implied move +/-{d['straddle_move_pct']:.2f}% by the close")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        RESULTS.mkdir(exist_ok=True)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(d["kgrid"], d["density"])
        ax.axvline(d["forward"], ls="--", lw=1, label=f"fwd {d['forward']:.1f}")
        ax.set_xlabel("SPY at close")
        ax.set_ylabel("implied density")
        ax.set_title(f"SPY 0DTE implied density  {d['snapshot']}")
        ax.legend()
        day = snap["expiry"].iloc[0]
        out = RESULTS / f"implied_density_{day}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"plot -> {out}")


if __name__ == "__main__":
    main()

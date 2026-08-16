"""The straddle-underpricing test — this lab's central question.

`timing_tester.py` found that big SPY moves cluster at the open and the close
(the textbook intraday U-shape) and the README has said, since 2026-07-06:

    Elevated realized movement is NOT an edge until shown to exceed what the
    options market charges for it at those times.

`signal_cost.py` measured the CHARGE side in 2026-08-15. This measures the
other side: buy the ATM 0DTE straddle at time T and hold it to expiry. It pays
|close - K| and costs what the book actually asked. If realized movement
exceeds the price of movement, that difference is where an edge would live.

THE TEST IS EXACT, NOT MODELLED
    A straddle struck at K pays exactly |S_close - K| at expiry. There is no
    Black-Scholes, no greeks, no vol surface, no early-exercise assumption -
    just the recorded ask, the recorded strike, and the day's actual close.
    That makes this the cleanest measurement in the repo.

THE SAMPLE IS THE PROBLEM, NOT THE METHOD
    Books inside one session are NOT independent observations: they all settle
    against the same close. 76 books on one day is one draw, not 76. Every
    statistic here is therefore computed on DAY-LEVEL means with n = sessions,
    never on book counts. With 17 usable sessions the confidence interval is
    wide enough to contain almost anything, which is exactly why the README
    set a 60-session gate. This script prints the reading and refuses to call
    it a verdict until that gate is met.

DIRECTION OF THE ANSWER
    net > 0  -> movement is underpriced; buying premium is where to look
    net < 0  -> movement is overpriced; the edge (if any) is on the sell side,
                which the desk has ruled out (OPTIONS_PAPER.md, debit-only)
    In both cases Constitution Rule 4 bars trading 0DTE live. This is research.

Run: /opt/anaconda3/bin/python src/straddle_test.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from signal_cost import (load_books, load_spy_5m, session_quality,  # noqa: E402
                         _pick, MIN_BOOKS, CONTRACT, TIME_BINS, TIME_LABELS)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
GATE = 60          # sessions required before this is called a verdict


def session_closes(spy: pd.DataFrame) -> dict:
    """Actual RTH close per session (16:00 ET), not the last recorded book."""
    t = spy["ts"].dt.hour * 60 + spy["ts"].dt.minute
    rth = spy[(t >= 570) & (t < 960)]
    return {d: float(g["close"].iloc[-1])
            for d, g in rth.groupby(rth["ts"].dt.date)}


def run(books: pd.DataFrame, closes: dict) -> pd.DataFrame:
    """One row per (session, book): cost of the ATM straddle vs what it paid."""
    rows = []
    for date, day in books.groupby("date"):
        if day["quote_ts"].nunique() < MIN_BOOKS or date not in closes:
            continue
        close_px = closes[date]
        for t0 in np.sort(day["quote_ts"].unique()):
            b = day[day["quote_ts"] == t0]
            spot = float(b["spot"].iloc[0])
            c = _pick(b, "C", spot, 0)
            p = _pick(b, "P", spot, 0)
            if c is None or p is None:
                continue
            K = float(c["strike"])
            if float(p["strike"]) != K:
                continue
            ask = float(c["ask"]) + float(p["ask"])      # marketable cost
            mid = (float(c["ask"]) + float(c["bid"])) / 2 + \
                  (float(p["ask"]) + float(p["bid"])) / 2
            if ask <= 0:
                continue
            payoff = abs(close_px - K)                   # exact expiry value
            ts = pd.Timestamp(t0)
            rows.append({
                "date": date, "quote_ts": ts,
                "minute": ts.hour * 60 + ts.minute,
                "strike": K, "spot": spot, "close": close_px,
                "cost_ask": ask, "cost_mid": mid, "payoff": payoff,
                "net_ask": payoff - ask, "net_mid": payoff - mid,
                "ret_ask_pct": (payoff - ask) / ask * 100,
                "implied_move_pct": ask / spot * 100,
                "realized_move_pct": payoff / spot * 100,
            })
    d = pd.DataFrame(rows)
    if not d.empty:
        d["bucket"] = pd.cut(d["minute"], bins=TIME_BINS, labels=TIME_LABELS)
    return d


def day_clustered(d: pd.DataFrame, col: str) -> tuple:
    """Mean and t-stat with n = SESSIONS. Books in a day share one close."""
    per_day = d.groupby("date")[col].mean()
    n = len(per_day)
    if n < 2:
        return per_day.mean() if n else np.nan, np.nan, n
    m = per_day.mean()
    se = per_day.std(ddof=1) / np.sqrt(n)
    return m, (m / se if se > 0 else np.nan), n


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    print("=" * 78)
    print("STRADDLE-UNDERPRICING TEST — is realized movement worth its price?")
    print("=" * 78)

    books = load_books()
    q = session_quality(books)
    spy = load_spy_5m()
    closes = session_closes(spy)
    d = run(books, closes)

    if d.empty:
        print("\nNo usable sessions yet.")
        return

    n_sess = d["date"].nunique()
    print(f"\nusable sessions: {n_sess}   gate: {GATE}   "
          f"books priced: {len(d)}")
    print("Buy the ATM 0DTE straddle at each book, hold to expiry.")
    print("Payoff |close - K| is exact; cost is the recorded ask.\n")

    for col, name in (("net_ask", "at the ASK (what you would pay)"),
                      ("net_mid", "at the MID (unreachable, upper bound)")):
        m, t, n = day_clustered(d, col)
        print(f"{name}:")
        print(f"   mean net {m * CONTRACT:+.2f} $/straddle   "
              f"t = {t:+.2f} on n = {n} sessions")

    print("\nBy time of day (net at ask, $/straddle, day-clustered):")
    rows = []
    for bk, g in d.groupby("bucket", observed=True):
        m, t, n = day_clustered(g, "net_ask")
        rows.append({
            "bucket": bk, "sessions": n, "books": len(g),
            "implied_%": round(g["implied_move_pct"].mean(), 3),
            "realized_%": round(g["realized_move_pct"].mean(), 3),
            "net_$": round(m * CONTRACT, 2),
            "t": round(t, 2) if np.isfinite(t) else np.nan,
        })
    print(pd.DataFrame(rows).to_string(index=False))

    # ── Tail panel. A straddle's payoff is one-sided and fat-tailed: it loses
    # a little most days and pays hugely on the rare violent one. That means
    # ANY sample without a vol event shows premium as overpriced, which is
    # precisely how short-vol blowups are underwritten. Show the dependence.
    per_day = d.groupby("date")["net_ask"].mean().sort_values()
    print("\nTail dependence (per-session mean net, $/straddle):")
    print(f"   sessions profitable: {(per_day > 0).sum()} of {len(per_day)}")
    print(f"   worst {per_day.iloc[0] * CONTRACT:+.0f}   "
          f"median {per_day.median() * CONTRACT:+.0f}   "
          f"best {per_day.iloc[-1] * CONTRACT:+.0f}")
    if len(per_day) > 1:
        wo_best = per_day.iloc[:-1].mean() * CONTRACT
        print(f"   mean excluding the single best session: {wo_best:+.2f}")
        print("   -> if dropping ONE day moves this a lot, the sample has not")
        print("      seen a vol event and the sign cannot be trusted.")

    m, t, n = day_clustered(d, "net_ask")
    print("\n" + "-" * 78)
    if n < GATE:
        print(f"READING, NOT A VERDICT. {n} of {GATE} sessions.")
        print("Books within a session settle against the same close, so the")
        print("honest sample size is sessions, not books. At this n the")
        print("interval is far too wide to conclude anything - the sign below")
        print("is a direction to watch, not a finding.")
        print(f"   direction so far: {'UNDERPRICED' if m > 0 else 'OVERPRICED'} "
              f"({m * CONTRACT:+.2f} $/straddle, t = {t:+.2f})")
    elif not np.isfinite(t) or abs(t) < 2:
        print("VERDICT: no separation. Realized movement is priced fairly; the")
        print("timing U-shape is NOT an edge. This closes the lab's question.")
    elif m > 0:
        print("VERDICT: movement is UNDERPRICED at these times. Run this past")
        print("the edge-refute panel and the deflation/PBO gate before it goes")
        print("anywhere near a README claim or a trade.")
    else:
        print("VERDICT: movement is OVERPRICED. Any edge is on the sell side,")
        print("which the desk has ruled out (debit-only, OPTIONS_PAPER.md).")
    print("\nDO NOT READ 'OVERPRICED' AS 'SELL PREMIUM'. Short straddles carry")
    print("unbounded loss and every quiet sample flatters them; see the tail")
    print("panel above. The desk is debit-only for this exact reason, and")
    print("Constitution Rule 4 bars live 0DTE regardless of this result.")
    print("-" * 78)

    d.to_csv(RESULTS / "straddle_test.csv", index=False)
    print("\nwrote results/straddle_test.csv")


if __name__ == "__main__":
    main()

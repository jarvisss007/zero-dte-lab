"""r19 verdict log — the forward record that decides whether the veto is worth it.

r19 (`pine/r19_checker.pine`) vetoes setups that cannot pay 1.5R in a 0DTE
contract. On the only sample that exists so far — 7 labels hand-scored from
screenshots — it cleared 2 setups that both lost and rejected the one winner
by 0.04. That is n=7 and means nothing in either direction, but it is also the
only evidence the tool has, and it is not evidence in its favour.

This file is how that changes. Log every setup you SEE, whether or not you
take it, along with what r19 said. Fill in the outcome later. After enough
rows, `score` answers the only question that matters:

    do setups r19 CLEARS outperform the ones it FAILS?

If they do not, r19 is decoration and should be deleted. The log is built to
be able to say that.

Logging the ones you skip is the whole point. A log of only-taken trades
cannot compare cleared against failed, which is exactly the comparison that
falsifies the tool.

Usage
-----
  python src/r19_log.py add --side short --e 776.00 --sl 776.86 --tp 774.72 \
      --at "2026-08-14 11:20" --source indicator --took no
  python src/r19_log.py outcome --id 3 --exit 776.86 --note "stopped"
  python src/r19_log.py score

Times are EXCHANGE time (ET), matching the Pine script and the chain data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "r19_log.csv"
TABLE = ROOT / "results" / "rule1_option_space.csv"

COLS = ["id", "logged_at", "at", "source", "side", "E", "SL", "TP", "hold",
        "rr_real", "rr_needed", "verdict", "took", "exit", "R", "note"]

BUCKETS = [(600, "09:30-10:00"), (630, "10:00-10:30"), (660, "10:30-11:00"),
           (720, "11:00-12:00"), (780, "12:00-13:00"), (840, "13:00-14:00"),
           (900, "14:00-15:00"), (960, "15:00-16:00")]


def bucket_of(minutes: int) -> str:
    for cut, name in BUCKETS:
        if minutes < cut:
            return name
    return BUCKETS[-1][1]


def required_mult(stop_pts: float, minutes: int, hold: int = 30,
                  rr: float = 1.5) -> float:
    """Interpolate the measured Rule-1 table. Same math as the Pine f_reqMult."""
    if not TABLE.exists():
        raise SystemExit(f"missing {TABLE} — run: python src/signal_cost.py")
    t = pd.read_csv(TABLE)
    row = t[(t["hold_min"] == hold) & (t["bucket"] == bucket_of(minutes))]
    if row.empty or row["req_mult"].isna().all():
        return np.nan
    row = row.sort_values("stop_pts")
    m = float(np.interp(max(stop_pts, 0.05),
                        row["stop_pts"].to_numpy(), row["req_mult"].to_numpy()))
    return m * rr / 1.5


def _load() -> pd.DataFrame:
    if LOG.exists():
        return pd.read_csv(LOG)
    return pd.DataFrame(columns=COLS)


def _save(df: pd.DataFrame) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LOG, index=False)


def cmd_add(a) -> None:
    ts = pd.Timestamp(a.at)
    mins = ts.hour * 60 + ts.minute
    stop = abs(a.e - a.sl)
    tgt = abs(a.tp - a.e)
    if stop <= 0:
        raise SystemExit("stop distance must be > 0")
    rr = tgt / stop
    need = required_mult(stop, mins, a.hold)

    in_sess = 575 <= mins <= 930
    if not in_sess:
        verdict = "FAIL:session"
    elif np.isnan(need):
        verdict = "FAIL:no-hold-room"
    elif rr >= need:
        verdict = "CLEARS"
    else:
        verdict = "FAIL:rule1"

    df = _load()
    new = {
        "id": (int(df["id"].max()) + 1) if len(df) else 1,
        "logged_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "at": a.at, "source": a.source, "side": a.side.lower(),
        "E": a.e, "SL": a.sl, "TP": a.tp, "hold": a.hold,
        "rr_real": round(rr, 2),
        "rr_needed": "" if np.isnan(need) else round(need, 2),
        "verdict": verdict, "took": a.took, "exit": "", "R": "", "note": a.note,
    }
    row = pd.DataFrame([new])
    _save(row if df.empty else pd.concat([df, row], ignore_index=True))
    print(f"#{new['id']}  {verdict}   RR {rr:.2f} vs needed "
          f"{'n/a' if np.isnan(need) else f'{need:.2f}'}   ({bucket_of(mins)})")


def cmd_outcome(a) -> None:
    df = _load()
    if df.empty or a.id not in set(df["id"]):
        raise SystemExit(f"no row #{a.id}")
    i = df.index[df["id"] == a.id][0]
    E, SL = float(df.at[i, "E"]), float(df.at[i, "SL"])
    side = str(df.at[i, "side"])
    R = (E - a.exit) / (SL - E) if side == "short" else (a.exit - E) / (E - SL)
    df.at[i, "exit"] = a.exit
    df.at[i, "R"] = round(R, 2)
    if a.note:
        df.at[i, "note"] = a.note
    _save(df)
    print(f"#{a.id}  exit {a.exit}  ->  {R:+.2f}R")


def cmd_score(a) -> None:
    df = _load()
    if df.empty:
        print("log is empty — nothing to score yet.")
        return
    done = df[pd.to_numeric(df["R"], errors="coerce").notna()].copy()
    done["R"] = done["R"].astype(float)
    print(f"logged {len(df)}   resolved {len(done)}   "
          f"open {len(df) - len(done)}\n")
    if done.empty:
        print("No resolved rows yet. Fill outcomes with: r19_log.py outcome")
        return

    done["gate"] = np.where(done["verdict"] == "CLEARS", "CLEARS", "FAILS")
    g = done.groupby("gate")["R"].agg(n="size", avg_R="mean", total_R="sum",
                                      win_rate=lambda s: (s > 0).mean() * 100)
    print(g.round(2).to_string())

    if {"CLEARS", "FAILS"} <= set(g.index) and g.loc["CLEARS", "n"] >= 2 \
            and g.loc["FAILS", "n"] >= 2:
        c, f = done[done.gate == "CLEARS"]["R"], done[done.gate == "FAILS"]["R"]
        diff = c.mean() - f.mean()
        se = np.sqrt(c.var(ddof=1) / len(c) + f.var(ddof=1) / len(f))
        t = diff / se if se > 0 else np.nan
        print(f"\nCLEARS - FAILS = {diff:+.3f}R   t = {t:+.2f}   "
              f"(n {len(c)} vs {len(f)})")
        if len(done) < 40:
            print("VERDICT: too few rows to conclude anything. Keep logging.")
        elif not np.isfinite(t) or abs(t) < 2:
            print("VERDICT: no separation. On this evidence r19's veto is "
                  "decoration — consider deleting it.")
        elif t > 0:
            print("VERDICT: cleared setups outperform. The veto is earning "
                  "its place. Still not an edge — it is a cost filter.")
        else:
            print("VERDICT: cleared setups UNDERPERFORM. The gate is "
                  "backwards or the table is stale. Stop using it.")
    else:
        print("\nNeed >= 2 resolved rows on BOTH sides to compare. Log the "
              "setups you skip, not just the ones you take.")


def main() -> None:
    p = argparse.ArgumentParser(description="r19 verdict log")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="log a setup you saw")
    a.add_argument("--side", required=True, choices=["long", "short", "Long", "Short"])
    a.add_argument("--e", type=float, required=True, help="entry")
    a.add_argument("--sl", type=float, required=True, help="stop")
    a.add_argument("--tp", type=float, required=True, help="target (the real one)")
    a.add_argument("--at", required=True, help='signal time ET, "YYYY-MM-DD HH:MM"')
    a.add_argument("--hold", type=int, default=30, choices=[15, 30, 60])
    a.add_argument("--source", default="indicator")
    a.add_argument("--took", default="no", choices=["yes", "no"])
    a.add_argument("--note", default="")
    a.set_defaults(func=cmd_add)

    o = sub.add_parser("outcome", help="fill in how it resolved")
    o.add_argument("--id", type=int, required=True)
    o.add_argument("--exit", type=float, required=True)
    o.add_argument("--note", default="")
    o.set_defaults(func=cmd_outcome)

    s = sub.add_parser("score", help="does CLEARS beat FAILS?")
    s.set_defaults(func=cmd_score)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

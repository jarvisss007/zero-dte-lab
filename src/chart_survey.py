#!/opt/anaconda3/bin/python
"""chart_survey.py — THE CHART DESK: the firm's weekly read of price patterns (2026-09-22).

Anupam: "the agents does some daily or weekly analysis over the chart to come up with any
strategies or any analysis."

WHAT THIS IS, AND THE ONE DESIGN DECISION BEHIND IT
---------------------------------------------------
It does NOT hunt for chart patterns. A weekly job that searches a fresh universe for whatever
worked last week is a mining machine: at 42 trials the estate already expects a |t|>=2 by luck
more often than not, and a searcher adds trials every time it runs, forever.

Instead it carries a FROZEN REGISTRY of patterns that were each pre-declared once, and re-measures
them on the NEW week's bars only. Every run is therefore out-of-sample evidence about the same
fixed questions. The estimate gets sharper; the trial count does not move. Adding a pattern is a
registration (evolution ledger, one trial) and is Anupam's alone — REGISTRY is frozen at import and
`--propose` refuses to write one.

Every pattern is judged the way the studies of 2026-09-19 were judged, and for the same reason:
  no-memory line   a walk with no memory reaches the upper barrier first with probability
                   (entry - lower) / (upper - lower). The statistic is outcome MINUS that, so a
                   pattern cannot look good merely by placing its target nearer than its stop.
  day clustering   n is independent SESSION DATES. Every name on one date is one observation.
  drift control    each pattern's mirror image is measured beside it. If a rising tape is doing the
                   work, the long side looks good and the short side looks bad by the same amount.
  entries          the NEXT bar's open. Both barriers inside one bar = ambiguous, dropped, counted.
  luck count       the report states how many |t|>=2 it expects from its own cell count by chance.

It proposes NOTHING on its own. A pattern becomes a candidate only after `PROMOTE_WEEKS` separate
weeks of out-of-sample evidence AND a pooled day-clustered |t| >= 2.0 on that forward record alone
— and even then it is written as a CANDIDATE for Anupam, never as a rule.

Forward book : results/chart_survey_book.json   (append-only, one row per pattern per week)
Report       : results/chart_survey.json
Forecasts    : agent/forecasts.csv               (the shared contract: date,p,outcome — fed to
                                                  ~/bin/score_forecasts.py so this desk is graded
                                                  on calibration like every other lab)
Run: chart_survey.py run [--week YYYY-MM-DD]   |   chart_survey.py report   |   chart_survey.py propose
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atomicio import atomic_json, hold_book                      # noqa: E402
from data_utils import atr                                       # noqa: E402
from zone_rotation_study import NAMES, first_passage, yahoo      # noqa: E402
from day_high_retest_study import scan as retest_scan            # noqa: E402
from bos_followthrough_study import scan as bos_scan             # noqa: E402
from zone_rotation_study import scan as zone_scan               # noqa: E402

LAB = HERE.parent
BOOK = LAB / "results" / "chart_survey_book.json"
OUT = LAB / "results" / "chart_survey.json"
FCAST = LAB / "agent" / "chart_forecasts.csv"   # its OWN ledger. zero-dte-lab/agent/forecasts.csv
# belongs to the 0DTE desk and has a different schema; appending to another desk's book is how a
# ledger gets silently corrupted (found by doing it, 2026-09-22).
PROMOTE_WEEKS, PROMOTE_T = 8, 2.0

# ── THE FROZEN REGISTRY ────────────────────────────────────────────────────────────────────────
# Each entry: the question, the scan that answers it, the sub-book to read, and the DATE it was
# declared. Nothing is added here by a run. Adding one costs a trial and is Anupam's ruling.
REGISTRY = {
    "zone_rotation": {
        "declared": "2026-09-19",
        "asks": "after a visit to premium (discount) and a pullback to equilibrium, does price get "
                "back to the zone it came from before it reaches the far one?",
        "first_verdict": "SPY 5m 2024-25 +7.8pp t 2.2; NOT replicated out of that span; +0.5pp on his names",
        "scan": lambda df, nm: zone_scan(df, nm, W=156, H=156, H_d=78),
        "question": "a_at_the_touch",
    },
    "day_high_retest": {
        "declared": "2026-09-19",
        "asks": "back at the day's high a second time, does it reject (-1 ATR) before it breaks (+1 ATR)?",
        "first_verdict": "46.0% vs a 46.3% no-memory line on 576 events — a coin",
        "scan": lambda df, nm: retest_scan(df, nm),
        "question": "e1_at_the_touch",
    },
    "bos_followthrough": {
        "declared": "2026-09-22",
        "asks": "after a break of structure, does price keep going 1.5 ATR before giving back 1.5 ATR?",
        "first_verdict": "47.8% vs 50% on SPY 5m and on his 16 names — a coin; bullish breaks faded (t -3.0)",
        "scan": lambda df, nm: bos_scan(df, nm, H=156),
        "question": "f1_keeps_going",
    },
}


def week_of(d: dt.date) -> str:
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def summarise(rows: list) -> dict:
    """The one scoring routine. Excess over the no-memory line, clustered by session date."""
    rows = [r for r in rows if r.get("status") != "ambiguous" and r.get("excess") is not None]
    if not rows:
        return {"n_events": 0, "n_days": 0, "reason": "the pattern did not occur this week"}
    df = pd.DataFrame(rows)
    days = df.groupby("date")["excess"].mean()
    sd = days.std(ddof=1) if len(days) > 2 else float("nan")
    t = float(days.mean() / (sd / math.sqrt(len(days)))) if sd and sd > 0 else None
    return {"n_events": int(len(df)), "n_days": int(len(days)),
            "clustered_by": "session date, all names pooled",
            "hit_pct": round(float(df["hit"].mean()) * 100, 1),
            "no_memory_pct": round(float(df["p0"].mean()) * 100, 1),
            "excess_pp": round(float(df["excess"].mean()) * 100, 1),
            "t_days": None if t is None else round(t, 2),
            "ambiguous_dropped": int(sum(1 for r in rows if r.get("status") == "ambiguous"))}


def run(week: str | None):
    frames, dropped = yahoo(NAMES, "5m", "60d")
    if not frames:
        print("chart_survey: BROKEN — no name returned usable bars; nothing measured, nothing written")
        return 1
    allts = pd.concat([d["ts"] for d in frames.values()])
    wk = week or week_of(allts.max().date())
    lo, hi = dt.date.fromisoformat(wk), dt.date.fromisoformat(wk) + dt.timedelta(days=7)
    # only THIS week's bars: every run is fresh evidence about the same frozen questions
    fresh = {nm: d[(d["ts"].dt.date >= lo) & (d["ts"].dt.date < hi)].reset_index(drop=True)
             for nm, d in frames.items()}
    fresh = {nm: d for nm, d in fresh.items() if len(d) > 200}
    if not fresh:
        print(f"chart_survey: week {wk} holds too few bars per name to measure — nothing written.\n"
              "  This is the correct answer mid-week: the desk reads a COMPLETE week, on Friday after "
              "the close.\n  Its first forward week is the first full one after each pattern's "
              "declaration date.")
        return 1

    results, fcast = {}, []
    for key, spec in REGISTRY.items():
        pooled = []
        for nm, d in fresh.items():
            try:
                r = spec["scan"](d, nm)
                rows = r["rows"][spec["question"]] if "rows" in r else r[spec["question"]]
                pooled += rows
            except Exception as e:
                print(f"  {key}/{nm}: scan failed ({type(e).__name__}) — excluded, not silently zeroed")
        s = summarise(pooled)
        results[key] = {"asks": spec["asks"], "declared": spec["declared"],
                        "first_verdict": spec["first_verdict"], **s}
        # one probabilistic forecast per pattern per week, on the SAME contract every lab uses:
        # p = the no-memory line (the honest prior), outcome = did the week's events beat it.
        # forward only, exactly like the book: an in-sample week is shown, never scored
        if s.get("n_events") and wk > spec["declared"]:
            fcast.append({"date": wk, "p": round(s["no_memory_pct"] / 100, 4),
                          "outcome": 1 if s["excess_pp"] > 0 else 0, "pattern": key,
                          "n_events": s["n_events"], "n_days": s["n_days"]})

    hold_book(str(BOOK))
    book = json.loads(BOOK.read_text()) if BOOK.exists() else {"rows": []}
    have = {(r["week"], r["pattern"]) for r in book["rows"]}
    added = 0
    for key, r in results.items():
        if (wk, key) in have or not r.get("n_events"):
            continue
        # FORWARD ONLY. A week that ends on or before the day a pattern was declared is the data the
        # pattern was found in; writing it into the forward book would let a backfill manufacture a
        # record out of the sample that produced the idea. Measured and reported, never banked.
        if wk <= REGISTRY[key]["declared"]:
            print(f"  {key}: week {wk} is ON OR BEFORE its declaration ({REGISTRY[key]['declared']}) — "
                  "measured and shown, NOT written to the forward book (in-sample)")
            continue
        book["rows"].append({"week": wk, "pattern": key, "measured_on": dt.date.today().isoformat(),
                             **{k: r[k] for k in ("n_events", "n_days", "hit_pct", "no_memory_pct",
                                                  "excess_pp", "t_days")}})
        added += 1
    atomic_json(str(BOOK), book, indent=1)

    if fcast:
        import csv
        COLS = ["date", "p", "outcome", "pattern", "n_events", "n_days"]
        FCAST.parent.mkdir(exist_ok=True)
        if FCAST.exists():
            have = (FCAST.read_text(encoding="utf-8").split("\n") or [""])[0].strip()
            if have and have != ",".join(COLS):
                print(f"  REFUSED to write forecasts: {FCAST.name} has a different header ({have[:60]}). "
                      "Appending rows under someone else's columns is how a ledger is corrupted.")
                fcast = []
        if fcast:
            new_file = not FCAST.exists()
            with open(FCAST, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=COLS)
                if new_file:
                    w.writeheader()
                for row in fcast:
                    w.writerow(row)

    report(wk, results, added)
    return 0


def forward(pattern: str, book: dict) -> dict:
    """The only record that counts: every week this pattern has been measured, pooled."""
    rows = [r for r in book["rows"] if r["pattern"] == pattern]
    if not rows:
        return {"weeks": 0}
    ex = [r["excess_pp"] for r in rows]
    sd = pd.Series(ex).std(ddof=1) if len(ex) > 2 else float("nan")
    t = (sum(ex) / len(ex)) / (sd / math.sqrt(len(ex))) if sd and sd > 0 else None
    return {"weeks": len(rows), "events": sum(r["n_events"] for r in rows),
            "days": sum(r["n_days"] for r in rows),
            "mean_excess_pp": round(sum(ex) / len(ex), 2),
            "weeks_positive": sum(1 for x in ex if x > 0),
            "t_weeks": None if t is None else round(float(t), 2),
            "weeks_to_promotion": max(0, PROMOTE_WEEKS - len(rows))}


def report(wk=None, results=None, added=0):
    book = json.loads(BOOK.read_text()) if BOOK.exists() else {"rows": []}
    fwd = {k: forward(k, book) for k in REGISTRY}
    scored = [r for r in (results or {}).values() if r.get("t_days") is not None]
    luck = 1 - (1 - 0.0455) ** len(scored) if scored else 0
    cand = [k for k, f in fwd.items()
            if f.get("weeks", 0) >= PROMOTE_WEEKS and abs(f.get("t_weeks") or 0) >= PROMOTE_T]
    rep = {"generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
           "week": wk, "rows_added": added,
           "registry_is_frozen": "a run never adds a pattern; adding one costs a trial and is Anupam's ruling",
           "this_week": results or {}, "forward_record": fwd,
           "cells_scored_this_week": len(scored),
           "chance_of_one_t2_by_luck_this_week": round(luck, 3),
           "promotion_bar": f"{PROMOTE_WEEKS} weeks of forward evidence AND |t| >= {PROMOTE_T} on that record alone",
           "candidates_for_anupam": cand,
           "status": "DESCRIPTION ONLY — proposes no rule, registers no variant, takes no position"}
    OUT.parent.mkdir(exist_ok=True)
    atomic_json(str(OUT), rep, indent=1)

    print(f"\nCHART DESK · week {wk or '(report only)'} · {added} row(s) added to the forward book")
    for k, f in fwd.items():
        w = results.get(k) if results else None
        line = (f"  {k:20s} forward: {f.get('weeks',0):2d} wk · {f.get('events',0):5d} events · "
                f"mean {f.get('mean_excess_pp','—')}pp · t {f.get('t_weeks','—')} · "
                f"{f.get('weeks_positive','—')}/{f.get('weeks',0)} weeks up")
        if w and w.get("n_events"):
            line += f"\n  {'':20s} this week: {w['hit_pct']}% vs {w['no_memory_pct']}% → {w['excess_pp']:+}pp (t {w['t_days']}, {w['n_days']}d)"
        elif w:
            line += f"\n  {'':20s} this week: {w.get('reason')}"
        print(line)
    print(f"  luck: {round(luck,3)} chance of one |t|>=2 among this week's {len(scored)} cells")
    print(f"  candidates for a ruling: {cand or 'none — and that is the expected result'}")
    print(f"  wrote {OUT.name} and {BOOK.name}")


def propose(_):
    print("chart_survey: REFUSED. A run may not add a pattern to the registry.\n"
          "  Adding one is a new pre-declared test: it costs a trial in the evolution ledger and is\n"
          "  Anupam's ruling alone (REG-PP-001). Write the question first, then register it, then\n"
          "  add it here — never the other way round.")
    return 1


def main():
    ap = argparse.ArgumentParser(description="the firm's weekly chart read — frozen questions, fresh bars")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--week", default=None, help="Monday of the week, YYYY-MM-DD")
    sub.add_parser("report"); sub.add_parser("propose")
    a = ap.parse_args()
    if a.cmd == "propose":
        return propose(a)
    if a.cmd == "report":
        return report()
    return run(getattr(a, "week", None))


if __name__ == "__main__":
    sys.exit(main() or 0)

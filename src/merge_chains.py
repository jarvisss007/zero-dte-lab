"""Union the two chain-recorder legs into one canonical per-session file.

The recorder now runs twice:
  - laptop leg  -> data/chains/     every 5 min via launchd, only while the lid
                   is open (this is the leg that lost 2026-07-09..07-16)
  - cloud leg   -> data/chains_ci/  every 10 min via GitHub Actions, awake or
                   not, but best-effort: GitHub delays and drops scheduled runs
                   under load

Neither leg is complete on its own and both are honest about why. This merges
them.

THE DEDUPE KEY IS THE BOOK TIMESTAMP, NOT THE FETCH TIME. Both legs pull the
same CBOE delayed-quotes endpoint; when their polls land inside the same
~5-minute book, they return byte-identical quotes under two different
fetched_at values. Deduping on fetched_at would double-count one observation
and inflate every row-based statistic in the lab. The unit of observation is
the book snapshot: (quote_ts, expiry, type, strike).

Coverage is reported in DISTINCT BOOK TIMESTAMPS per session, never in rows —
rows scale with how many strikes were inside the +/-5% band that day, which
moves with realized vol and has nothing to do with capture.

Run:  /opt/anaconda3/bin/python src/merge_chains.py            # merge + report
      /opt/anaconda3/bin/python src/merge_chains.py --report   # report only
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAPTOP_DIR = ROOT / "data" / "chains"
CLOUD_DIR = ROOT / "data" / "chains_ci"
MERGED_DIR = ROOT / "data" / "chains_merged"

SESSION_RE = re.compile(r"^SPY_(\d{4}-\d{2}-\d{2})\.csv$")

# One book roughly every 5 min across 09:30-16:00 ET. Used only to express
# coverage as a percentage; the raw distinct-timestamp count is the fact.
NOMINAL_BOOKS_PER_SESSION = 78

KEY_FIELDS = ("quote_ts", "expiry", "type", "strike")


def session_files(d: Path) -> dict[str, Path]:
    """Map YYYY-MM-DD -> csv path for one leg's directory."""
    if not d.is_dir():
        return {}
    out = {}
    for p in sorted(d.iterdir()):
        m = SESSION_RE.match(p.name)
        if m:
            out[m.group(1)] = p
    return out


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def merge_session(paths: list[Path]) -> tuple[list[str], list[dict]]:
    """Union rows from every leg for one date, deduped on the book key.

    On a collision the row with the EARLIEST fetched_at wins — that is the leg
    that actually observed the book first; the other is a re-read of the same
    quotes.
    """
    header: list[str] = []
    best: dict[tuple, dict] = {}
    for p in paths:
        cols, rows = read_rows(p)
        if not header:
            header = cols
        for row in rows:
            key = tuple(row.get(f, "") for f in KEY_FIELDS)
            prev = best.get(key)
            if prev is None or row.get("fetched_at", "") < prev.get("fetched_at", ""):
                best[key] = row
    merged = sorted(best.values(),
                    key=lambda r: (r.get("quote_ts", ""), r.get("type", ""),
                                   float(r.get("strike") or 0)))
    return header, merged


def books(rows: list[dict]) -> set[str]:
    return {r.get("quote_ts", "") for r in rows if r.get("quote_ts")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print the coverage table without writing merged files")
    args = ap.parse_args()

    laptop = session_files(LAPTOP_DIR)
    cloud = session_files(CLOUD_DIR)
    dates = sorted(set(laptop) | set(cloud))
    if not dates:
        print("no session files found in either leg")
        return 1

    if not args.report:
        MERGED_DIR.mkdir(parents=True, exist_ok=True)

    per_leg: dict[str, set[str]] = defaultdict(set)
    rows_out = []
    for date in dates:
        paths = [p for p in (laptop.get(date), cloud.get(date)) if p]
        header, merged = merge_session(paths)

        lap_books = books(read_rows(laptop[date])[1]) if date in laptop else set()
        cld_books = books(read_rows(cloud[date])[1]) if date in cloud else set()
        all_books = lap_books | cld_books
        per_leg["laptop"] |= {f"{date} {t}" for t in lap_books}
        per_leg["cloud"] |= {f"{date} {t}" for t in cld_books}

        if not args.report:
            with open(MERGED_DIR / f"SPY_{date}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=header)
                w.writeheader()
                w.writerows(merged)

        rows_out.append((
            date, len(lap_books), len(cld_books),
            len(cld_books - lap_books), len(all_books),
            100.0 * len(all_books) / NOMINAL_BOOKS_PER_SESSION,
        ))

    print(f"{'session':<12}{'laptop':>8}{'cloud':>7}{'rescued':>9}"
          f"{'merged':>8}{'cover':>8}")
    print("-" * 52)
    for date, lap, cld, resc, tot, pct in rows_out:
        print(f"{date:<12}{lap:>8}{cld:>7}{resc:>9}{tot:>8}{pct:>7.0f}%")
    print("-" * 52)
    tot_books = len(per_leg["laptop"] | per_leg["cloud"])
    rescued = len(per_leg["cloud"] - per_leg["laptop"])
    print(f"{len(rows_out)} sessions · {tot_books} distinct books · "
          f"{rescued} the laptop alone would have missed")
    print("\n'rescued' is the honest measure of what the cloud leg bought: "
          "books\nno lid-open recorder saw. It reads 0 until the cloud leg has "
          "run.\nSessions, not rows, are what the 60-session verdict counts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""session_count.py — the lab's OWN count of usable recorded sessions.

CARD-001 (2026-08-20): the front page said "1/60 sessions" while 25 session files sat on
disk, and the Resolver rightly refused to type a number onto the card because the
definition of USABLE belongs to this lab. Here it is, machine-readable:

  A session file is USABLE when it holds at least 86% of a full session's books
  (the README's published threshold), where "full" is the median row count of the
  sessions that are clearly not stubs (>= 25% of the largest file). Stubs — recorder
  died at the open, DNS at the bell, sleep gaps — are counted and named, not hidden.

Writes data/session_count.json and prints one line. Nothing else reads the chains.
Run after every recording day; the card and the README quote this number and no other.
"""
import json, os, statistics, glob, datetime as dt
BASE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(BASE, "data", "chains")
USABLE_FRAC = 0.86
GATE = 60


def first_snapshot_fits(path):
    """Does this session's FIRST snapshot admit a smile fit?

    CARD-005, 2026-08-29. The lab publishes two counts and says plainly which governs:
    a row-count (`usable`) and the smile-fit/admissible count, "the gate is the later of
    the two". Only the row-count was ever emitted, so the front page published 24/60
    while the lab's own text said 21/60 governs — and a green test certified it.

    The criterion is NOT re-derived here. It is src/implied_density.py's own bar, read
    off that file: live two-sided quotes, forward by put-call parity, OTM wing in IV
    space filtered to 0.01 < iv < 5.0, deduplicated — and >= 8 survivors, below which
    implied_density itself raises "smile unfit". Duplicating a threshold is how two
    numbers drift apart; this reads the same data the fitter would.

    FIRST snapshot, not last: ZDTE-003 stamps the first, and the whole point of the
    gate is what was knowable at the call.
    """
    try:
        import pandas as pd
    except ImportError:
        return None                      # cannot judge; caller must not guess
    try:
        df = pd.read_csv(path)
        first = sorted(df["fetched_at_et"].unique())[0]
        snap = df[df["fetched_at_et"] == first]
        live = snap[(snap["bid"] > 0) & (snap["ask"] > 0)].copy()
        live["mid"] = (live["bid"] + live["ask"]) / 2
        calls = live[live["type"] == "C"].set_index("strike").sort_index()
        puts = live[live["type"] == "P"].set_index("strike").sort_index()
        both = calls.join(puts, lsuffix="_c", rsuffix="_p", how="inner")
        if both.empty:
            return False
        k0 = (both["mid_c"] - both["mid_p"]).abs().idxmin()
        fwd = k0 + both.loc[k0, "mid_c"] - both.loc[k0, "mid_p"]
        otm = pd.concat([puts[puts.index < fwd], calls[calls.index >= fwd]])
        otm = otm[(otm["iv"] > 0.01) & (otm["iv"] < 5.0)]
        otm = otm[~otm.index.duplicated()]
        return len(otm) >= 8
    except Exception:
        return False


def main():
    files = sorted(glob.glob(os.path.join(CH, "SPY_*.csv")))
    counts = {}
    for f in files:
        with open(f) as fh:
            counts[os.path.basename(f)[4:14]] = max(0, sum(1 for _ in fh) - 1)
    if not counts:
        print("no session files"); return
    top = max(counts.values())
    full_like = [c for c in counts.values() if c >= 0.25 * top]
    full = statistics.median(full_like) if full_like else top
    need = USABLE_FRAC * full
    usable = sorted(d for d, c in counts.items() if c >= need)
    stubs = sorted(d for d, c in counts.items() if c < need)
    # Admissible = complete AND the first snapshot fits the smile. This is the count the
    # lab says GOVERNS its gate; `usable` alone is the flattering half (CARD-005).
    by_date = {os.path.basename(f)[4:14]: f for f in files}
    fits, unfit, unknown = [], [], []
    for d in usable:
        v = first_snapshot_fits(by_date[d])
        (fits if v else unknown if v is None else unfit).append(d)
    out = {"as_of": dt.date.today().isoformat(), "definition": f"rows >= {USABLE_FRAC:.0%} of full-session median ({int(full)} rows -> need {int(need)})",
           "files": len(counts), "usable": len(usable), "stubs": len(stubs), "gate": GATE,
           "usable_sessions": usable, "stub_sessions": stubs,
           "admissible": len(fits),
           "admissible_definition": ("complete AND first snapshot fits the smile "
                                     "(>=8 usable OTM quotes, implied_density.py's own bar) "
                                     "— THIS is the count that governs the gate"),
           "admissible_sessions": fits, "unfit_sessions": unfit,
           "unjudged_sessions": unknown}
    json.dump(out, open(os.path.join(BASE, "data", "session_count.json"), "w"), indent=1)
    print(f"zero-dte sessions: {len(usable)} usable / {len(counts)} files ({len(stubs)} stubs: {', '.join(stubs)}) "
          f"-> {len(usable)}/{GATE} toward the timing gate")

if __name__ == "__main__":
    main()

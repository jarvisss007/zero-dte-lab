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
    out = {"as_of": dt.date.today().isoformat(), "definition": f"rows >= {USABLE_FRAC:.0%} of full-session median ({int(full)} rows -> need {int(need)})",
           "files": len(counts), "usable": len(usable), "stubs": len(stubs), "gate": GATE,
           "usable_sessions": usable, "stub_sessions": stubs}
    json.dump(out, open(os.path.join(BASE, "data", "session_count.json"), "w"), indent=1)
    print(f"zero-dte sessions: {len(usable)} usable / {len(counts)} files ({len(stubs)} stubs: {', '.join(stubs)}) "
          f"-> {len(usable)}/{GATE} toward the timing gate")

if __name__ == "__main__":
    main()

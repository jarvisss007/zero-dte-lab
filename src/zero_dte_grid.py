"""The entry×exit grid: naked 0DTE SPY legs entered at EVERY snapshot, all exits measured.

Anupam, 2026-08-30: "it can take positions all the time whenever the market is open...
if it's profitable at 5min at good criteria then exit, or 20 or 30 min."

Retrospective study over every recorded session — the recorder already holds ~76
snapshots/day with bid/ask, so "enter all the time" is measurable from disk before any
forward book commits to it. Entries: ATM call and ATM put at each snapshot, bought at
the ASK. Exits: the bid at +5/10/15/20/30 minutes, and settle (|close−K| ITM else 0).

Also scores the one mechanical version of "exit when good" that can be named in advance:
  FIRST-GREEN — exit at the first checkpoint whose bid exceeds the entry ask;
                if none is green, ride to settle.
That rule harvests small wins and keeps full losses by construction; the study exists to
show what that costs rather than argue about it.

HONEST N. Entries within one session share that session's realized path — 150 entries on
one day are nearer ONE observation than 150. Aggregates are reported per entry-hour
bucket with the SESSION count beside them; the session count is the only n.
"""
from __future__ import annotations
import csv, datetime as dt, glob, json, os, statistics as st
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAINS = os.path.join(BASE, "data", "chains")
OUT = os.path.join(BASE, "results", "entry_exit_grid.json")
HORIZONS = (5, 10, 15, 20, 30)
MIN_OI, MAX_SPREAD = 50, 0.35


def leg_ok(o):
    try:
        b, a, oi = float(o["bid"] or 0), float(o["ask"] or 0), float(o["open_interest"] or 0)
    except ValueError:
        return False
    return b > 0 and a > 0 and oi >= MIN_OI and (a - b) / ((a + b) / 2) <= MAX_SPREAD


def run():
    files = sorted(glob.glob(os.path.join(CHAINS, "SPY_*.csv")))
    agg = defaultdict(list)          # (hour_bucket, exit) -> [pnl_pct]
    sess_of = defaultdict(set)
    fg = defaultdict(list)           # hour_bucket -> first-green pnl_pct
    n_entries = 0
    for f in files:
        day = os.path.basename(f)[4:14]
        rows = list(csv.DictReader(open(f)))
        snaps = defaultdict(list)
        for r in rows:
            if r.get("expiry") == day:
                snaps[r["fetched_at_et"]].append(r)
        stamps = sorted(snaps)
        if len(stamps) < 8 or stamps[-1][-8:] < "15:55:00":
            continue                                    # incomplete session — skip whole day
        close = float(snaps[stamps[-1]][0]["spot"])
        T = {s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") for s in stamps}
        for i, s0 in enumerate(stamps):
            if s0[-8:] > "15:25:00":
                continue                                # entry must have room for +30m
            spot = float(snaps[s0][0]["spot"])
            by = {}
            for r in snaps[s0]:
                if leg_ok(r):
                    by.setdefault(float(r["strike"]), {})[r["type"]] = r
            ks = [k for k, v in by.items() if "C" in v and "P" in v]
            if not ks:
                continue
            k = min(ks, key=lambda x: abs(x - spot))
            hb = s0[11:13] + ":00 ET"
            for cp in ("C", "P"):
                ask = float(by[k][cp]["ask"])
                n_entries += 1
                exits = {}
                for h in HORIZONS:
                    tgt = T[s0] + dt.timedelta(minutes=h)
                    cand = next((s for s in stamps[i:] if T[s] >= tgt), None)
                    if not cand:
                        continue
                    m = [x for x in snaps[cand] if x["type"] == cp
                         and abs(float(x["strike"] or 0) - k) < 1e-9 and (x.get("bid") or "").strip()]
                    if m:
                        exits[h] = (float(m[0]["bid"]) - ask) / ask * 100
                sv = max(close - k, 0) if cp == "C" else max(k - close, 0)
                exits["settle"] = (sv - ask) / ask * 100
                for h, v in exits.items():
                    agg[(hb, h)].append(v)
                    sess_of[hb].add(day)
                green = next((exits[h] for h in HORIZONS if h in exits and exits[h] > 0), None)
                fg[hb].append(green if green is not None else exits["settle"])
    tbl = {}
    for (hb, h), v in agg.items():
        tbl.setdefault(hb, {})[str(h)] = {"mean_pct": round(st.mean(v), 1),
                                          "win": round(100 * sum(1 for x in v if x > 0) / len(v)),
                                          "n_rows": len(v)}
    for hb, v in fg.items():
        tbl.setdefault(hb, {})["FIRST-GREEN"] = {"mean_pct": round(st.mean(v), 1),
                                                 "win": round(100 * sum(1 for x in v if x > 0) / len(v)),
                                                 "n_rows": len(v)}
    out = {"as_of": dt.date.today().isoformat(), "sessions_used": len({d for s in sess_of.values() for d in s}),
           "entries": n_entries,
           "note": ("Entries within one session share its realized path; the SESSION count is "
                    "the only n. FIRST-GREEN = exit at first profitable checkpoint else settle."),
           "by_entry_hour": {hb: {"sessions": len(sess_of[hb]), **tbl[hb]} for hb in sorted(tbl)}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"grid: {n_entries} entries over {out['sessions_used']} sessions -> {OUT}")
    hdr = ["entry"] + [f"+{h}m" for h in HORIZONS] + ["settle", "FIRSTGRN", "sess"]
    print("  " + "  ".join(f"{h:>8}" for h in hdr))
    for hb in sorted(tbl):
        cells = [hb]
        for h in list(HORIZONS) + ["settle", "FIRST-GREEN"]:
            c = tbl[hb].get(str(h) if h != "FIRST-GREEN" else h)
            cells.append(f"{c['mean_pct']:+.1f}" if c else "—")
        cells.append(str(len(sess_of[hb])))
        print("  " + "  ".join(f"{c:>8}" for c in cells))


if __name__ == "__main__":
    run()

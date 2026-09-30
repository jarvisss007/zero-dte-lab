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

2026-09-29 REFRESH (data range only): `--out` writes a NEW file, `--through` caps the DATA RANGE, and the
loader now reads only the CBOE recorder's plain session files (SPY_<date>.csv). `SPY_<date>.yfinance.csv` is a
labelled fallback feed of a different quality that shares the date stem, so the bare glob would have counted its
session a second time; it is excluded (same regex merge_chains.py uses). No rule, threshold, fill or guard changed.
`--added` also computes the cells ADDED 2026-09-29 (bottom of this file); they are extra looks and feed nothing above.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, glob, json, math, os, re, statistics as st
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAINS = os.path.join(BASE, "data", "chains")
OUT = os.path.join(BASE, "results", "entry_exit_grid.json")
HORIZONS = (5, 10, 15, 20, 30)
MIN_OI, MAX_SPREAD = 50, 0.35
SESSION_FILE = re.compile(r"^SPY_(\d{4}-\d{2}-\d{2})\.csv$")   # plain CBOE session files only


def session_files(through=None):
    """Every recorded CBOE session file, oldest first. `through` (YYYY-MM-DD) caps the DATA RANGE only."""
    files = []
    for f in sorted(glob.glob(os.path.join(CHAINS, "SPY_*.csv"))):
        m = SESSION_FILE.match(os.path.basename(f))
        if m and (through is None or m.group(1) <= through):
            files.append(f)
    return files


def leg_ok(o):
    try:
        b, a, oi = float(o["bid"] or 0), float(o["ask"] or 0), float(o["open_interest"] or 0)
    except ValueError:
        return False
    return b > 0 and a > 0 and oi >= MIN_OI and (a - b) / ((a + b) / 2) <= MAX_SPREAD


def run(out_path=OUT, through=None, added=False):
    files = session_files(through)
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
    if added:
        out["ADDED_2026-09-29"] = added_cells(files, fg, sess_of)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"grid: {n_entries} entries over {out['sessions_used']} sessions -> {out_path}")
    hdr = ["entry"] + [f"+{h}m" for h in HORIZONS] + ["settle", "FIRSTGRN", "sess"]
    print("  " + "  ".join(f"{h:>8}" for h in hdr))
    for hb in sorted(tbl):
        cells = [hb]
        for h in list(HORIZONS) + ["settle", "FIRST-GREEN"]:
            c = tbl[hb].get(str(h) if h != "FIRST-GREEN" else h)
            cells.append(f"{c['mean_pct']:+.1f}" if c else "—")
        cells.append(str(len(sess_of[hb])))
        print("  " + "  ".join(f"{c:>8}" for c in cells))
    if added:
        print_added(out["ADDED_2026-09-29"])


# =====================================================================================================
# ADDED 2026-09-29 - extra looks, each COUNTED as a look (multiplicity). Nothing below feeds the grid above.
# Definitions frozen here, before the first number was seen.
#
# HIS PATTERN. He enters near 07:25 PT (10:25 ET) and exits near 08:05 PT (+40 min). One entry per session:
#   ATM call, ATM put, 1-strike-OTM call, 1-strike-OTM put, each bought at the ASK. Everything else is the grid's own:
#   ATM = the strike nearest spot among strikes whose call AND put pass leg_ok; 1-strike OTM = the next LISTED strike
#   away (call up, put down) and that leg must itself pass leg_ok; exit = the BID of the same contract at the first
#   snapshot at/after +40 min (blank bid = no exit, "0" = worthless); settle = |last-snapshot spot - K| ITM else 0;
#   the grid's session-completeness rule applies. pnl% = (exit - ask) / ask.
#   The nearest snapshot must lie within 7.5 min (1.5 snapshot intervals) of 10:25, else that session has no entry.
#   TWO CLOCKS, because they differ by ~16 min. `quote_ts` is the CBOE book stamp = the market time of the quotes
#   (the chain's spot tracks it: mean abs error 0.13 vs 0.60 against the SPY 5m path, 2026-07-17..08-14), so it is the
#   PRIMARY reading - 10:25 means quotes that existed at 10:25. `fetched_at_et` is when the recorder polled; it is the
#   clock the grid's own entry-hour labels use (its "10:00 ET" bucket is market time ~09:44-10:43).
# FIRST-GREEN SHAPE. avg loss / avg win of the grid's own FIRST-GREEN rows per entry hour (headline: 10:00 ET).
#   Does the mechanical take-the-first-profit exit produce a loss-heavy shape (losses several times the wins)?
# SETTLE REFERENCE. The grid's settle uses the last recorded snapshot's spot, stamped ~15:47-15:52 ET (the feed is
#   delayed), not the 16:00 close. Kept as the grid's own convention; the settle cells also show a labelled check
#   against the official close (stock-radar/data/spy_daily.csv, written after the bell).
# =====================================================================================================
OFFICIAL_CLOSES = os.path.expanduser("~/stock-radar/data/spy_daily.csv")
ENTRY_HHMM, HOLD_MIN, TOL_MIN = "10:25:00", 40, 7.5
STRUCTS = ("ATM_call", "ATM_put", "OTM1_call", "OTM1_put")


def _official_closes():
    """{YYYY-MM-DD: settled daily close}, read-only, from stock-radar's own SPY file. {} if unreadable."""
    try:
        with open(OFFICIAL_CLOSES) as fh:
            rd = csv.reader(fh)
            next(rd)
            return {r[0]: float(r[1]) for r in rd if len(r) > 1 and r[1]}
    except OSError:
        return {}


def _load_session(fp):
    """The grid's own per-session load and completeness rule, verbatim."""
    day = os.path.basename(fp)[4:14]
    snaps = defaultdict(list)
    for r in csv.DictReader(open(fp)):
        if r.get("expiry") == day:
            snaps[r["fetched_at_et"]].append(r)
    stamps = sorted(snaps)
    if len(stamps) < 8 or stamps[-1][-8:] < "15:55:00":
        return None
    return day, snaps, stamps, float(snaps[stamps[-1]][0]["spot"])


def _qt(snaps, s):
    """The CBOE book stamp of snapshot s, as a naive ET datetime."""
    return dt.datetime.strptime(snaps[s][0]["quote_ts"][:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")


def _stats(vals):
    """One entry per session, so n = sessions."""
    n = len(vals)
    if not n:
        return {"n_sessions": 0, "reason": "no session produced this exit"}
    wins, losses = [x for x in vals if x > 0], [x for x in vals if x < 0]
    aw = st.mean(wins) if wins else None
    al = st.mean(losses) if losses else None
    sd = st.stdev(vals) if n > 2 else 0.0
    return {"n_sessions": n, "clustered_by": "session date",
            "mean_pct": round(st.mean(vals), 1), "median_pct": round(st.median(vals), 1),
            "win_pct": round(100 * len(wins) / n, 1), "n_win": len(wins), "n_loss": len(losses),
            "n_flat": n - len(wins) - len(losses),
            "avg_win_pct": None if aw is None else round(aw, 1),
            "avg_loss_pct": None if al is None else round(al, 1),
            "loss_over_win_ratio": round(-al / aw, 2) if (aw and al is not None) else None,
            "t_days": round(st.mean(vals) / (sd / math.sqrt(n)), 2) if sd > 0 else None}


def _his_pattern(sessions, clock, off):
    """sessions: [(day, snaps, stamps, close)]. One entry per session per structure -> (records, excluded)."""
    recs, excluded = [], defaultdict(list)          # excluded[reason] -> [session]
    for day, snaps, stamps, close in sessions:
        T = {s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") for s in stamps}
        Q = {s: _qt(snaps, s) for s in stamps}
        C = Q if clock == "market" else T
        want = dt.datetime.strptime(f"{day} {ENTRY_HHMM}", "%Y-%m-%d %H:%M:%S")
        i = min(range(len(stamps)), key=lambda j: abs((C[stamps[j]] - want).total_seconds()))
        s0 = stamps[i]
        gap = (C[s0] - want).total_seconds() / 60
        if abs(gap) > TOL_MIN:
            excluded[f"nearest snapshot more than {TOL_MIN} min from 10:25"].append(f"{day} ({gap:+.1f} min)")
            continue
        spot = float(snaps[s0][0]["spot"])
        by = {}
        for r in snaps[s0]:
            if leg_ok(r):
                by.setdefault(float(r["strike"]), {})[r["type"]] = r
        ks = [k for k, v in by.items() if "C" in v and "P" in v]
        if not ks:
            excluded["no strike with both legs passing leg_ok"].append(day)
            continue
        k = min(ks, key=lambda x: abs(x - spot))
        listed = {t: sorted({float(r["strike"]) for r in snaps[s0] if r["type"] == t}) for t in ("C", "P")}
        ic, ip = listed["C"].index(k), listed["P"].index(k)
        legs = {"ATM_call": ("C", k), "ATM_put": ("P", k)}
        if ic + 1 < len(listed["C"]):
            legs["OTM1_call"] = ("C", listed["C"][ic + 1])
        if ip > 0:
            legs["OTM1_put"] = ("P", listed["P"][ip - 1])
        for name in STRUCTS:
            if name not in legs:
                excluded[f"{name}: no listed strike beyond ATM"].append(day)
                continue
            cp, kk = legs[name]
            row = by.get(kk, {}).get(cp)
            if row is None:
                excluded[f"{name}: leg fails leg_ok"].append(day)
                continue
            ask = float(row["ask"])
            tgt = C[s0] + dt.timedelta(minutes=HOLD_MIN)
            cand = next((s for s in stamps[i:] if C[s] >= tgt), None)
            m = [x for x in snaps[cand] if x["type"] == cp and abs(float(x["strike"] or 0) - kk) < 1e-9
                 and (x.get("bid") or "").strip()] if cand else []
            sv = max(close - kk, 0) if cp == "C" else max(kk - close, 0)
            rec = {"date": day, "structure": name, "strike": kk, "ask": ask, "entry_fetched_et": s0[11:],
                   "entry_book_stamp_et": Q[s0].strftime("%H:%M:%S"), "gap_to_10:25_min": round(gap, 1),
                   "settle_spot_grid": close, "pnl_settle_grid_pct": round((sv - ask) / ask * 100, 3)}
            if m:
                bid = float(m[0]["bid"])
                rec.update({"exit_fetched_et": cand[11:], "exit_book_stamp_et": Q[cand].strftime("%H:%M:%S"),
                            "exit_bid": bid, "hold_min": round((C[cand] - C[s0]).total_seconds() / 60, 1),
                            "pnl_40m_pct": round((bid - ask) / ask * 100, 3)})
            else:
                rec["pnl_40m_pct"] = None
                excluded[f"{name}: no +{HOLD_MIN}m exit quote"].append(day)
            if day in off:
                sv2 = max(off[day] - kk, 0) if cp == "C" else max(kk - off[day], 0)
                rec.update({"settle_close_official": off[day],
                            "pnl_settle_official_pct": round((sv2 - ask) / ask * 100, 3)})
            recs.append(rec)
    return recs, excluded


def _his_pattern_block(sessions, clock, off):
    recs, excluded = _his_pattern(sessions, clock, off)
    cells = {}
    for name in STRUCTS:
        rs = [r for r in recs if r["structure"] == name]
        holds = [r["hold_min"] for r in rs if r.get("hold_min") is not None]
        cells[name] = {
            "entries": len(rs), "avg_ask_per_share": round(st.mean(r["ask"] for r in rs), 3) if rs else None,
            f"exit_plus_{HOLD_MIN}m_at_bid": {**_stats([r["pnl_40m_pct"] for r in rs if r["pnl_40m_pct"] is not None]),
                                              "median_hold_min": round(st.median(holds), 1) if holds else None,
                                              "max_hold_min": max(holds) if holds else None},
            "exit_settle_grid_convention": _stats([r["pnl_settle_grid_pct"] for r in rs]),
            "exit_settle_vs_official_close_CHECK": _stats([r["pnl_settle_official_pct"] for r in rs
                                                           if "pnl_settle_official_pct" in r])}
    return {"clock": "CBOE book stamp quote_ts (market time of the quotes)" if clock == "market"
            else "fetched_at_et (when the recorder polled - the grid's own labels)",
            "sessions_in_grid": len(sessions), "sessions_with_an_entry": len({r["date"] for r in recs}),
            "excluded": dict(excluded), "cells": cells, "records": recs}


def _fg_shape(v, n_sessions):
    wins, losses = [x for x in v if x > 0], [x for x in v if x < 0]
    aw, al = (st.mean(wins) if wins else None), (st.mean(losses) if losses else None)
    return {"n_rows": len(v), "n_sessions": n_sessions,
            "clustered_by": "rows share their session's path - the session count is the only n",
            "win_pct": round(100 * len(wins) / len(v), 1), "mean_pct": round(st.mean(v), 1),
            "avg_win_pct": None if aw is None else round(aw, 1), "avg_loss_pct": None if al is None else round(al, 1),
            "loss_over_win_ratio": round(-al / aw, 2) if (aw and al is not None) else None}


def added_cells(files, fg, sess_of):
    sessions = [s for s in (_load_session(fp) for fp in files) if s]
    off = _official_closes()
    grid_days = {d for s in sess_of.values() for d in s}
    diffs = [close - off[day] for day, _, _, close in sessions if day in off]
    last_stamps = sorted(_qt(snaps, stamps[-1]).strftime("%H:%M:%S") for _, snaps, stamps, _ in sessions)
    settle_ref = ({"sessions_compared": len(diffs), "mean_grid_minus_official": round(st.mean(diffs), 3),
                   "mean_abs": round(st.mean(abs(x) for x in diffs), 3), "max_abs": round(max(abs(x) for x in diffs), 3),
                   "last_book_stamp_et_earliest_latest": [last_stamps[0], last_stamps[-1]],
                   "note": "the grid's settle spot is the last recorded snapshot's spot, stamped ~15:47-15:52 ET, not 16:00"}
                  if diffs else {"reason": f"official closes unreadable at {OFFICIAL_CLOSES}"})
    n_cells = len(STRUCTS) * 2
    return {
        "label": "ADDED 2026-09-29 - extra looks, counted as looks; nothing here feeds the grid above",
        "status": "DESCRIPTION ONLY - nothing registered, no position follows from it",
        "session_set_matches_grid": grid_days == {s[0] for s in sessions},
        "his_pattern": {
            "definition": f"entry at the snapshot nearest {ENTRY_HHMM} ET (07:25 PT), within {TOL_MIN} min; exit = bid "
                          f"+{HOLD_MIN} min (08:05 PT) or settle; ATM/1-strike-OTM call and put bought at the ask; "
                          "grid's own leg_ok, exit-snapshot rule and settle",
            "PRIMARY_market_clock": _his_pattern_block(sessions, "market", off),
            "grid_fetch_clock_reading": _his_pattern_block(sessions, "fetch", off)},
        "first_green_shape": {
            "headline_10:00_ET": _fg_shape(fg["10:00 ET"], len(sess_of["10:00 ET"])) if fg.get("10:00 ET")
                                 else {"reason": "no 10:00 ET FIRST-GREEN rows"},
            "all_entry_hours_context": {hb: _fg_shape(v, len(sess_of[hb])) for hb, v in sorted(fg.items())},
            "his_own_record_loss_over_win": 2.8},
        "settle_reference_check": settle_ref,
        "looks_added": {"his_pattern_market_clock_cells": n_cells,
                        "his_pattern_settle_vs_official_close_check": len(STRUCTS),
                        "his_pattern_fetch_clock_cells": n_cells,
                        "first_green_loss_over_win_ratio_at_10:00_ET": 1,
                        "total": n_cells + len(STRUCTS) + n_cells + 1}}


def print_added(a):
    print("\n  ADDED 2026-09-29 - his pattern (07:25 -> +40 min, or settle), one entry per session")
    for key in ("PRIMARY_market_clock", "grid_fetch_clock_reading"):
        b = a["his_pattern"][key]
        print(f"   [{key}] {b['sessions_with_an_entry']} of {b['sessions_in_grid']} sessions have an entry")
        for name in STRUCTS:
            c = b["cells"][name]
            for ex in (f"exit_plus_{HOLD_MIN}m_at_bid", "exit_settle_grid_convention"):
                s = c[ex]
                if not s["n_sessions"]:
                    print(f"     {name:<10} {ex:<28} n=0"); continue
                print(f"     {name:<10} {ex:<28} n={s['n_sessions']:>2}  mean {s['mean_pct']:+7.1f}%  med {s['median_pct']:+7.1f}%  "
                      f"win {s['win_pct']:5.1f}%  avgW {s['avg_win_pct']}  avgL {s['avg_loss_pct']}  L/W {s['loss_over_win_ratio']}")
    fgh = a["first_green_shape"]["headline_10:00_ET"]
    print(f"   FIRST-GREEN @10:00 ET: rows {fgh.get('n_rows')} / sessions {fgh.get('n_sessions')}  win {fgh.get('win_pct')}%  "
          f"avgW {fgh.get('avg_win_pct')}  avgL {fgh.get('avg_loss_pct')}  L/W {fgh.get('loss_over_win_ratio')}")
    print(f"   settle-reference check: {a['settle_reference_check']}")
    print(f"   extra looks added: {a['looks_added']['total']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Entry x exit grid of naked 0DTE SPY legs (descriptive; paper only).")
    ap.add_argument("--out", default=OUT,
                    help="output JSON. The default is the REGISTERED results/entry_exit_grid.json - pass a NEW path to refresh without overwriting it")
    ap.add_argument("--through", default=None, help="cap the DATA RANGE at this session date (YYYY-MM-DD); default: every recorded session")
    ap.add_argument("--added", action="store_true", help="also compute the cells ADDED 2026-09-29 (his 10:25 pattern; FIRST-GREEN shape)")
    a = ap.parse_args()
    if (a.added or a.through) and os.path.abspath(a.out) == os.path.abspath(OUT):
        raise SystemExit("REFUSED: --added/--through would overwrite the registered results/entry_exit_grid.json; pass a NEW --out")
    run(out_path=a.out, through=a.through, added=a.added)

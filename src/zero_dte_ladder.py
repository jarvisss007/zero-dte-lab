"""Track D — naked 0DTE SPY call AND put, one entry, every exit horizon scored. Paper only.

Anupam, 2026-08-30: "0DTE can also take naked options like calls and puts and exit
within the next 5-10-15-20-30 min based upon the move, until there is a change in
direction or something that makes it not continue."

WHAT THIS BUILDS AND WHAT IT REFUSES TO BUILD. The 5/10/15/20/30-minute exits are
measurable: the recorder snapshots the chain every ~5 minutes with bid and ask, so each
horizon's exit is computable from recorded data at the EXECUTABLE price (sell at bid).
The reactive half — "until a change in direction" — is not a rule until it is defined
mechanically before the outcome exists; as stated it is discretion wearing a rule's
clothes, the defect this desk convicts as "a horizon changed mid-flight". So Track D
takes ONE entry and scores ALL exits simultaneously as a counterfactual ladder. No exit
is chosen; every exit is measured. After 30 sessions the ladder says which horizon fits
the desk's own tape, and a reactive rule can then be pre-registered with a mechanical
trigger it must name in advance.

CONSTRUCTION. At the first snapshot (ZDTE-003 — what was actually knowable at the call):
buy the ATM call at the ask AND buy the ATM put at the ask, as two separate naked rows.
Together they decompose the Track C straddle: C measures the price of movement, D
measures whether either DIRECTION pays after the same premium. For each leg, at each of
+5/+10/+15/+20/+30 minutes, the exit is that snapshot's BID for the same contract; at
settle it is |close − K| for the ITM leg and zero for the other.

COUNT ENTRY DAYS, NEVER ROWS. Two legs × six exits = twelve numbers per session and ONE
independent observation. The book stores one row per leg and the ladder inside the row,
so a row count of 2n cannot masquerade as 2n observations — n_days is the only n.

EXPECTED TO LOSE ON BOTH LEGS. The lab measured implied above realized in every bucket
(−$43.10/straddle, t = −2.65) and the open is the most expensive hour to hold. A naked
leg pays the same U-shaped premium and adds direction risk. If either side of the ladder
is positive at n>=30, that contradicts the lab's own measurement — and the contradiction
would be the finding. Sim-only until the Rule 7 gate; Rule 4 bars live 0DTE regardless.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAINS = os.path.join(BASE, os.environ.get("ZDTE_CHAINS", os.path.join("data", "chains")))  # CI sets ZDTE_CHAINS=data/chains_ci
BOOK = os.path.join(BASE, "data", "track_d.json")
HORIZONS = (5, 10, 15, 20, 30)
MIN_OI = 50
MAX_SPREAD_PCT = 0.35


def _snapshots(day):
    p = os.path.join(CHAINS, f"SPY_{day}.csv")
    if not os.path.exists(p):
        return None, f"no chain file for {day}"
    rows = list(csv.DictReader(open(p)))
    if not rows:
        return None, f"chain file for {day} is empty"
    by = {}
    for r in rows:
        by.setdefault(r["fetched_at_et"], []).append(r)
    return dict(sorted(by.items())), ""


def _leg_ok(o):
    try:
        bid, ask, oi = float(o["bid"] or 0), float(o["ask"] or 0), float(o["open_interest"] or 0)
    except ValueError:
        return False
    if bid <= 0 or ask <= 0 or oi < MIN_OI:
        return False
    mid = (bid + ask) / 2
    return mid > 0 and (ask - bid) / mid <= MAX_SPREAD_PCT


def load():
    return json.load(open(BOOK)) if os.path.exists(BOOK) else []


def save(rows):
    json.dump(rows, open(BOOK, "w"), indent=1)


def register(day=None):
    day = day or dt.date.today().isoformat()
    if dt.date.fromisoformat(day).weekday() > 4:
        return f"REFUSED: {day} is a weekend"
    book = load()
    if any(r["session"] == day for r in book):
        return f"REFUSED: {day} already registered — one entry per session"
    snaps, err = _snapshots(day)
    if err:
        return f"REFUSED: {err}"
    first = next(iter(snaps))
    snap = [r for r in snaps[first] if r.get("expiry") == day]
    if not snap:
        return f"REFUSED: no 0DTE contracts in the first snapshot"
    spot = float(snap[0]["spot"])
    by = {}
    for r in snap:
        if _leg_ok(r):
            try:
                by.setdefault(float(r["strike"]), {})[r["type"]] = r
            except ValueError:
                pass
    pairs = [k for k, v in by.items() if "C" in v and "P" in v]
    if not pairs:
        return "REFUSED: no strike had a quotable two-sided C and P in the first snapshot"
    k = min(pairs, key=lambda x: abs(x - spot))
    new = []
    for cp in ("C", "P"):
        o = by[k][cp]
        new.append({
            "session": day, "structure_id": f"TD-SPY-{day.replace('-', '')}-{cp}",
            "track": "D", "underlying": "SPY", "expiry": day, "type": cp,
            "strike": k, "spot_at_entry": round(spot, 2),
            "entered_at_snapshot": first,
            "entry_ask": float(o["ask"]), "entry_bid_at_entry": float(o["bid"]),
            "entry_basis": "EXECUTABLE (bought at the ask)",
            "ladder": {}, "settle_value": "", "outcome": "",
        })
    book.extend(new)
    save(book)
    c, p = new[0], new[1]
    return (f"REGISTERED {day}: naked {k:g}C @{c['entry_ask']:.2f} + naked {k:g}P "
            f"@{p['entry_ask']:.2f} (spot {spot:.2f}, first snapshot {first}) — one entry "
            f"day, ladder scores at +{'/'.join(map(str, HORIZONS))}min and settle")


def score(day=None):
    day = day or dt.date.today().isoformat()
    book = load()
    done = 0
    cache = {}
    for r in book:
        if r.get("outcome") or r["session"] > day:
            continue
        if r["session"] not in cache:
            cache[r["session"]] = _snapshots(r["session"])[0]
        snaps = cache[r["session"]]
        if not snaps:
            continue
        stamps = list(snaps)
        last = stamps[-1]
        if r["session"] == day and last[-8:] < "15:55:00":
            continue                       # session not over yet — same guard as Track C
        t0 = dt.datetime.strptime(r["entered_at_snapshot"], "%Y-%m-%d %H:%M:%S")
        lad = {}
        for h in HORIZONS:
            target = t0 + dt.timedelta(minutes=h)
            # nearest snapshot AT OR AFTER the horizon — never before it, which would be
            # an exit taken earlier than the rule allows
            cand = [s for s in stamps
                    if dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") >= target]
            if not cand:
                lad[f"+{h}m"] = {"note": "no snapshot at or after this horizon"}
                continue
            at = cand[0]
            legs = [x for x in snaps[at] if x.get("expiry") == r["session"]
                    and x.get("type") == r["type"]
                    and abs(float(x["strike"] or 0) - r["strike"]) < 1e-9]
            if not legs or not (legs[0].get("bid") or "").strip():
                lad[f"+{h}m"] = {"note": "contract not quoted at this snapshot"}
                continue
            bid = float(legs[0]["bid"])
            pnl = bid - r["entry_ask"]
            lad[f"+{h}m"] = {"exit_bid": bid, "at": at[-8:],
                             "pnl": round(pnl, 2),
                             "pnl_pct": round(pnl / r["entry_ask"] * 100, 1)}
        close = float(snaps[last][0]["spot"])
        itm = (close > r["strike"]) if r["type"] == "C" else (close < r["strike"])
        sv = abs(close - r["strike"]) if itm else 0.0
        spnl = sv - r["entry_ask"]
        r["ladder"] = lad
        # FIRST-GREEN, the one mechanical form of "exit when good": first checkpoint
        # whose bid beats the entry ask, else ride to settle. Computed, never chosen.
        _g = next((lad[f"+{h}m"] for h in HORIZONS
                   if f"+{h}m" in lad and lad[f"+{h}m"].get("pnl", -1) > 0), None)
        r["first_green"] = ({"exit": "settle", "pnl_pct": round(spnl / r["entry_ask"] * 100, 1)}
                            if _g is None else
                            {"exit": _g["at"], "pnl_pct": _g["pnl_pct"]})
        r["settle_value"] = round(sv, 2)
        r["outcome"] = (
            f"SETTLE {spnl / r['entry_ask'] * 100:+.1f}% | close {close:.2f} vs {r['strike']:g}"
            f"{r['type']} -> worth {sv:.2f} against {r['entry_ask']:.2f} at the ask. Close "
            f"from the session's last snapshot ({last[-8:]}), not an official settle. "
            f"Ladder holds the +{'/'.join(map(str, HORIZONS))}min executable exits.")
        done += 1
    if done:
        save(book)
    sc = [r for r in book if r.get("outcome")]
    days = len({r["session"] for r in sc})
    out = [f"Track D: scored {done} legs this run; {len(sc)} legs over {days} entry days"]
    if sc:
        import statistics as st
        out.append("  horizon    mean%   win     (both legs pooled — direction-free read)")
        for h in [f"+{x}m" for x in HORIZONS] + ["settle"]:
            if h == "settle":
                v = [ (r["settle_value"] - r["entry_ask"]) / r["entry_ask"] * 100 for r in sc]
            else:
                v = [r["ladder"][h]["pnl_pct"] for r in sc
                     if h in r.get("ladder", {}) and "pnl_pct" in r["ladder"][h]]
            if v:
                out.append(f"  {h:<9} {st.mean(v):+7.1f}  {sum(1 for x in v if x > 0)}/{len(v)}")
        if days < 30:
            out.append(f"  NOT READABLE: {days}/30 entry days. Twelve numbers per session "
                       f"are ONE observation; n_days is the only n.")
    return "\n".join(out)


if __name__ == "__main__":
    # SESSION-001 (2026-09-05): a holiday is not a session. This job fires on weekday crons
    # (launchd 07:12/07:18 PT, CI 09:55 ET); on Labor Day it would have registered a row
    # dated a day SPY never traded, off a chain book that was Friday's. The calendar
    # decides, not the weekday — src/sessions.py is a byte-identical mirror of
    # stock-radar/sessions.py (the resolver check sessions_calendar enforces that).
    import sessions
    if not sessions.is_session(dt.date.today()):
        print(sessions.status_line()); print(f"{os.path.basename(__file__)}: skipped — no session today.")
        sys.exit(0)
    if "--score" in sys.argv:
        print(score())
    else:
        print(register())
        print(score())

"""Track C — one 0DTE SPY straddle per session, entered at the first snapshot, held to settle.

Anupam, 2026-08-30: "zero DTE options, SPY ETF, trade it on an everyday basis." Paper
only — Constitution Rule 4 bars live short-dated options and sim-only stands until the
Rule 7 gate. Nothing here is a recommendation; it is a registered experiment.

WHY THIS IS WORTH RUNNING, given the lab already has an answer.

src/straddle_test.py measured the 0DTE straddle RETROSPECTIVELY over 17 usable sessions:
implied above realized in every time bucket, net -$43.10 per straddle, t = -2.65. That
is a backward-looking result on a sample the lab chose after the fact. Track C is the
same question asked FORWARD, one session at a time, pre-registered, with the entry fixed
before the outcome exists. A retrospective finding and a forward book are different kinds
of evidence, and this desk's standing law is that the forward record is the one that
counts.

WHY A STRADDLE. The claim under test is about what the market CHARGES for a day's
movement, not about direction. A straddle pays |close - K| and is indifferent to which
way SPY goes, so the result cannot be contaminated by whether some entry signal happened
to be right. A directional 0DTE call answers two questions and separates neither.

WHY 0DTE IS THE CLEANEST MEASUREMENT ON THE DESK. The option expires the same session it
was opened. Its exit value is |close - K| against the settlement price — not a mid, not a
spread, not a mark taken at some chosen moment. There is no overnight gap and no
marking judgment. Track A (near-expiry) already scores at settle; Track C does it in one
day, so the book accrues an independent observation every session.

ENTRY IS THE FIRST SNAPSHOT OF THE SESSION (ZDTE-003). CBOE's free delayed feed does not
publish a fresh book until roughly 09:45 ET, so the first snapshot is what was actually
knowable at the call. Using a later one would be choosing an entry after seeing part of
the day — the exact leak ZDTE-004 was raised about.

ENTRY PRICE IS THE EXECUTABLE DEBIT: both legs bought at the ASK. Mid is not a fill. The
lab's own straddle test uses the recorded ask for the same reason.

THE ENTRY TIME IS THE MOST EXPENSIVE ONE, DELIBERATELY. The lab's own README records
that "the open is the most expensive hour to hold... the market maker prices the
U-shape". Entering at the first snapshot therefore buys at the worst moment of the day
by construction. That cost is accepted rather than optimised away, because any cheaper
entry would be chosen AFTER seeing part of the session — the leak ZDTE-004 was raised
about. A book that picks its hour after the fact measures the picker, not the market.

VALIDATION, NOT EVIDENCE. Replaying this exact rule over the 8 recorded sessions
2026-08-19..08-28 (in a throwaway book, never the real one) returns 0 wins in 8, mean
-42.4%, -1.20 points per straddle. That confirms the CODE runs and the settle arithmetic
is sane. It is retrospective, n=8, and on the most expensive entry hour, so it proves
nothing about the market and is recorded here only so nobody later mistakes it for a
result.

EXPECTED TO LOSE. If this book ends positive over 30+ sessions it contradicts the lab's
own measurement and the contradiction is the finding. If it ends negative it confirms,
forward and out-of-sample, that the desk cannot buy a day's movement for less than it is
worth. Either way the row was written before the close.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAINS = os.path.join(BASE, "data", "chains")
BOOK = os.path.join(BASE, "data", "track_c.json")
MIN_OI = 50
MAX_SPREAD_PCT = 0.35


def first_snapshot(day):
    """Every contract from the EARLIEST snapshot in the day's chain file."""
    p = os.path.join(CHAINS, f"SPY_{day}.csv")
    if not os.path.exists(p):
        return None, None, f"no chain file for {day} — the recorder did not run"
    rows = list(csv.DictReader(open(p)))
    if not rows:
        return None, None, f"chain file for {day} is empty"
    snaps = sorted({r["fetched_at_et"] for r in rows})
    first = snaps[0]
    return [r for r in rows if r["fetched_at_et"] == first], first, ""


def leg_ok(o):
    try:
        bid, ask, oi = float(o["bid"] or 0), float(o["ask"] or 0), float(o["open_interest"] or 0)
    except ValueError:
        return False
    if bid <= 0 or ask <= 0 or oi < MIN_OI:
        return False
    mid = (bid + ask) / 2
    return mid > 0 and (ask - bid) / mid <= MAX_SPREAD_PCT


def pick(snap, day):
    """ATM straddle on the 0DTE expiry, both legs at the ask."""
    same = [r for r in snap if r.get("expiry") == day]
    if not same:
        return None, f"no contracts expiring {day} in the first snapshot — not a 0DTE session"
    try:
        spot = float(same[0]["spot"])
    except (ValueError, KeyError):
        return None, "first snapshot carries no usable spot"
    by = {}
    for r in same:
        if not leg_ok(r):
            continue
        try:
            k = float(r["strike"])
        except ValueError:
            continue
        by.setdefault(k, {})[r["type"]] = r
    pairs = [k for k, v in by.items() if "C" in v and "P" in v]
    if not pairs:
        return None, "no strike had a quotable two-sided call AND put in the first snapshot"
    k = min(pairs, key=lambda x: abs(x - spot))
    c, p = by[k]["C"], by[k]["P"]
    debit = float(c["ask"]) + float(p["ask"])
    mid = (float(c["bid"]) + float(c["ask"]) + float(p["bid"]) + float(p["ask"])) / 2
    if debit <= 0:
        return None, "computed a non-positive debit"
    return dict(strike=k, spot=spot, debit=debit, mid=mid,
                call_ask=float(c["ask"]), put_ask=float(p["ask"]),
                breakeven_pct=debit / spot * 100), ""


def load():
    return json.load(open(BOOK)) if os.path.exists(BOOK) else []


def save(rows):
    json.dump(rows, open(BOOK, "w"), indent=1)


def register(day=None):
    day = day or dt.date.today().isoformat()
    if dt.date.fromisoformat(day).weekday() > 4:
        return f"REFUSED: {day} is a weekend — no session"
    book = load()
    if any(r["session"] == day for r in book):
        return f"REFUSED: {day} already has a Track C row — one per session, a second would cluster the sample"
    snap, stamp, err = first_snapshot(day)
    if err:
        return f"REFUSED: {err}"
    s, err = pick(snap, day)
    if err:
        return f"REFUSED: {err}"
    row = {
        "session": day, "structure_id": f"TC-SPY-{day.replace('-', '')}",
        "track": "C", "underlying": "SPY", "expiry": day,
        "entered_at_snapshot": stamp,
        "legs": f"BUY {s['strike']:g}C @{s['call_ask']:.2f} / BUY {s['strike']:g}P @{s['put_ask']:.2f}",
        "strike": s["strike"], "spot_at_entry": round(s["spot"], 2),
        "entry_debit": round(s["debit"], 2), "entry_basis": "EXECUTABLE (both legs at ask)",
        "mid_debit": round(s["mid"], 2),
        "breakeven_move_pct": round(s["breakeven_pct"], 3),
        "settle_close": "", "settle_value": "", "pnl": "", "pnl_pct": "", "outcome": "",
        "thesis_why": ("Registered forward test of the lab's own retrospective finding: "
                       "straddle_test measured implied above realized in every bucket, "
                       "-$43.10/straddle at t=-2.65 over 17 sessions. Expected to LOSE. "
                       "Entered at the FIRST snapshot of the session (ZDTE-003) at the "
                       "executable debit; scored at settle as |close - K|, never a mark."),
    }
    book.append(row)
    save(book)
    return (f"REGISTERED {row['structure_id']}: {row['legs']} · debit {row['entry_debit']} "
            f"(mid {row['mid_debit']}) · needs {row['breakeven_move_pct']:.2f}% by the close "
            f"· first snapshot {stamp} · book {len(book)} rows")


def score(day=None):
    """Score any matured row off the day's SETTLE. |close - K| is arithmetic, not a mark."""
    day = day or dt.date.today().isoformat()
    book = load()
    done = []
    for r in book:
        if r.get("outcome") or r["session"] > day:
            continue
        rows = list(csv.DictReader(open(os.path.join(CHAINS, f"SPY_{r['session']}.csv"))))
        if not rows:
            continue
        last = max(x["fetched_at_et"] for x in rows)
        spots = [float(x["spot"]) for x in rows if x["fetched_at_et"] == last and x.get("spot")]
        if not spots:
            continue
        close = spots[0]
        # The final snapshot is ~16:04 ET, after the 16:00 settle. It is the closest the
        # free feed gets to a settlement print, and the row says so rather than implying
        # an official settle it does not have.
        value = abs(close - r["strike"])
        pnl = value - r["entry_debit"]
        r["settle_close"] = round(close, 2)
        r["settle_value"] = round(value, 2)
        r["pnl"] = round(pnl, 2)
        r["pnl_pct"] = round(pnl / r["entry_debit"] * 100, 1)
        r["outcome"] = (
            f"{'WIN' if pnl > 0 else 'LOSS'} {pnl / r['entry_debit'] * 100:+.1f}% | SETTLE. "
            f"SPY {close:.2f} against strike {r['strike']:g} = |{close:.2f}-{r['strike']:g}| "
            f"= {value:.2f} against a {r['entry_debit']:.2f} executable debit. Close taken "
            f"from the session's LAST snapshot ({last}), the nearest the free feed gets to "
            f"a settlement print — not an official settle.")
        done.append(r["structure_id"])
    if done:
        save(book)
    sc = [r for r in book if r.get("outcome")]
    out = [f"Track C: scored {len(done)} this run; {len(sc)}/{len(book)} sessions closed"]
    if sc:
        import statistics as st
        p = [r["pnl_pct"] for r in sc]
        d = [r["pnl"] for r in sc]
        out.append(f"  n={len(p)} sessions (rows ARE independent days) "
                   f"win {sum(1 for x in p if x > 0)}/{len(p)} "
                   f"mean {st.mean(p):+.1f}% median {st.median(p):+.1f}% "
                   f"mean $ {st.mean(d):+.2f}/straddle")
        if len(p) < 30:
            out.append(f"  NOT READABLE: {len(p)}/30 sessions. The lab's retrospective "
                       f"figure is -$43.10 at t=-2.65; this book cannot confirm or "
                       f"contradict it yet.")
    return "\n".join(out)


if __name__ == "__main__":
    if "--score" in sys.argv:
        print(score())
    else:
        print(register())
        print(score())

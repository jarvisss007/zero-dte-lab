#!/opt/anaconda3/bin/python
"""PTR-001 runner - the simulated paper trader on the IE Pro trigger. PAPER ONLY: no broker, no key, no order of any kind.
Implements PREREG_IE_PRO_PAPER.md exactly; read that document first. A plain script (zero Claude credits).

  paper_runner.py                     run the last SETTLED session (what launchd calls, ~13:40 PT and a 14:20 retry)
  paper_runner.py --session YYYY-MM-DD  run one named session (catch-up)
  paper_runner.py --shakedown A B     replay recorded sessions A..B into data/paper/shakedown/ - SHAKEDOWN, NOT COUNTED,
                                      exit reason / exit price / P&L REDACTED (the prereg keeps real outcomes unseen until
                                      the counted sessions); only invariants are checked

Refuses to run if a frozen file's hash differs (results/PTR-001_FREEZE_HASHES.txt) or if its own hash differs from the one
pinned at the APPROVED stamp. Every run writes one heartbeat row; a run with no new settled session writes nothing else.
Book writes are atomic (src/atomicio.py, BOOK-001).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(HERE))
import atomicio  # noqa: E402
import ie_pro_trigger as P  # noqa: E402
import paper_bars as B  # noqa: E402
import sessions  # noqa: E402

ET = "America/New_York"
PAPER = LAB / "data" / "paper"
FREEZE = LAB / "results" / "PTR-001_FREEZE_HASHES.txt"
APPROVAL = PAPER / "APPROVED.json"
RETIRED = PAPER / "RETIRED.json"
SEED = PAPER / "bars_seed_2026-10-09.csv"

# ---- frozen by PREREG_IE_PRO_PAPER.md (any change = a new registered variant) -------------------------------
CAPITAL, BUDGET = 5000.0, 1000.0
FEE, FEE_SENS = 0.36, 0.65            # per contract per side; sensitivity rate printed descriptively
STOP_MULT, TARGET_MULT, CLOCK_MIN = 0.70, 1.50, 60
FILL_WINDOW_MIN, LAG_MIN, LAG_MAX = 10, 10, 25
SESSION_CAP = 5
BARS_FRAC, BOOK_FRAC = 0.90, 0.75
KILL_NET = -1500.0
VARIANT = "PTR-001"

TRADE_COLS = ["variant", "label", "session", "signal_bar_open_et", "decision_et", "side", "grade", "sig_close", "ind_sl", "ind_tp1",
              "ind_tp2", "fill_quote_ts", "spot_at_fill", "type", "strike", "bid_entry", "ask_entry", "ask_size", "contracts",
              "size_exceeds_ask_size", "entry_fee", "exit_reason", "exit_quote_ts", "exit_bid", "exit_price", "exit_fee", "gross",
              "net", "net_pct", "net_pct_fee065", "min_bid_held", "max_bid_held", "invariants_ok", "twin_status", "twin_type",
              "twin_strike", "twin_ask", "twin_contracts", "twin_exit_reason", "twin_net", "twin_net_pct"]
SKIP_COLS = ["variant", "label", "session", "decision_et", "side", "reason", "detail"]
SIG_COLS = ["session", "bar_open_et", "sig", "grade", "close", "ind_sl", "ind_tp1", "ind_tp2", "tradable"]
SESS_COLS = ["variant", "label", "session", "status", "bars_frac", "book_frac", "n_signals", "n_tradable", "n_filled",
             "n_skipped", "net", "cum_net", "note"]
HB_COLS = ["run_at_et", "mode", "session", "status", "detail"]


class Refuse(RuntimeError):
    """A frozen-file or consistency refusal. Fails LOUD: nothing is written except the heartbeat."""


# =============================================================================================================
# identity / approval
# =============================================================================================================
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_freeze() -> None:
    bad = []
    for line in FREEZE.read_text().splitlines():
        if not line.strip():
            continue
        h, rel = line.split(None, 1)
        if sha256_file(LAB / rel.strip()) != h:
            bad.append(rel.strip())
    if bad:
        raise Refuse(f"FROZEN FILE CHANGED: {bad} - a change is a new registered variant, not an edit")
    ap = read_approval()
    if ap and ap.get("runner_sha256") and ap["runner_sha256"] != sha256_file(Path(__file__)):
        raise Refuse("paper_runner.py differs from the hash pinned at the APPROVED stamp")


def read_approval() -> dict | None:
    return json.loads(APPROVAL.read_text()) if APPROVAL.exists() else None


# =============================================================================================================
# books
# =============================================================================================================
def _naive_et(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.tz_localize(ET)


def load_chain_books(day: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """CBOE-only files for the day (never *.yfinance.csv, ZDTE-011). Returns (rows, books): rows = valid-book contract quotes
    deduped on (quote_ts, expiry, type, strike); books = one line per distinct quote_ts with its first-fetch lag and validity."""
    frames = []
    for d in ("chains", "chains_ci"):
        p = LAB / "data" / d / f"SPY_{day}.csv"
        if p.exists():
            frames.append(pd.read_csv(p))
    if not frames:
        empty = pd.DataFrame(columns=["quote_ts", "first_fetch", "lag_min", "valid"])
        return pd.DataFrame(), empty
    x = pd.concat(frames, ignore_index=True)
    x["quote_ts"] = _naive_et(x["quote_ts"])
    x["fetched"] = _naive_et(x["fetched_at_et"])
    books = x.groupby("quote_ts", as_index=False).agg(first_fetch=("fetched", "min"))
    books["lag_min"] = (books["first_fetch"] - books["quote_ts"]).dt.total_seconds() / 60.0
    books["valid"] = books["lag_min"].between(LAG_MIN, LAG_MAX)
    x = x[x["quote_ts"].isin(books.loc[books["valid"], "quote_ts"])]
    x = x[x["expiry"].astype(str) == day]
    x = x.sort_values(["quote_ts", "fetched"]).drop_duplicates(["quote_ts", "expiry", "type", "strike"], keep="first")
    return x.reset_index(drop=True), books


def day_close(day: str) -> pd.Timestamp:
    return pd.Timestamp.combine(pd.Timestamp(day).date(), B.close_et(day)).tz_localize(ET)


def day_open(day: str) -> pd.Timestamp:
    return pd.Timestamp.combine(pd.Timestamp(day).date(), dt.time(9, 30)).tz_localize(ET)


def coverage(day: str, bars: pd.DataFrame, books: pd.DataFrame) -> tuple[float, float]:
    op, cl = day_open(day), day_close(day)
    exp_bars = (cl - op).total_seconds() / 300.0
    have = ((bars["ts"] >= op) & (bars["ts"] < cl)).sum()
    exp_books = (cl - (op + pd.Timedelta(minutes=5))).total_seconds() / 300.0
    ok = books[books["valid"] & (books["quote_ts"] >= op + pd.Timedelta(minutes=5)) & (books["quote_ts"] <= cl)]
    return float(have / exp_bars), float(len(ok) / exp_books)


# =============================================================================================================
# the trading rules (pure functions; unit-tested on synthetic fixtures)
# =============================================================================================================
def pick_strike(snap: pd.DataFrame, typ: str, spot: float) -> float | None:
    s = snap[snap["type"] == typ]["strike"]
    if typ == "C":
        s = s[s > spot]
        return float(s.min()) if len(s) else None
    s = s[s < spot]
    return float(s.max()) if len(s) else None


def two_sided(bid: float, ask: float) -> bool:
    return bool(np.isfinite(bid) and np.isfinite(ask) and bid > 0 and ask > 0 and bid <= ask)


def contracts_for(ask: float) -> int:
    return int(math.floor(BUDGET / (ask * 100.0)))


def contract_path(rows: pd.DataFrame, typ: str, strike: float, after: pd.Timestamp) -> pd.DataFrame:
    """Valid LATER snapshots of the same contract, in time order. A NaN or crossed quote is skipped; bid == 0 is valid."""
    p = rows[(rows["type"] == typ) & (rows["strike"] == strike) & (rows["quote_ts"] > after)].copy()
    p = p[np.isfinite(p["bid"]) & np.isfinite(p["ask"]) & (p["bid"] >= 0) & (p["bid"] <= p["ask"])]
    return p.sort_values("quote_ts")


def simulate_exit(entry_ts: pd.Timestamp, entry_ask: float, path: pd.DataFrame) -> dict:
    """Section 6, in order, against the BID: TARGET (fill at the line) -> STOP (fill at that snapshot's bid) -> CLOCK -> BOOK_END."""
    target, stop = TARGET_MULT * entry_ask, STOP_MULT * entry_ask
    for _, r in path.iterrows():
        if r["bid"] >= target:
            return dict(reason="TARGET", ts=r["quote_ts"], bid=float(r["bid"]), price=float(target))
        if r["bid"] <= stop:
            return dict(reason="STOP", ts=r["quote_ts"], bid=float(r["bid"]), price=float(r["bid"]))
        if r["quote_ts"] >= entry_ts + pd.Timedelta(minutes=CLOCK_MIN):
            return dict(reason="CLOCK", ts=r["quote_ts"], bid=float(r["bid"]), price=float(r["bid"]))
    last = path.iloc[-1]
    return dict(reason="BOOK_END", ts=last["quote_ts"], bid=float(last["bid"]), price=float(last["bid"]))


def money(entry_ask: float, contracts: int, exit_price: float, fee: float = FEE) -> tuple[float, float, float]:
    gross = (exit_price - entry_ask) * 100.0 * contracts
    net = gross - 2.0 * fee * contracts
    return gross, net, net / (entry_ask * 100.0 * contracts)


def fill_leg(rows: pd.DataFrame, books_ts: pd.Timestamp, typ: str, spot: float) -> dict:
    """Entry for one leg at one snapshot: strike, two-sided test, size, later path. Returns {'skip': reason} or the leg."""
    snap = rows[rows["quote_ts"] == books_ts]
    strike = pick_strike(snap, typ, spot)
    if strike is None:
        return {"skip": "NO_TWO_SIDED_MARKET", "detail": f"no {typ} strike on the OTM side of {spot}"}
    q = snap[(snap["type"] == typ) & (snap["strike"] == strike)].iloc[0]
    bid, ask = float(q["bid"]), float(q["ask"])
    if not two_sided(bid, ask):
        return {"skip": "NO_TWO_SIDED_MARKET", "detail": f"{typ} {strike} bid {bid} ask {ask}"}
    n = contracts_for(ask)
    if n < 1:
        return {"skip": "TOO_EXPENSIVE", "detail": f"ask {ask}"}
    path = contract_path(rows, typ, strike, books_ts)
    if path.empty:
        return {"skip": "NO_LATER_BOOK", "detail": f"{typ} {strike}"}
    ex = simulate_exit(books_ts, ask, path)
    gross, net, pct = money(ask, n, ex["price"])
    _, _, pct65 = money(ask, n, ex["price"], FEE_SENS)
    return dict(type=typ, strike=strike, bid=bid, ask=ask, ask_size=float(q["ask_size"]), contracts=n, ex=ex, gross=gross, net=net,
                pct=pct, pct65=pct65, min_bid=float(path["bid"].min()), max_bid=float(path["bid"].max()))


def process_session(day: str, sig_rows: pd.DataFrame, rows: pd.DataFrame, books: pd.DataFrame, label: str, redact: bool,
                    trade_allowed: bool = True) -> tuple[list[dict], list[dict]]:
    """Section 4's ordered skips. sig_rows: this session's TRADABLE signals in time order (ts, sig, grade, E, SL, TP1, TP2)."""
    trades, skips = [], []
    cl = day_close(day)
    valid_ts = sorted(books.loc[books["valid"], "quote_ts"]) if len(books) else []
    open_until = None
    for _, s in sig_rows.sort_values("ts").iterrows():
        decision = s["ts"] + pd.Timedelta(minutes=5)
        side = "long" if s["sig"] > 0 else "short"
        base = dict(variant=VARIANT, label=label, session=day, decision_et=decision.isoformat(), side=side)

        def skip(reason, detail=""):
            skips.append({**base, "reason": reason, "detail": detail})

        if not trade_allowed:
            skip("RETIRED_SHADOW", "kill line reached; recording only"); continue
        if len(trades) >= SESSION_CAP:
            skip("SESSION_CAP"); continue
        if open_until is not None and decision < open_until:
            skip("POSITION_OPEN", f"open until {open_until.isoformat()}"); continue
        cand = [t for t in valid_ts if decision <= t <= decision + pd.Timedelta(minutes=FILL_WINDOW_MIN) and t < cl - pd.Timedelta(minutes=5)]
        if not cand:
            skip("NO_BOOK_WINDOW"); continue
        ts = cand[0]
        spot = float(rows.loc[rows["quote_ts"] == ts, "spot"].iloc[0])
        typ = "C" if s["sig"] > 0 else "P"
        main = fill_leg(rows, ts, typ, spot)
        if "skip" in main:
            skip(main["skip"], main["detail"]); continue
        twin = fill_leg(rows, ts, "P" if typ == "C" else "C", spot)
        ex = main["ex"]
        ok = (ex["ts"] > ts and ex["reason"] in ("TARGET", "STOP", "CLOCK", "BOOK_END") and main["contracts"] >= 1)
        hid = ""  # redacted cell in the shakedown
        row = {**base, "signal_bar_open_et": s["ts"].isoformat(), "grade": s["grade"], "sig_close": round(float(s["E"]), 4),
               "ind_sl": round(float(s["SL"]), 4), "ind_tp1": round(float(s["TP1"]), 4), "ind_tp2": round(float(s["TP2"]), 4),
               "fill_quote_ts": ts.isoformat(), "spot_at_fill": spot, "type": typ, "strike": main["strike"], "bid_entry": main["bid"],
               "ask_entry": main["ask"], "ask_size": main["ask_size"], "contracts": main["contracts"],
               "size_exceeds_ask_size": bool(main["contracts"] > main["ask_size"]), "entry_fee": round(FEE * main["contracts"], 2),
               "invariants_ok": bool(ok),
               "exit_reason": hid if redact else ex["reason"], "exit_quote_ts": hid if redact else ex["ts"].isoformat(),
               "exit_bid": hid if redact else ex["bid"], "exit_price": hid if redact else round(ex["price"], 4),
               "exit_fee": hid if redact else round(FEE * main["contracts"], 2), "gross": hid if redact else round(main["gross"], 2),
               "net": hid if redact else round(main["net"], 2), "net_pct": hid if redact else round(main["pct"], 6),
               "net_pct_fee065": hid if redact else round(main["pct65"], 6), "min_bid_held": hid if redact else main["min_bid"],
               "max_bid_held": hid if redact else main["max_bid"]}
        if "skip" in twin:
            row.update(twin_status="UNFILLABLE:" + twin["skip"])
        else:
            row.update(twin_status="OK", twin_type=twin["type"], twin_strike=twin["strike"], twin_ask=twin["ask"],
                       twin_contracts=twin["contracts"], twin_exit_reason=hid if redact else twin["ex"]["reason"],
                       twin_net=hid if redact else round(twin["net"], 2), twin_net_pct=hid if redact else round(twin["pct"], 6))
        trades.append(row)
        open_until = ex["ts"]
    return trades, skips


# =============================================================================================================
# bars + signals
# =============================================================================================================
def load_series(extra_days: list[str] | None = None) -> pd.DataFrame:
    """Seed + archived per-session raw bars (first write wins on a duplicate timestamp), then the frozen clean()."""
    frames = [B.load(SEED)]
    for p in sorted((PAPER / "bars").glob("*.csv")):
        frames.append(B.load(p))
    raw = pd.concat(frames, ignore_index=True).drop_duplicates("ts", keep="first").sort_values("ts")
    return B.clean(raw.reset_index(drop=True))


def archive_session_bars(day: str) -> None:
    """Capture the session's raw bars once, after the close, and never rewrite them."""
    p = PAPER / "bars" / f"{day}.csv"
    if p.exists():
        return
    raw = B.fetch_yahoo_5m("5d")
    d = raw[raw["ts"].dt.date == pd.Timestamp(day).date()]
    last = d[d["ts"] < day_close(day)]["ts"].max() if len(d) else None
    if last is None or last < day_close(day) - pd.Timedelta(minutes=5):
        raise Refuse(f"BARS_INCOMPLETE: last regular bar for {day} is {last}; the session is not fully captured yet")
    p.parent.mkdir(parents=True, exist_ok=True)
    atomicio.atomic_write_text(str(p), d.to_csv(index=False))


def session_signals(series: pd.DataFrame, day: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the frozen trigger on the whole series up to `day`. Returns (all signals in the series, this session's TRADABLE ones)."""
    upto = series[series["ts"].dt.date <= pd.Timestamp(day).date()].reset_index(drop=True)
    r = P.run(upto, htf_mode="developing")
    s = r[r["sig"] != 0].copy()
    s["tradable"] = [B.tradable_bar(t) for t in s["ts"]]
    s["session"] = s["ts"].dt.date.astype(str)
    return s, s[(s["session"] == day) & s["tradable"]]


# =============================================================================================================
# book writes
# =============================================================================================================
def append_rows(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomicio.hold_book(str(path))
    old = list(pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records")) if path.exists() else []
    atomicio.atomic_csv(str(path), cols, old + [{c: r.get(c, "") for c in cols} for r in rows])


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame()


def heartbeat(mode: str, day: str, status: str, detail: str = "") -> None:
    now = pd.Timestamp.now(tz=ET).isoformat(timespec="seconds")
    append_rows(PAPER / "heartbeat.csv", HB_COLS, [dict(run_at_et=now, mode=mode, session=day, status=status, detail=detail)])
    print(f"[{now}] {mode} {day}: {status} {detail}")


# =============================================================================================================
# one session
# =============================================================================================================
def run_session(day: str, mode: str) -> str:
    shake = mode == "shakedown"
    out = PAPER / "shakedown" if shake else PAPER
    label = "SHAKEDOWN - NOT COUNTED" if shake else "COUNTED"
    sess = read_csv(out / "sessions.csv")
    if len(sess) and day in set(sess["session"]):
        heartbeat(mode, day, "NO_NEW_SESSION", "already recorded")
        return "NO_NEW_SESSION"
    ap = read_approval()
    if not shake:
        if ap is None:
            heartbeat(mode, day, "NO_APPROVAL", "no APPROVED stamp: nothing is counted")
            return "NO_APPROVAL"
        if day_open(day) <= pd.Timestamp(ap["approved_at_et"]):
            heartbeat(mode, day, "PRE_APPROVAL", f"session opened before the stamp {ap['approved_at_et']}: not counted")
            return "PRE_APPROVAL"
        archive_session_bars(day)
    series = load_series()
    allsig, tradable = session_signals(series, day)
    # stored signals must be reproduced exactly (BENCH-002): a disagreement fails LOUD, nothing is rewritten
    stored = read_csv(out / "signals.csv")
    if len(stored):
        prev = allsig[allsig["session"].isin(set(stored["session"])) & (allsig["session"] < day)]
        mine = {(t.isoformat(), int(g)) for t, g in zip(prev["ts"], prev["sig"])}
        theirs = {(a, int(b)) for a, b in zip(stored["bar_open_et"], stored["sig"]) if a[:10] < day}
        if mine != theirs:
            raise Refuse(f"SIGNAL_MISMATCH: recompute disagrees with the stored signals ({len(mine ^ theirs)} differ)")
    bars_d = series[series["ts"].dt.date == pd.Timestamp(day).date()]
    rows, books = load_chain_books(day)
    bf, kf = coverage(day, bars_d, books)
    srows = [dict(session=day, bar_open_et=t.isoformat(), sig=int(g), grade=gr, close=round(float(e), 4), ind_sl=round(float(a), 4),
                  ind_tp1=round(float(b), 4), ind_tp2=round(float(c), 4), tradable=bool(tr))
             for t, g, gr, e, a, b, c, tr in zip(*[allsig[allsig["session"] == day][k] for k in
                                                   ("ts", "sig", "grade", "E", "SL", "TP1", "TP2", "tradable")])]
    cum = 0.0
    if len(sess):
        counted = sess[sess["status"] == "COUNTED"]
        cum = float(pd.to_numeric(counted["net"], errors="coerce").fillna(0).sum()) if not shake else 0.0
    status, note = ("DATA_GAP" if (bf < BARS_FRAC or kf < BOOK_FRAC) else "SHAKEDOWN" if shake else "COUNTED"), ""
    if status == "DATA_GAP":
        note = f"bars {bf:.2f} (need {BARS_FRAC}), books {kf:.2f} (need {BOOK_FRAC}): logged, not scored"
    trades, skips = [], []
    if status != "DATA_GAP":
        allowed = not RETIRED.exists() or shake
        trades, skips = process_session(day, tradable, rows, books, label, redact=shake, trade_allowed=allowed)
    net = "" if (shake or status == "DATA_GAP") else round(sum(float(t["net"]) for t in trades), 2)
    if net != "":
        cum += net
    append_rows(out / "signals.csv", SIG_COLS, srows)
    append_rows(out / "trades.csv", TRADE_COLS, trades)
    append_rows(out / "skips.csv", SKIP_COLS, skips)
    append_rows(out / "sessions.csv", SESS_COLS, [dict(variant=VARIANT, label=label, session=day, status=status, bars_frac=round(bf, 3),
                                                       book_frac=round(kf, 3), n_signals=len(srows), n_tradable=len(tradable),
                                                       n_filled=len(trades), n_skipped=len(skips), net=net,
                                                       cum_net=("" if net == "" else round(cum, 2)), note=note)])
    if not shake and status == "COUNTED" and cum <= KILL_NET and not RETIRED.exists():
        atomicio.atomic_json(str(RETIRED), {"retired_at": pd.Timestamp.now(tz=ET).isoformat(), "cum_net": cum, "kill": KILL_NET}, indent=1)
    heartbeat(mode, day, status, f"signals {len(srows)} tradable {len(tradable)} filled {len(trades)} skipped {len(skips)} "
                              f"bars {bf:.2f} books {kf:.2f}" + (" (outcomes redacted)" if shake else ""))
    return status


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session")
    ap.add_argument("--shakedown", nargs=2, metavar=("FIRST", "LAST"))
    a = ap.parse_args()
    PAPER.mkdir(parents=True, exist_ok=True)
    mode, day = ("shakedown", "range") if a.shakedown else ("live", a.session or "")
    try:
        verify_freeze()
        if a.shakedown:
            d0, d1 = pd.Timestamp(a.shakedown[0]).date(), pd.Timestamp(a.shakedown[1]).date()
            for k in range((d1 - d0).days + 1):       # inclusive on both ends (sessions_between excludes the start)
                d = d0 + dt.timedelta(days=k)
                if sessions.is_session(d):
                    run_session(d.isoformat(), "shakedown")
            return 0
        day = day or sessions.settled_session().isoformat()
        if not sessions.is_session(day):
            heartbeat(mode, day, "NO_NEW_SESSION", "not a session")
            return 0
        run_session(day, "live")
        return 0
    except Refuse as e:
        heartbeat(mode, day, "REFUSED", str(e))
        return 2
    except Exception as e:  # fail LOUD, never a clean zero
        heartbeat(mode, day, "ERROR", f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())

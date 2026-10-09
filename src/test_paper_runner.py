"""Synthetic-fixture tests for paper_runner.py. Invented prices only - they never read a recorded chain, so the blind shakedown
(PREREG section 10) can verify the exit code path without anyone seeing a real outcome.
Run: /opt/anaconda3/bin/python -m pytest -q src/test_paper_runner.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_runner as R  # noqa: E402

ET = "America/New_York"
T0 = pd.Timestamp("2026-10-12 10:00:00", tz=ET)


def path(bids, step=5, typ="C", strike=777.0, asks=None):
    rows = []
    for i, b in enumerate(bids):
        rows.append(dict(quote_ts=T0 + pd.Timedelta(minutes=step * (i + 1)), type=typ, strike=strike, bid=b,
                         ask=(asks[i] if asks else (b + 0.02 if np.isfinite(b) else np.nan)), bid_size=1, ask_size=10, spot=776.5))
    return pd.DataFrame(rows)


def test_target_fills_at_the_line_not_the_bid():
    ex = R.simulate_exit(T0, 1.00, R.contract_path(path([0.9, 1.2, 1.9]), "C", 777.0, T0))
    assert ex["reason"] == "TARGET" and ex["price"] == 1.5 and ex["bid"] == 1.9


def test_stop_fills_at_the_gapped_bid():
    ex = R.simulate_exit(T0, 1.00, R.contract_path(path([0.9, 0.40]), "C", 777.0, T0))
    assert ex["reason"] == "STOP" and ex["price"] == 0.40


def test_bid_zero_is_valid_and_stops_at_zero():
    ex = R.simulate_exit(T0, 1.00, R.contract_path(path([0.9, 0.0]), "C", 777.0, T0))
    assert ex["reason"] == "STOP" and ex["price"] == 0.0


def test_stop_line_is_inclusive_target_line_is_inclusive():
    assert R.simulate_exit(T0, 1.00, R.contract_path(path([0.70]), "C", 777.0, T0))["reason"] == "STOP"
    assert R.simulate_exit(T0, 1.00, R.contract_path(path([1.50]), "C", 777.0, T0))["reason"] == "TARGET"


def test_clock_is_inclusive_and_fills_at_the_bid():
    bids = [1.0] * 12  # 5-minute steps: the 12th snapshot is exactly +60 minutes
    ex = R.simulate_exit(T0, 1.00, R.contract_path(path(bids), "C", 777.0, T0))
    assert ex["reason"] == "CLOCK" and ex["ts"] == T0 + pd.Timedelta(minutes=60) and ex["price"] == 1.0


def test_book_end_uses_the_last_valid_snapshot():
    ex = R.simulate_exit(T0, 1.00, R.contract_path(path([1.0, 1.1, 0.95]), "C", 777.0, T0))
    assert ex["reason"] == "BOOK_END" and ex["price"] == 0.95 and ex["ts"] == T0 + pd.Timedelta(minutes=15)


def test_nan_and_crossed_quotes_are_skipped_not_used():
    p = path([1.0, np.nan, 1.0, 1.0], asks=[1.02, np.nan, 0.5, 1.02])  # row 2 NaN, row 3 crossed (bid > ask)
    v = R.contract_path(p, "C", 777.0, T0)
    assert len(v) == 2 and list(v["quote_ts"]) == [T0 + pd.Timedelta(minutes=5), T0 + pd.Timedelta(minutes=20)]


def test_money_and_fees():
    g, n, pct = R.money(1.00, 10, 1.5)
    assert g == 500.0 and n == 500.0 - 2 * 0.36 * 10 and abs(pct - n / 1000.0) < 1e-12
    assert R.money(1.00, 10, 1.5, 0.65)[1] == 500.0 - 2 * 0.65 * 10


def test_contract_count_and_no_premium_floor():
    assert R.contracts_for(1.00) == 10 and R.contracts_for(0.05) == 200 and R.contracts_for(10.01) == 0


def test_two_sided_rule():
    assert R.two_sided(0.5, 0.6) and not R.two_sided(0.0, 0.6) and not R.two_sided(0.7, 0.6) and not R.two_sided(np.nan, 0.6)


def test_strike_is_strictly_otm_and_a_strike_on_the_money_moves_away():
    snap = pd.DataFrame([dict(type=t, strike=k) for t in "CP" for k in (775, 776, 777, 778)])
    assert R.pick_strike(snap, "C", 776.37) == 777 and R.pick_strike(snap, "P", 776.37) == 776
    assert R.pick_strike(snap, "C", 777.0) == 778 and R.pick_strike(snap, "P", 777.0) == 776
    assert R.pick_strike(snap, "C", 778.5) is None


def chain(day="2026-10-12"):
    """A synthetic session book: snapshots every 5 minutes 09:40..15:45, ask 1.00 rising slowly, same bid 0.98."""
    rows, books = [], []
    ts = pd.Timestamp(f"{day} 09:40:00", tz=ET)
    while ts <= pd.Timestamp(f"{day} 15:45:00", tz=ET):
        for typ in "CP":
            for k in (775.0, 776.0, 777.0, 778.0):
                rows.append(dict(quote_ts=ts, type=typ, strike=k, bid=0.98, ask=1.00, bid_size=5, ask_size=50, spot=776.40, expiry=day))
        books.append(dict(quote_ts=ts, first_fetch=ts + pd.Timedelta(minutes=15), lag_min=15.0, valid=True))
        ts += pd.Timedelta(minutes=5)
    return pd.DataFrame(rows), pd.DataFrame(books)


def sig(day, hhmm, side=1, grade="A"):
    return dict(ts=pd.Timestamp(f"{day} {hhmm}:00", tz=ET), sig=side, grade=grade, E=776.4, SL=775.9, TP1=777.0, TP2=777.5)


def test_ordered_skips_and_position_open_is_strict():
    day = "2026-10-12"
    rows, books = chain(day)
    # trade 1 at the first snapshot after 10:00 decision (10:05); flat bid 0.98 -> CLOCK at 11:05. A signal deciding at 11:05 is NOT blocked.
    s = pd.DataFrame([sig(day, "10:00"), sig(day, "10:30"), sig(day, "11:00")])
    tr, sk = R.process_session(day, s, rows, books, "T", redact=False)
    assert [t["fill_quote_ts"][11:16] for t in tr] == ["10:05", "11:05"]          # 10:30 skipped; 11:05 decision == exit ts: free
    assert [(k["reason"], k["decision_et"][11:16]) for k in sk] == [("POSITION_OPEN", "10:35")]
    assert tr[0]["exit_reason"] == "CLOCK" and tr[0]["twin_status"] == "OK" and tr[0]["type"] == "C" and tr[0]["strike"] == 777.0


def test_session_cap_and_no_book_window_and_too_late():
    day = "2026-10-12"
    rows, books = chain(day)
    s = pd.DataFrame([sig(day, h) for h in ("09:35", "10:50", "12:05", "13:20", "14:35", "15:15")])
    tr, sk = R.process_session(day, s, rows, books, "T", redact=False)
    assert len(tr) == 5 and sk[0]["reason"] == "SESSION_CAP"
    s2 = pd.DataFrame([sig(day, "15:45")])                                          # decision 15:50: after close - 5 min (15:55)? no, before;
    tr2, sk2 = R.process_session(day, s2, rows, books, "T", redact=False)           # but no snapshot at/after 15:50 within 10 min
    assert not tr2 and sk2[0]["reason"] == "NO_BOOK_WINDOW"


def test_shakedown_redacts_every_outcome_but_keeps_the_entry():
    day = "2026-10-12"
    rows, books = chain(day)
    tr, _ = R.process_session(day, pd.DataFrame([sig(day, "10:00")]), rows, books, "SHAKEDOWN - NOT COUNTED", redact=True)
    t = tr[0]
    assert t["ask_entry"] == 1.0 and t["contracts"] == 10 and t["invariants_ok"] is True
    assert all(t[k] == "" for k in ("exit_reason", "exit_price", "gross", "net", "net_pct", "twin_net", "twin_exit_reason"))


def test_invalid_books_never_fill():
    day = "2026-10-12"
    rows, books = chain(day)
    books.loc[:, "valid"] = False
    tr, sk = R.process_session(day, pd.DataFrame([sig(day, "10:00")]), rows, books, "T", redact=False)
    assert not tr and sk[0]["reason"] == "NO_BOOK_WINDOW"


def test_pending_days_catch_up_in_order_and_never_precede_the_stamp():
    ap = {"approved_at_et": "2026-10-09T18:30:00-04:00"}
    assert R.pending_days("2026-10-09", set(), ap) == []                         # 10-09 opened before the stamp
    assert R.pending_days("2026-10-14", set(), ap) == ["2026-10-12", "2026-10-13", "2026-10-14"]   # weekend skipped, in order
    assert R.pending_days("2026-10-14", {"2026-10-12"}, ap) == ["2026-10-13", "2026-10-14"]
    assert R.pending_days("2026-10-14", {"2026-10-12", "2026-10-13", "2026-10-14"}, ap) == []
    assert R.pending_days("2026-10-09", set(), None) == ["2026-10-09"]            # no stamp: one heartbeat for the settled day

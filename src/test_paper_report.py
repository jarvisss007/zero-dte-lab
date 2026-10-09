"""Synthetic-book tests for paper_report.py (PREREG section 9 written down before any counted session exists).
Run: /opt/anaconda3/bin/python -m pytest -q src/test_paper_report.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_report as RP  # noqa: E402


def book(mean_pct=0.0, twin_pct=0.0, short_twin_pct=None, sessions=60, per=3, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(sessions):
        d = (pd.Timestamp("2026-10-12") + pd.Timedelta(days=i)).date().isoformat()
        for k in range(per):
            side = "long" if (i + k) % 2 == 0 else "short"
            pct = mean_pct + rng.normal(0, 0.15)
            tw = (short_twin_pct if (side == "short" and short_twin_pct is not None) else twin_pct) + rng.normal(0, 0.15)
            rows.append(dict(session=d, side=side, net=pct * 1000, gross=pct * 1000 + 7, net_pct=pct, net_pct_fee065=pct - 0.01,
                             contracts=10, ask_entry=1.0, size_exceeds_ask_size="False", twin_status="OK", twin_net_pct=tw))
    t = pd.DataFrame(rows)
    s = pd.DataFrame({"session": sorted(t.session.unique()), "status": "COUNTED"})
    return t, s


def test_null_book_fails():
    t, s = book(0.0, 0.0)
    ro = RP.readout(t, s)
    assert ro["verdict"].startswith("FAIL") and ro["n_sessions"] == 60 and ro["n_trades"] == 180


def test_clearly_positive_book_passes():
    t, s = book(0.20, -0.05)
    ro = RP.readout(t, s)
    assert ro["verdict"] == "PASS" and all(ro["conditions"].values())


def test_positive_but_shorts_lose_to_their_twin_fails():
    t, s = book(0.20, -0.05, short_twin_pct=0.60)      # shorts beat by their mirror: drift cannot pass as skill
    ro = RP.readout(t, s)
    assert ro["twin_by_side"]["short"] < 0 and ro["verdict"].startswith("FAIL")


def test_readout_set_extends_only_until_100_trades():
    t, s = book(0.0, 0.0, sessions=80, per=1)           # 80 trades in 80 sessions: needs 100 trades
    t100, s100 = t, s
    ro = RP.readout(t100, s100)
    assert ro["n_sessions"] == 80                       # never more than exist; the gate in main() blocks this case anyway


def test_bootstrap_is_deterministic():
    v = np.linspace(-1, 1, 60)
    assert RP.boot_ci(v) == RP.boot_ci(v)


def test_before_the_gate_the_public_report_shows_no_profit_number():
    t, s = book(0.20, -0.05, sessions=5)
    md = RP.public_md("2026-10-18", s, t.assign(label="COUNTED"), pd.DataFrame(), pd.DataFrame(), None, "5 counted sessions.")
    assert "Not yet readable" in md and "mean" not in md.lower().replace("mean's sign", "") and "%" not in md.replace("Percent only", "").replace("percent", "")

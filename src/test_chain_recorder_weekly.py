"""Weekly leg of chain_recorder.py: expiry choice, closing window, isolation from data/chains.
Run: /opt/anaconda3/bin/python -m pytest -q src/test_chain_recorder_weekly.py"""
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_recorder as cr  # noqa: E402

ET = ZoneInfo("America/New_York")
D = dt.date.fromisoformat


def test_weekly_expiry_midweek_is_this_friday():
    assert cr.weekly_expiry(D("2026-10-19")) == "2026-10-23"   # Mon -> Fri
    assert cr.weekly_expiry(D("2026-10-22")) == "2026-10-23"   # Thu -> Fri


def test_weekly_expiry_on_friday_is_next_friday():
    assert cr.weekly_expiry(D("2026-10-16")) == "2026-10-23"
    assert cr.weekly_expiry(D("2026-10-17")) == "2026-10-23"   # weekend


def test_weekly_expiry_holiday_friday_moves_to_thursday():
    assert cr.weekly_expiry(D("2027-03-22")) == "2027-03-25"   # Good Friday 2027-03-26
    assert cr.weekly_expiry(D("2027-03-19")) == "2027-03-25"


def test_weekly_expiry_thanksgiving_week_keeps_the_early_close_friday():
    assert cr.weekly_expiry(D("2026-11-23")) == "2026-11-27"


def test_closing_window_normal_and_early_close():
    at = lambda s: dt.datetime.fromisoformat(s).replace(tzinfo=ET)
    assert not cr.in_weekly_window(at("2026-10-19 15:39"))
    assert cr.in_weekly_window(at("2026-10-19 15:40"))
    assert cr.in_weekly_window(at("2026-10-19 16:06"))
    assert not cr.in_weekly_window(at("2026-10-19 16:07"))
    assert cr.in_weekly_window(at("2026-11-27 12:45"))       # 13:00 early close
    assert not cr.in_weekly_window(at("2026-11-27 15:45"))


def _payload(spot, expiries):
    opts = []
    for e in expiries:
        y = e[2:4] + e[5:7] + e[8:10]
        for k in (int(spot * 0.85), int(spot * 0.95), int(spot), int(spot * 1.05), int(spot * 1.15)):
            for cp in "CP":
                opts.append({"option": f"SPY{y}{cp}{k * 1000:08d}", "bid": 1.0, "ask": 1.1})
    return {"current_price": spot, "options": opts}


def test_weekly_rows_go_to_the_sibling_folder_only(tmp_path, monkeypatch):
    out = tmp_path / "chains"
    monkeypatch.setattr(cr, "OUT_DIR", out)
    now = dt.datetime(2026, 10, 19, 15, 50, tzinfo=ET)
    cr.record_weekly(_payload(700.0, ["2026-10-19", "2026-10-23"]), now, "2026-10-19 15:50:00",
                     "2026-10-19T15:35:00", dry_run=False, force=False)
    f = tmp_path / "chains_weekly" / "SPY_2026-10-23.csv"
    assert f.exists()
    assert not (out / "SPY_2026-10-23.csv").exists()
    rows = f.read_text().strip().splitlines()[1:]
    assert len(rows) == 6                      # +/-10% band keeps 0.95/1.00/1.05 strikes, C and P
    assert all(",2026-10-23," in r for r in rows)


def test_weekly_outside_window_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "OUT_DIR", tmp_path / "chains")
    now = dt.datetime(2026, 10, 19, 11, 0, tzinfo=ET)
    cr.record_weekly(_payload(700.0, ["2026-10-23"]), now, "x", "y", dry_run=False, force=False)
    assert not (tmp_path / "chains_weekly").exists()


def test_weekly_error_is_swallowed(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "OUT_DIR", tmp_path / "chains")
    now = dt.datetime(2026, 10, 19, 15, 50, tzinfo=ET)
    cr.record_weekly({"options": []}, now, "x", "y", dry_run=False, force=False)   # no current_price -> KeyError

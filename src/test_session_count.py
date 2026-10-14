"""ZDTE-013 audit 2026-10-14: a .yfinance.csv sidecar must not overwrite its session's row count."""
import importlib.util, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("session_count", os.path.join(HERE, "..", "session_count.py"))


def test_sidecar_does_not_turn_a_full_session_into_a_stub(tmp_path, monkeypatch):
    sc = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(sc)
    ch = tmp_path / "data" / "chains"; ch.mkdir(parents=True)
    for d in ("2026-10-12", "2026-10-13", "2026-10-14"):
        (ch / f"SPY_{d}.csv").write_text("h\n" + "r\n" * 1000)
    (ch / "SPY_2026-10-13.yfinance.csv").write_text("h\n" + "r\n" * 10)
    monkeypatch.setattr(sc, "CH", str(ch)); monkeypatch.setattr(sc, "BASE", str(tmp_path))
    monkeypatch.setattr(sc, "first_snapshot_fits", lambda path: True)
    sc.main()
    out = json.load(open(tmp_path / "data" / "session_count.json"))
    assert out["files"] == 3 and out["usable"] == 3 and out["stubs"] == 0
    assert "2026-10-13" in out["usable_sessions"]

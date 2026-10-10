"""SWEEP-003 / BOOK-001 (2026-10-09, second wave): session_count.py and src/merge_chains.py no longer truncate their output in place.

session_count.py wrote data/session_count.json (the count the card and README quote, read by command-center's sync_lab_counts) with json.dump(.., open(.., "w"));
merge_chains.py wrote each data/chains_merged/SPY_<date>.csv with open(.., "w") + DictWriter. Both are now write-beside-and-replace through src/atomicio.py (the mirror of stock-radar's).
Pinned: an AST guard; old == new byte for byte (json indent=1; a DictWriter session file with commas, quotes and unicode in the cells).
Run: /opt/anaconda3/bin/python -m pytest -q src/test_book001_sweep003.py"""
import ast
import csv
import json
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import atomicio  # noqa: E402

FILES = [ROOT / "session_count.py", SRC / "merge_chains.py"]


def truncating_opens(src):
    out = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open":
            mode = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == "mode"), None)
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and mode.value.startswith("w") and "tmp" not in ast.unparse(n.args[0]):
                out.append(n.lineno)
    return out


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_converted_file_truncates_in_place(path):
    assert truncating_opens(path.read_text()) == []


def test_session_count_json_is_identical(tmp_path):
    obj = {"as_of": "2026-10-09", "files": 59, "usable": 43, "stub_sessions": ["2026-10-08"], "definition": "rows >= 50% of full-session median (100 rows -> need 50)"}
    with open(tmp_path / "old", "w") as f:
        json.dump(obj, f, indent=1)
    atomicio.atomic_json(str(tmp_path / "new"), obj, indent=1)
    assert (tmp_path / "old").read_bytes() == (tmp_path / "new").read_bytes()
    assert sorted(os.listdir(tmp_path)) == ["new", "old"]


def test_merged_session_csv_is_identical(tmp_path):
    header = ["quote_ts", "type", "strike", "bid", "ask", "note"]
    merged = [{"quote_ts": "2026-10-09T13:30:00Z", "type": "C", "strike": "600", "bid": "1.1", "ask": "1.2", "note": "a,b"},
              {"quote_ts": "2026-10-09T13:30:00Z", "type": "P", "strike": "600", "bid": "0.9", "ask": "1.0", "note": 'q"q é'}]
    with open(tmp_path / "old", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(merged)
    atomicio.atomic_csv(str(tmp_path / "new"), header, merged)
    assert (tmp_path / "old").read_bytes() == (tmp_path / "new").read_bytes()

ROOT_DIR = ROOT
LOADABLE = ["session_count.py", "src/merge_chains.py"]


def test_each_converted_module_loads_by_path_from_any_cwd(tmp_path):
    """a resolver check, a bin script or another repo may load these with spec_from_file_location and no sys.path help: the atomicio import must not depend on the
    caller's path (found by loading every converted module from cwd=/ on 2026-10-09; a bare `from atomicio import` failed for most of them)."""
    import subprocess
    code = "import importlib.util as u,sys; s=u.spec_from_file_location('probe', sys.argv[1]); m=u.module_from_spec(s); s.loader.exec_module(m)"
    for name in LOADABLE:
        r = subprocess.run([sys.executable, "-c", code, str(ROOT_DIR / name)], cwd=tmp_path, capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, (name, r.stderr[-300:])

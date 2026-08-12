"""SPY 0DTE option-chain recorder (roadmap phase 2).

Snapshots the free CBOE delayed-quotes chain (no API key, ~15-min delay) and
appends today's 0DTE contracts near the money to a daily CSV. Free intraday
chain history is unobtainable retroactively — recording starts the clock.

Source: https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json
Output: data/chains/SPY_YYYY-MM-DD.csv   (one row per contract per snapshot)
Log:    data/chains/recorder.log
State:  data/chains/.recorder_state.json (per-session fetch counters; survives
        the 5-min launchd relaunches, which each run a fresh process)

Guards (all bypassable with --force, for testing):
  - Mon-Fri, 09:29-16:06 ET only (RTH plus a buffer at the close).
  - Quote staleness: skip if CBOE's book timestamp is >30 min old (holiday /
    half-day close), so dead snapshots don't pollute the file.
  - Strike window: spot +/- 5% (plenty for a same-day expiry smile).

Resilience (added 2026-08-04 after the 2026-08-03 lost session — 80 straight
DNS failures, gaierror 8, machine-side):
  - Each invocation retries the fetch 3x with backoff (5s, 20s), explicitly
    re-resolving DNS and using a fresh opener (fresh TCP/TLS handshake) per
    attempt.
  - Consecutive failed snapshots are counted across invocations. At
    FAIL_THRESHOLD (6 = 30 min dark) a dated FAILURE_YYYY-MM-DD.txt marker is
    written into data/chains so a lost session is visibly lost, and one full
    client re-init + extra fetch attempt is made.
  - One summary line per session is logged after the close:
    "SESSION SUMMARY date: N fetches ok, M failed".

Scheduling: launched every 5 min by launchd
(~/Library/LaunchAgents/com.anupam.zerodte-recorder.plist); outside the RTH
window the script exits immediately (after flushing a pending session
summary). HONESTY NOTE: launchd does not wake a sleeping Mac — snapshots only
accumulate while the lid is open. Gap-tolerant by design: every snapshot is
independent.

Second leg (2026-08-11): this same script also runs every 10 min on a GitHub
runner (.github/workflows/chain-recorder.yml) with
`--out-dir data/chains_ci`, which is awake when the laptop is not. The two
legs never write the same file; src/merge_chains.py unions them and dedupes on
the CBOE book timestamp. Note that on an ephemeral runner the state file
starts empty every run, so the consecutive-failure counter and the
FAILURE_*.txt marker are effectively laptop-only — a dark stretch in the cloud
leg shows up as absent rows in the merge report, not as a marker.

Run once by hand:  /opt/anaconda3/bin/python src/chain_recorder.py [--force]
                   [--expiry YYYY-MM-DD] (test on a non-0DTE expiry)
                   [--dry-run] (fetch + parse, write nothing, touch no state)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import socket
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HOST = "cdn.cboe.com"
URL = f"https://{HOST}/api/global/delayed_quotes/options/SPY.json"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "chains"
STRIKE_BAND = 0.05  # keep strikes within +/-5% of spot
STALE_MIN = 30

FAIL_THRESHOLD = 6      # consecutive failed snapshots (30 min) -> marker + re-init
BACKOFF_S = (5, 20)     # sleeps between the in-invocation retry attempts
FETCH_TIMEOUT = 30

FIELDS = [
    "fetched_at_et", "quote_ts", "spot", "expiry", "type", "strike",
    "bid", "ask", "bid_size", "ask_size", "last_trade_price", "iv",
    "delta", "gamma", "theta", "vega", "rho", "volume", "open_interest",
]
OCC_RE = re.compile(r"^SPY(\d{6})([CP])(\d{8})$")


def log(msg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET")
    with open(OUT_DIR / "recorder.log", "a") as f:
        f.write(f"{stamp}  {msg}\n")
    print(msg)


def in_rth_window(now_et: datetime) -> bool:
    if now_et.weekday() >= 5:
        return False
    t = now_et.hour * 60 + now_et.minute
    return (9 * 60 + 29) <= t <= (16 * 60 + 6)


# ---------------------------------------------------------------- state

def state_path() -> Path:
    return OUT_DIR / ".recorder_state.json"


def load_state() -> dict:
    try:
        with open(state_path()) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = state_path().with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f)
    tmp.replace(state_path())


def fresh_state(date: str) -> dict:
    return {"date": date, "ok": 0, "failed": 0, "consecutive_failures": 0,
            "marker_written": False, "summary_written": False}


def flush_summary_if_due(state: dict, now_et: datetime) -> None:
    """Log the one-line session summary once the session is over."""
    if not state.get("date") or state.get("summary_written"):
        return
    today = now_et.strftime("%Y-%m-%d")
    session_over = state["date"] < today or (
        state["date"] == today
        and now_et.hour * 60 + now_et.minute > 16 * 60 + 6)
    if not session_over:
        return
    if state.get("ok", 0) == 0 and state.get("failed", 0) == 0:
        state["summary_written"] = True
        save_state(state)
        return
    log(f"SESSION SUMMARY {state['date']}: {state['ok']} fetches ok, "
        f"{state['failed']} failed")
    state["summary_written"] = True
    save_state(state)


# ---------------------------------------------------------------- fetch

def _one_fetch() -> dict:
    # Explicit re-resolve first: fails fast on dead DNS (the 2026-08-03 mode)
    # and guarantees each attempt is a fresh lookup, not a cached failure.
    socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "https://www.cboe.com/",
    })
    # Fresh opener per attempt -> fresh TCP + TLS handshake, no reused client.
    opener = urllib.request.build_opener()
    with opener.open(req, timeout=FETCH_TIMEOUT) as resp:
        return json.loads(resp.read())["data"]


def fetch_chain() -> dict:
    """Fetch with in-invocation retries + exponential backoff.

    Raises the last exception if every attempt fails.
    """
    last_err: Exception | None = None
    for i in range(len(BACKOFF_S) + 1):
        try:
            data = _one_fetch()
            if i > 0:
                log(f"fetch recovered on retry {i} (prior: {last_err!r})")
            return data
        except Exception as e:
            last_err = e
            if i < len(BACKOFF_S):
                time.sleep(BACKOFF_S[i])
    raise last_err  # type: ignore[misc]


def full_reinit_fetch() -> dict:
    """One last-ditch attempt with the client rebuilt from scratch."""
    urllib.request.install_opener(urllib.request.build_opener())
    return _one_fetch()


def write_failure_marker(state: dict, now_et: datetime, err: Exception) -> None:
    marker = OUT_DIR / f"FAILURE_{state['date']}.txt"
    stamp = now_et.strftime("%Y-%m-%d %H:%M:%S ET")
    with open(marker, "a") as f:
        f.write(
            f"LOST/DEGRADED SESSION {state['date']}\n"
            f"{state['consecutive_failures']} consecutive fetch failures "
            f"as of {stamp}.\n"
            f"Last error: {err!r}\n"
            f"Do not count this session toward the 60-session gate unless the "
            f"CSV is verified complete.\n")
    log(f"FAILURE MARKER written: {marker.name} "
        f"({state['consecutive_failures']} consecutive failures)")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="bypass RTH + staleness guards (testing)")
    ap.add_argument("--expiry", default=None,
                    help="YYYY-MM-DD expiry override (default: today = 0DTE)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + parse only; write no CSV, touch no state")
    ap.add_argument("--out-dir", default=None,
                    help="write CSV/log/state here instead of data/chains "
                         "(the CI recorder uses data/chains_ci so the two "
                         "recorders never write the same file)")
    args = ap.parse_args()

    if args.out_dir:
        global OUT_DIR
        OUT_DIR = Path(args.out_dir).expanduser().resolve()

    now_et = datetime.now(ET)
    today = now_et.strftime("%Y-%m-%d")
    state = load_state()

    if not args.force and not in_rth_window(now_et):
        # launchd fires 24/7; the first out-of-window run flushes the summary.
        if not args.dry_run:
            flush_summary_if_due(state, now_et)
        return 0

    if not args.dry_run:
        if state.get("date") != today:
            flush_summary_if_due(state, now_et)  # summarize a stranded session
            state = fresh_state(today)
            save_state(state)

    try:
        data = fetch_chain()
    except Exception as e:  # every retry failed
        if args.dry_run:
            log(f"DRY-RUN FETCH ERROR: {e!r}")
            return 1
        state["failed"] += 1
        state["consecutive_failures"] += 1
        log(f"FETCH ERROR (attempt incl. {len(BACKOFF_S)} retries): {e!r} "
            f"[consecutive: {state['consecutive_failures']}]")
        if (state["consecutive_failures"] >= FAIL_THRESHOLD
                and not state["marker_written"]):
            write_failure_marker(state, now_et, e)
            state["marker_written"] = True
            try:
                data = full_reinit_fetch()
                log("full client re-init succeeded")
                state["failed"] -= 1  # this snapshot recovered after all
            except Exception as e2:
                log(f"full client re-init failed: {e2!r}")
                save_state(state)
                return 1
        else:
            save_state(state)
            return 1
    # fetch (or re-init) succeeded
    if not args.dry_run:
        state["ok"] += 1
        state["consecutive_failures"] = 0
        save_state(state)

    spot = data["current_price"]
    quote_ts = data.get("last_trade_time") or ""
    if not args.force and quote_ts:
        try:
            age = now_et.replace(tzinfo=None) - datetime.fromisoformat(quote_ts)
            if age > timedelta(minutes=STALE_MIN):
                log(f"skip: stale quotes ({quote_ts} ET, spot {spot})")
                return 0
        except ValueError:
            pass  # unparseable timestamp: record anyway

    expiry = args.expiry or now_et.strftime("%Y-%m-%d")
    want = expiry[2:4] + expiry[5:7] + expiry[8:10]  # YYMMDD in OCC symbol
    lo, hi = spot * (1 - STRIKE_BAND), spot * (1 + STRIKE_BAND)

    rows = []
    fetched = now_et.strftime("%Y-%m-%d %H:%M:%S")
    for o in data["options"]:
        m = OCC_RE.match(o["option"])
        if not m or m.group(1) != want:
            continue
        strike = int(m.group(3)) / 1000.0
        if not lo <= strike <= hi:
            continue
        rows.append({
            "fetched_at_et": fetched, "quote_ts": quote_ts, "spot": spot,
            "expiry": expiry, "type": m.group(2), "strike": strike,
            "bid": o.get("bid"), "ask": o.get("ask"),
            "bid_size": o.get("bid_size"), "ask_size": o.get("ask_size"),
            "last_trade_price": o.get("last_trade_price"), "iv": o.get("iv"),
            "delta": o.get("delta"), "gamma": o.get("gamma"),
            "theta": o.get("theta"), "vega": o.get("vega"), "rho": o.get("rho"),
            "volume": o.get("volume"), "open_interest": o.get("open_interest"),
        })

    if not rows:
        log(f"skip: no contracts for expiry {expiry} (holiday?)")
        return 0

    if args.dry_run:
        log(f"DRY-RUN fetch ok: {len(rows)} contracts parsed for {expiry} "
            f"(spot {spot}, quotes {quote_ts}) — nothing written")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"SPY_{expiry}.csv"
    new_file = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    log(f"wrote {len(rows)} rows -> {out.name} (spot {spot}, quotes {quote_ts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

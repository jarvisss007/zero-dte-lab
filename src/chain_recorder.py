"""SPY 0DTE option-chain recorder (roadmap phase 2).

Snapshots the free CBOE delayed-quotes chain (no API key, ~15-min delay) and
appends today's 0DTE contracts near the money to a daily CSV. Free intraday
chain history is unobtainable retroactively — recording starts the clock.

Source: https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json
Output: data/chains/SPY_YYYY-MM-DD.csv   (one row per contract per snapshot)
Log:    data/chains/recorder.log

Guards (all bypassable with --force, for testing):
  - Mon-Fri, 09:29-16:06 ET only (RTH plus a buffer at the close).
  - Quote staleness: skip if CBOE's book timestamp is >30 min old (holiday /
    half-day close), so dead snapshots don't pollute the file.
  - Strike window: spot +/- 5% (plenty for a same-day expiry smile).

Scheduling: launched every 5 min by launchd
(~/Library/LaunchAgents/com.anupam.zerodte-recorder.plist); outside the RTH
window the script exits immediately. HONESTY NOTE: launchd does not wake a
sleeping Mac — snapshots only accumulate while the lid is open. Gap-tolerant
by design: every snapshot is independent.

Run once by hand:  /opt/anaconda3/bin/python src/chain_recorder.py [--force]
                   [--expiry YYYY-MM-DD] (test on a non-0DTE expiry)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "chains"
STRIKE_BAND = 0.05  # keep strikes within +/-5% of spot
STALE_MIN = 30

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


def fetch_chain() -> dict:
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "https://www.cboe.com/",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["data"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="bypass RTH + staleness guards (testing)")
    ap.add_argument("--expiry", default=None,
                    help="YYYY-MM-DD expiry override (default: today = 0DTE)")
    args = ap.parse_args()

    now_et = datetime.now(ET)
    if not args.force and not in_rth_window(now_et):
        return 0  # silent outside market hours; launchd fires 24/7

    try:
        data = fetch_chain()
    except Exception as e:  # network blips are expected; log and move on
        log(f"FETCH ERROR: {e!r}")
        return 1

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

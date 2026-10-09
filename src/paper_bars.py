"""Bars for the simulated paper trader (PREREG_IE_PRO_PAPER.md section 2). Paper only; no keys; reads public Yahoo chart data.

fetch_yahoo_5m()  SPY 5-minute bars with pre/post market, timestamps in ET.
clean()           the two frozen drops: (1) every bar stamped at or after its session's close (16:00 ET, or the early-close
                  time in src/sessions.py), because Yahoo's post-close bars carry bad prints; (2) flat carry-forward bars
                  (O=H=L=C equal to the previous kept close, volume 0 - Firm Brain 18). Bars on non-sessions are dropped.
close_et()        the session close as an ET clock time (early closes from src/sessions.EARLY_CLOSES).
tradable_bar()    a signal bar may be traded only if it opened at or after 09:30 ET and its decision time (open + 5 min)
                  is at least 5 minutes before the close.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request
from pathlib import Path

import pandas as pd

import sessions

UA = "Anupam Patil research apati077@ucr.edu"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=5m&range={rng}&includePrePost=true"
ET = "America/New_York"


def fetch_yahoo_5m(rng: str = "60d") -> pd.DataFrame:
    req = urllib.request.Request(URL.format(rng=rng), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({"ts": pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(ET),
                       "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"]})
    return df.dropna(subset=["close"]).reset_index(drop=True)


def close_et(d) -> dt.time:
    """Session close as an ET clock time: 16:00, or the EARLY_CLOSES entry ('13:00 ET')."""
    s = sessions.EARLY_CLOSES.get(pd.Timestamp(d).date().isoformat())
    if s:
        h, m = s.split(" ")[0].split(":")
        return dt.time(int(h), int(m))
    return dt.time(16, 0)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts").reset_index(drop=True)
    day = df["ts"].dt.date
    keep = []
    for d, g in df.groupby(day, sort=True):
        if not sessions.is_session(d):
            continue
        cl = close_et(d)
        keep.append(g[g["ts"].dt.time < cl])
    out = pd.concat(keep).reset_index(drop=True) if keep else df.iloc[0:0]
    prev = out["close"].shift(1)
    flat = ((out.open == out.high) & (out.high == out.low) & (out.low == out.close)
            & (out.close == prev) & (out.volume == 0))
    return out[~flat].reset_index(drop=True)


def tradable_bar(ts: pd.Timestamp) -> bool:
    """ts = the bar's open (ET). Opened at/after 09:30 and decision time (open + 5 min) at least 5 minutes before the close."""
    cl = pd.Timestamp.combine(ts.date(), close_et(ts)).tz_localize(ET)
    return ts.time() >= dt.time(9, 30) and ts + pd.Timedelta(minutes=5) <= cl - pd.Timedelta(minutes=5)


def load(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(ET)
    return df

"""Shared loaders for zero-dte-lab.

All data comes from ~/spy-trading/data (not copied). Everything is converted
to America/New_York and filtered to regular trading hours (09:30-16:00).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path.home() / "spy-trading" / "data"
ET = "America/New_York"


def load_minute_closes() -> pd.DataFrame:
    """1-min close-only bars, Aug 2024 -> Nov 2025. Columns: ts (ET), close."""
    df = pd.read_csv(DATA_DIR / "spy_minute_bars.csv")
    df["ts"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(ET)
    df = df.rename(columns={"c": "close"})[["ts", "close"]]
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return _rth(df)


def load_bats(name: str) -> pd.DataFrame:
    """TradingView BATS export (true OHLCV). name: '5' or '15'."""
    fname = {"5": "BATS_SPY, 5_7c70e.csv", "15": "BATS_SPY, 15_4c750.csv"}[name]
    df = pd.read_csv(DATA_DIR / fname)
    df["ts"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(ET)
    df = df.rename(columns={"Volume": "volume"})
    df = df[["ts", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return _rth(df)


def minute_to_pseudo_ohlc(minutes: pd.DataFrame, freq: str = "5min") -> pd.DataFrame:
    """Resample close-only 1-min bars to pseudo-OHLC.

    HONESTY NOTE: highs/lows are built from minute CLOSES, so true intrabar
    wicks are understated. Sweep detections on this data are a lower bound;
    results are cross-checked against the true-OHLC BATS files.
    """
    m = minutes.set_index("ts")["close"]
    o = m.resample(freq, label="left", closed="left").agg(
        ["first", "max", "min", "last", "count"])
    o.columns = ["open", "high", "low", "close", "n"]
    o = o[o["n"] >= 3].drop(columns="n").reset_index()
    return _rth(o)


def _rth(df: pd.DataFrame) -> pd.DataFrame:
    t = df["ts"].dt
    keep = ((t.hour * 60 + t.minute) >= 9 * 60 + 30) & \
           ((t.hour * 60 + t.minute) < 16 * 60) & (t.dayofweek < 5)
    return df[keep].reset_index(drop=True)


def session_groups(df: pd.DataFrame):
    return df.groupby(df["ts"].dt.date, sort=True)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()

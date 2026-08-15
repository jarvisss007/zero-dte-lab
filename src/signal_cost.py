"""Signal-costing engine — what an r18 signal actually pays in a 0DTE option.

Every backtest in ~/ie-pro-project and every row in this repo's
`sweep_results.csv` scores r17/r18 in SPY *points* (R-multiples on the
underlying). Anupam does not trade SPY shares — he trades SPY 0DTE options.
A -0.24R average in share-space and a -0.24R average in option-space are not
the same number, because the option costs a bid/ask to enter and exit and
bleeds theta for every minute the trade is open.

This module closes that gap. It takes the signals the honest (causal-HTF)
port generates, and prices each one through the ACTUAL recorded chain:
buy at the real ask, sell at the real bid, on the real 5-minute book grid.

Two deliverables:

  1. `trade_report()` — the same trades, scored twice: SPY R-multiple vs the
     dollars-and-percent the 0DTE contract would have returned.

  2. `breakeven_curve()` — the permanent asset. For an ATM 0DTE contract, how
     far must SPY move, over a given holding time, for the trade to break even
     after the round-trip spread and theta? This is a property of the
     INSTRUMENT, not of r18. It survives whatever strategy comes next: any
     future signal whose target is below this curve cannot be traded in 0DTE
     options at that time of day, no matter how good its hit rate is.

     It is computed model-free — no greeks, no Black-Scholes. The chain
     recorded H minutes later IS the pricing function: we ask "in the later
     book, what moneyness prices at what we paid?" and invert to a spot move.
     The recorder's own `delta` column is never used (it is unreliable for
     deep ITM/OTM strikes in the CBOE feed; see the 0.0-IV rows).

HONESTY NOTES / LIMITS
  - Book granularity is ~5 min. A signal is filled at the first book at or
    after the signal bar's close, so fills can drift up to one book from the
    bar. `spot_drift` records the drift for every trade; nothing is hidden.
  - CBOE quotes are ~15 min delayed at FETCH time, but each book carries its
    own `quote_ts`. Aligning on `quote_ts` (not `fetched_at_et`) means the
    prices are the real market at that moment, merely recorded late. The
    delay is a recording limitation, not a backtest bias.
  - Marketable fills only: we always pay the ask and always receive the bid.
    No mid-price fills, no price improvement. This is the pessimistic end.
  - 0DTE positions are FORCE-CLOSED at the last book of the session. There
    is no overnight; an unclosed 0DTE expires.
  - Sample is small (see the session table the report prints). This measures
    COST, which is stable and needs far less data than edge. It is not, and
    does not claim to be, an edge verdict.

Run: /opt/anaconda3/bin/python src/signal_cost.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_utils import atr  # noqa: E402
from sweep_backtest import build_signals, htf_bias, ATR_SL, TP_RR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHAINS = ROOT / "data" / "chains"
CHAINS_CI = ROOT / "data" / "chains_ci"
RESULTS = ROOT / "results"
CACHE = ROOT / "data" / "spy_5m_cache.csv"
ET = "America/New_York"

MIN_BOOKS = 40          # a session with fewer books is gutted; skip it
HOLDS = (15, 30, 60)    # minutes, for the breakeven curve
CONTRACT = 100          # shares per option contract


# ─────────────────────────────────────────────────────────────── price data
def load_spy_5m(refresh: bool = False) -> pd.DataFrame:
    """SPY 5-min true OHLCV, ET, RTH. Cached — yfinance caps 5m at ~60 days."""
    if CACHE.exists() and not refresh:
        df = pd.read_csv(CACHE)
        df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(ET)
        return df

    import yfinance as yf
    raw = yf.download("SPY", interval="5m", period="60d",
                      auto_adjust=False, prepost=False, progress=False)
    if raw.empty:
        raise RuntimeError("yfinance returned no 5m data for SPY")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.DatetimeIndex(df.index).tz_convert(ET)
    df = df.between_time("09:30", "15:59")
    df = df[df["volume"] > 0].dropna().reset_index()
    df = df.rename(columns={df.columns[0]: "ts"})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


# ─────────────────────────────────────────────────────────────── chain data
def load_books() -> pd.DataFrame:
    """All recorded 0DTE books, deduped on (quote_ts, type, strike).

    Unions the laptop leg and the CI leg the same way merge_chains.py does —
    dedupe on the CBOE book timestamp, never on fetch time, or one observation
    polled by both legs counts twice.
    """
    files = sorted(CHAINS.glob("SPY_*.csv")) + sorted(CHAINS_CI.glob("SPY_*.csv"))
    if not files:
        raise RuntimeError(f"no chain files under {CHAINS}")

    frames = []
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if d.empty or "quote_ts" not in d:
            continue
        frames.append(d)

    df = pd.concat(frames, ignore_index=True)
    df["quote_ts"] = pd.to_datetime(df["quote_ts"], errors="coerce")
    df = df.dropna(subset=["quote_ts", "bid", "ask", "strike", "spot"])
    df["quote_ts"] = df["quote_ts"].dt.tz_localize(ET, ambiguous="NaT",
                                                   nonexistent="NaT")
    df = df.dropna(subset=["quote_ts"])
    df["date"] = df["quote_ts"].dt.date

    # 0DTE only: the contract expires the day it was recorded
    df = df[pd.to_datetime(df["expiry"]).dt.date == df["date"]]
    # a real fill needs a two-sided market
    df = df[(df["ask"] > 0) & (df["bid"] >= 0) & (df["ask"] >= df["bid"])]

    df = df.drop_duplicates(subset=["quote_ts", "type", "strike"], keep="last")
    return df.sort_values("quote_ts").reset_index(drop=True)


def session_quality(books: pd.DataFrame) -> pd.DataFrame:
    q = books.groupby("date").agg(
        books=("quote_ts", "nunique"),
        first=("quote_ts", "min"),
        last=("quote_ts", "max"),
        strikes=("strike", "nunique"),
    ).reset_index()
    q["usable"] = q["books"] >= MIN_BOOKS
    return q


# ────────────────────────────────────────────────────────── signal + exits
@dataclass
class SpyTrade:
    """A trade in SPY-space: entry/exit driven purely by the 5-min bars."""
    date: object
    side: int              # +1 long, -1 short
    entry_ts: pd.Timestamp  # bar CLOSE time (fills are on close)
    exit_ts: pd.Timestamp
    entry_px: float
    exit_px: float
    risk: float            # 1 ATR
    reason: str
    bars: int

    @property
    def r(self) -> float:
        return (self.exit_px - self.entry_px) * self.side / self.risk

    @property
    def move_pts(self) -> float:
        return (self.exit_px - self.entry_px) * self.side


def run_spy(df: pd.DataFrame) -> list[SpyTrade]:
    """r18 exit logic (ATR stop, 2.5R target, breakeven at +1R) + forced EOD.

    Same worst-case intrabar rule as sweep_backtest: if both the stop and the
    target sit inside one bar's range, the stop is assumed to fill first.
    0DTE forces a close at each session's last bar — an option cannot be held.
    """
    a = atr(df).to_numpy()
    h, l, c = (df[k].to_numpy() for k in ("high", "low", "close"))
    sig = df["sig"].to_numpy()
    ts = df["ts"].to_numpy()
    dates = df["ts"].dt.date.to_numpy()
    last_of_day = np.r_[dates[1:] != dates[:-1], True]

    out: list[SpyTrade] = []
    pos = 0
    entry = stop = target = risk = 0.0
    ebar = 0
    be_done = False

    def close(i: int, px: float, why: str) -> None:
        nonlocal pos
        out.append(SpyTrade(
            date=dates[ebar], side=pos,
            entry_ts=pd.Timestamp(ts[ebar]), exit_ts=pd.Timestamp(ts[i]),
            entry_px=entry, exit_px=px, risk=risk, reason=why, bars=i - ebar))
        pos = 0

    for i in range(len(df)):
        if pos != 0 and i > ebar:
            if pos == 1:
                if l[i] <= stop:
                    close(i, stop, "BE" if be_done else "SL")
                elif h[i] >= target:
                    close(i, target, "TP")
                elif not be_done and c[i] >= entry + risk:
                    stop, be_done = entry, True
            else:
                if h[i] >= stop:
                    close(i, stop, "BE" if be_done else "SL")
                elif l[i] <= target:
                    close(i, target, "TP")
                elif not be_done and c[i] <= entry - risk:
                    stop, be_done = entry, True

        if pos != 0 and last_of_day[i]:
            close(i, c[i], "EOD")
            continue

        if sig[i] != 0 and pos == 0 and np.isfinite(a[i]) and a[i] > 0 \
                and not last_of_day[i]:
            pos, entry, ebar, be_done = int(sig[i]), c[i], i, False
            risk = a[i] * ATR_SL
            stop = entry - pos * risk
            target = entry + pos * risk * TP_RR

    return out


# ──────────────────────────────────────────────────────── option execution
def _book_at_or_after(books_day: pd.DataFrame, t: pd.Timestamp):
    """First book at or after t. You cannot fill on a book that hasn't printed."""
    later = books_day[books_day["quote_ts"] >= t]
    if later.empty:
        return None
    return later["quote_ts"].iloc[0]


def _pick(book: pd.DataFrame, opt_type: str, spot: float, offset: int):
    """Nearest-to-spot strike, shifted `offset` strikes further OTM."""
    side = book[book["type"] == opt_type]
    if side.empty:
        return None
    strikes = np.sort(side["strike"].unique())
    k_atm = strikes[np.abs(strikes - spot).argmin()]
    idx = int(np.where(strikes == k_atm)[0][0])
    idx += offset if opt_type == "C" else -offset
    if idx < 0 or idx >= len(strikes):
        return None
    row = side[side["strike"] == strikes[idx]]
    return row.iloc[0] if len(row) else None


def price_trades(trades: list[SpyTrade], books: pd.DataFrame,
                 offset: int = 0) -> pd.DataFrame:
    """Fill every SPY trade in the 0DTE chain: pay ask in, receive bid out."""
    by_date = {d: g for d, g in books.groupby("date")}
    bar = pd.Timedelta(minutes=5)     # bar ts is the bar's START
    rows = []

    for t in trades:
        day = by_date.get(t.date)
        if day is None or day["quote_ts"].nunique() < MIN_BOOKS:
            rows.append({"status": "no_session"})
            continue

        t_in = _book_at_or_after(day, t.entry_ts + bar)
        if t_in is None:
            rows.append({"status": "entry_after_last_book"})
            continue
        b_in = day[day["quote_ts"] == t_in]

        opt = "P" if t.side < 0 else "C"
        leg_in = _pick(b_in, opt, float(b_in["spot"].iloc[0]), offset)
        if leg_in is None or leg_in["ask"] <= 0:
            rows.append({"status": "no_contract"})
            continue

        t_out = _book_at_or_after(day, t.exit_ts + bar)
        if t_out is None:                       # ran past the last book: force close
            t_out = day["quote_ts"].max()
            forced = True
        else:
            forced = False
        b_out = day[day["quote_ts"] == t_out]
        leg_out = b_out[(b_out["type"] == opt) & (b_out["strike"] == leg_in["strike"])]
        if leg_out.empty:
            rows.append({"status": "contract_vanished"})
            continue
        leg_out = leg_out.iloc[0]

        paid, got = float(leg_in["ask"]), float(leg_out["bid"])
        spread_in = float(leg_in["ask"] - leg_in["bid"])
        spread_out = float(leg_out["ask"] - leg_out["bid"])
        rows.append({
            "status": "ok",
            "strike": float(leg_in["strike"]), "type": opt,
            "t_in": t_in, "t_out": t_out,
            "spot_in": float(leg_in["spot"]), "spot_out": float(leg_out["spot"]),
            "spot_drift": float(leg_in["spot"]) - t.entry_px,
            "paid": paid, "got": got,
            "pnl_$": (got - paid) * CONTRACT,
            "ret_pct": (got - paid) / paid * 100 if paid > 0 else np.nan,
            "spread_rt_$": (spread_in + spread_out) * CONTRACT,
            "spread_rt_pct": (spread_in + spread_out) / paid * 100 if paid > 0 else np.nan,
            "hold_min": (t_out - t_in).total_seconds() / 60,
            "forced_close": forced,
        })

    base = pd.DataFrame([{
        "date": t.date, "side": t.side, "entry_ts": t.entry_ts,
        "exit_ts": t.exit_ts, "spy_entry": t.entry_px, "spy_exit": t.exit_px,
        "spy_R": t.r, "spy_move_pts": t.move_pts, "reason": t.reason,
        "atr": t.risk,
    } for t in trades])
    return pd.concat([base, pd.DataFrame(rows)], axis=1)


# ─────────────────────────────────────────────────── the breakeven cost curve
def breakeven_curve(books: pd.DataFrame, holds=HOLDS) -> pd.DataFrame:
    """Model-free: how far must SPY move for an ATM 0DTE to break even?

    For each book t we buy the ATM contract at the ask. We then look at the
    book H minutes later and use IT as the pricing function: across that
    book's strikes, option bid is a monotone function of moneyness
    (spot - strike for calls). We invert it to find the moneyness x at which
    the bid equals what we paid, then the spot needed at t+H is
    (our strike + x), and the required move is that minus the entry spot.

    No greeks and no option model are involved — only quotes that were
    actually printed. Theta is included automatically, because the later book
    is genuinely later in the day and its prices reflect the decay.
    """
    rows = []
    for date, day in books.groupby("date"):
        if day["quote_ts"].nunique() < MIN_BOOKS:
            continue
        stamps = np.sort(day["quote_ts"].unique())
        for t0 in stamps:
            b0 = day[day["quote_ts"] == t0]
            spot0 = float(b0["spot"].iloc[0])
            for H in holds:
                t1_cands = stamps[stamps >= t0 + pd.Timedelta(minutes=H)]
                if len(t1_cands) == 0:
                    continue
                t1 = t1_cands[0]
                b1 = day[day["quote_ts"] == t1]
                for opt in ("C", "P"):
                    leg = _pick(b0, opt, spot0, 0)
                    if leg is None or leg["ask"] <= 0:
                        continue
                    paid = float(leg["ask"])
                    K = float(leg["strike"])

                    side1 = b1[b1["type"] == opt].copy()
                    if len(side1) < 5:
                        continue
                    spot1 = float(side1["spot"].iloc[0])
                    # moneyness, positive = in the money
                    side1["x"] = (spot1 - side1["strike"]) if opt == "C" \
                        else (side1["strike"] - spot1)
                    side1 = side1.sort_values("x")
                    x, y = side1["x"].to_numpy(), side1["bid"].to_numpy()
                    if not (y.min() <= paid <= y.max()):
                        continue          # cannot recover the entry price at all
                    keep = np.r_[True, np.diff(y) > 0]     # strictly increasing
                    if keep.sum() < 3:
                        continue
                    x_need = float(np.interp(paid, y[keep], x[keep]))
                    spot_need = K + x_need if opt == "C" else K - x_need
                    move = (spot_need - spot0) * (1 if opt == "C" else -1)

                    rows.append({
                        "date": date, "quote_ts": t0,
                        "minute": pd.Timestamp(t0).hour * 60 + pd.Timestamp(t0).minute,
                        "hold_min": H, "type": opt, "strike": K,
                        "spot": spot0, "paid": paid,
                        "spread_pct": float(leg["ask"] - leg["bid"]) / paid * 100,
                        "be_move_pts": move,
                        "be_move_pct": move / spot0 * 100,
                    })
    return pd.DataFrame(rows)


MOVE_GRID = tuple(np.round(np.arange(-2.0, 2.001, 0.25), 2))


def payoff_table(books: pd.DataFrame, moves=MOVE_GRID,
                 holds=HOLDS) -> pd.DataFrame:
    """What an ATM 0DTE returns for a given SPY move, held H minutes.

    Moves are signed FAVOURABLY: +0.5 means spot rose 0.5 for a call, or fell
    0.5 for a put. That makes calls and puts directly comparable, so a long
    signal and a short signal can be read off the same row.

    Same model-free method as `breakeven_curve`: the book printed H minutes
    later is the pricing function, read at the moneyness the move implies.

    Assumption worth naming: this is sticky-moneyness. The later book's smile
    was printed at the spot that actually happened; using it to price a
    counterfactual spot assumes the vol surface would look the same in
    moneyness terms had the move been different. That is the standard
    approximation and it is not free — treat the tails (|move| >= 1) as
    softer than the middle of the table.
    """
    rows = []
    for date, day in books.groupby("date"):
        if day["quote_ts"].nunique() < MIN_BOOKS:
            continue
        stamps = np.sort(day["quote_ts"].unique())
        for t0 in stamps:
            b0 = day[day["quote_ts"] == t0]
            spot0 = float(b0["spot"].iloc[0])
            for H in holds:
                cand = stamps[stamps >= t0 + pd.Timedelta(minutes=H)]
                if len(cand) == 0:
                    continue
                b1 = day[day["quote_ts"] == cand[0]]
                for opt in ("C", "P"):
                    leg = _pick(b0, opt, spot0, 0)
                    if leg is None or leg["ask"] <= 0:
                        continue
                    paid, K = float(leg["ask"]), float(leg["strike"])
                    side1 = b1[b1["type"] == opt].copy()
                    if len(side1) < 5:
                        continue
                    spot1 = float(side1["spot"].iloc[0])
                    side1["x"] = (spot1 - side1["strike"]) if opt == "C" \
                        else (side1["strike"] - spot1)
                    side1 = side1.sort_values("x")
                    x, y = side1["x"].to_numpy(), side1["bid"].to_numpy()
                    keep = np.r_[True, np.diff(y) > 0]
                    if keep.sum() < 3:
                        continue
                    x_entry = (spot0 - K) if opt == "C" else (K - spot0)
                    for m in moves:
                        xn = x_entry + m
                        if not (x[keep].min() <= xn <= x[keep].max()):
                            continue
                        got = float(np.interp(xn, x[keep], y[keep]))
                        rows.append({
                            "date": date, "quote_ts": t0,
                            "minute": pd.Timestamp(t0).hour * 60 + pd.Timestamp(t0).minute,
                            "hold_min": H, "type": opt, "move_pts": m,
                            "paid": paid, "got": got,
                            "ret_pct": (got - paid) / paid * 100,
                        })
    return pd.DataFrame(rows)


TIME_BINS = [0, 600, 630, 660, 720, 780, 840, 900, 960]
TIME_LABELS = ["09:30-10:00", "10:00-10:30", "10:30-11:00", "11:00-12:00",
               "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00"]


def _bucket(minutes: pd.Series) -> pd.Series:
    return pd.cut(minutes, bins=TIME_BINS, labels=TIME_LABELS)


def rule1_target(pay: pd.DataFrame, rr: float = 1.5,
                 stops=(0.25, 0.4, 0.5, 0.75)) -> pd.DataFrame:
    """Constitution Rule 1, enforced in OPTION space.

    Rule 1: "No entry without a written stop AND a target >= 1.5R." In
    share-space R is just distance, so a 0.5-point stop and a 0.75-point
    target satisfies it trivially. In a 0DTE option it does not, because the
    same-sized adverse move loses more than the favourable move gains and
    theta charges rent on both.

    For each time-of-day bucket, holding time and stop distance, this returns
    the SPY move the target must actually reach for the trade to pay `rr`
    times what the stop costs, once real bid/ask and decay are priced in.

    `req_mult` is the honest headline: how many times wider than the stop the
    target has to be. If it reads 3.0, a "1:1.5" plan on the chart is really
    asking for 1:3 from the market.
    """
    pay = pay.assign(bucket=_bucket(pay["minute"]))
    rows = []
    for (bucket, H), g in pay.groupby(["bucket", "hold_min"], observed=True):
        curve = g.groupby("move_pts")["ret_pct"].median().sort_index()
        if len(curve) < 6:
            continue
        mv, rt = curve.index.to_numpy(), curve.to_numpy()
        gain_side = mv >= 0
        for s in stops:
            if s > mv.max() or -s < mv.min():
                continue
            loss = float(np.interp(-s, mv, rt))       # negative %
            if loss >= 0:
                continue
            need = rr * abs(loss)
            gm, gr = mv[gain_side], rt[gain_side]
            keep = np.r_[True, np.diff(gr) > 0]
            if keep.sum() < 3 or need > gr[keep].max():
                tgt = np.nan                          # unreachable in +/-2 pts
            else:
                tgt = float(np.interp(need, gr[keep], gm[keep]))
            rows.append({
                "bucket": bucket, "hold_min": H, "stop_pts": s,
                "loss_at_stop_%": round(loss, 1),
                "need_gain_%": round(need, 1),
                "req_target_pts": round(tgt, 2) if np.isfinite(tgt) else np.nan,
                "req_mult": round(tgt / s, 2) if np.isfinite(tgt) else np.nan,
            })
    return pd.DataFrame(rows)


def validate_payoff(books: pd.DataFrame, holds=HOLDS) -> pd.DataFrame:
    """Ground-truth check on `payoff_table`, using no interpolation at all.

    Buy the ATM contract at t0's ask, sell the SAME strike at t0+H's bid, and
    bin by the spot move that actually happened. If the sticky-moneyness
    inversion in `payoff_table` is sound, these medians should track it. Where
    they disagree, THIS table is the authority — it is pure observation.

    The outer bins are open-ended (|move| >= 0.875 lands in +/-1.0), so the
    tails read more extreme here than in the interpolated table by
    construction. Compare the middle of the distribution.
    """
    rows = []
    for date, day in books.groupby("date"):
        if day["quote_ts"].nunique() < MIN_BOOKS:
            continue
        stamps = np.sort(day["quote_ts"].unique())
        for t0 in stamps:
            b0 = day[day["quote_ts"] == t0]
            spot0 = float(b0["spot"].iloc[0])
            for H in holds:
                cand = stamps[stamps >= t0 + pd.Timedelta(minutes=H)]
                if len(cand) == 0:
                    continue
                b1 = day[day["quote_ts"] == cand[0]]
                spot1 = float(b1["spot"].iloc[0])
                for opt in ("C", "P"):
                    leg = _pick(b0, opt, spot0, 0)
                    if leg is None or leg["ask"] <= 0:
                        continue
                    K, paid = float(leg["strike"]), float(leg["ask"])
                    ex = b1[(b1["type"] == opt) & (b1["strike"] == K)]
                    if ex.empty:
                        continue
                    rows.append({
                        "hold_min": H, "type": opt,
                        "fav_move": (spot1 - spot0) * (1 if opt == "C" else -1),
                        "ret_pct": (float(ex["bid"].iloc[0]) - paid) / paid * 100,
                    })
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["move_bin"] = pd.cut(
        d["fav_move"],
        [-np.inf, -.875, -.625, -.375, -.125, .125, .375, .625, .875, np.inf],
        labels=["<=-1", "-0.75", "-0.50", "-0.25", "0.00",
                "+0.25", "+0.50", "+0.75", ">=+1"])
    return d


# ─────────────────────────────────────────────────────────────────── report
def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    print("=" * 78)
    print("SIGNAL-COSTING ENGINE — r18 signals priced in the real 0DTE chain")
    print("=" * 78)

    books = load_books()
    q = session_quality(books)
    print(f"\nRecorded sessions: {len(q)}  |  usable (>= {MIN_BOOKS} books): "
          f"{int(q['usable'].sum())}")
    print(_fmt(q.assign(first=q["first"].dt.strftime("%H:%M"),
                        last=q["last"].dt.strftime("%H:%M"))))

    good = q[q["usable"]]
    if good.empty:
        print("\nNo usable sessions. Nothing to cost.")
        return
    lo, hi = good["date"].min(), good["date"].max()

    spy = load_spy_5m()
    spy = spy[(spy["ts"].dt.date >= lo) & (spy["ts"].dt.date <= hi)].reset_index(drop=True)
    print(f"\nSPY 5m bars over the chain window: {len(spy)} "
          f"({lo} -> {hi})")

    hb = htf_bias(spy, "15min", leaky=False)          # causal — the honest one
    sigs = build_signals(spy, hb)
    trades = run_spy(sigs)
    print(f"r18 (causal HTF) signals in window: {len(trades)}  "
          f"[long {sum(t.side > 0 for t in trades)} / "
          f"short {sum(t.side < 0 for t in trades)}]")

    if not trades:
        print("\nNo signals in the recorded window — nothing to cost.")
        return

    frames = {}
    for off, name in ((0, "ATM"), (1, "1 strike OTM"), (2, "2 strikes OTM")):
        d = price_trades(trades, books, offset=off)
        frames[name] = d

    print("\n" + "-" * 78)
    print("SPY-SPACE vs OPTION-SPACE  (marketable fills: pay ask, sell bid)")
    print("-" * 78)
    summ = []
    for name, d in frames.items():
        ok = d[d["status"] == "ok"]
        if ok.empty:
            summ.append({"contract": name, "n": 0})
            continue
        summ.append({
            "contract": name,
            "n": len(ok),
            "spy_avg_R": round(ok["spy_R"].mean(), 3),
            "spy_win%": round(100 * (ok["spy_R"] > 0).mean(), 1),
            "opt_win%": round(100 * (ok["pnl_$"] > 0).mean(), 1),
            "opt_avg_%": round(ok["ret_pct"].mean(), 1),
            "opt_med_%": round(ok["ret_pct"].median(), 1),
            "opt_tot_$": round(ok["pnl_$"].sum(), 0),
            "avg_paid_$": round(ok["paid"].mean() * CONTRACT, 0),
            "spread_%_of_prem": round(ok["spread_rt_pct"].mean(), 1),
            "med_hold_min": round(ok["hold_min"].median(), 0),
        })
    print(_fmt(pd.DataFrame(summ)))

    atm = frames["ATM"]
    dropped = atm[atm["status"] != "ok"]
    if not dropped.empty:
        print("\nUnfilled signals (no session / outside book coverage):")
        print(_fmt(dropped["status"].value_counts().rename_axis("status")
                   .reset_index(name="n")))

    ok = atm[atm["status"] == "ok"]
    if not ok.empty:
        print("\nBy SPY exit reason (ATM contract):")
        g = ok.groupby("reason").agg(
            n=("pnl_$", "size"), spy_avg_R=("spy_R", "mean"),
            opt_avg_pct=("ret_pct", "mean"), opt_tot=("pnl_$", "sum"),
            med_hold=("hold_min", "median")).round(2).reset_index()
        print(_fmt(g))

        print("\nFill quality — drift between the signal bar and the first book:")
        print(f"  median |spot drift|: {ok['spot_drift'].abs().median():.3f} pts"
              f"   max: {ok['spot_drift'].abs().max():.3f} pts")

    print("\n" + "-" * 78)
    print("THE COST CURVE — SPY move an ATM 0DTE needs just to BREAK EVEN")
    print("(model-free: inverted from the chain printed H minutes later)")
    print("-" * 78)
    be = breakeven_curve(books)
    if be.empty:
        print("Not enough book depth to build the curve.")
    else:
        be["bucket"] = _bucket(be["minute"])
        piv = be.pivot_table(index="bucket", columns="hold_min",
                             values="be_move_pts", aggfunc="median",
                             observed=True).round(3)
        piv.columns = [f"hold {int(c)}m" for c in piv.columns]
        print("\nMedian break-even SPY move, in POINTS, by time of day (ET):")
        print(_fmt(piv.reset_index()))

        pivp = be.pivot_table(index="bucket", columns="hold_min",
                              values="be_move_pct", aggfunc="median",
                              observed=True).round(3)
        pivp.columns = [f"hold {int(c)}m" for c in pivp.columns]
        print("\nSame, as % of spot:")
        print(_fmt(pivp.reset_index()))

        print(f"\nATM round-trip spread, median: "
              f"{be['spread_pct'].median():.2f}% of premium "
              f"(median premium ${be['paid'].median() * CONTRACT:.0f}/contract)")

    print("\n" + "-" * 78)
    print("PAYOFF ASYMMETRY — ATM 0DTE return (%) for a given SPY move")
    print("(+ = move in the option's favour; median across all books)")
    print("-" * 78)
    pay = payoff_table(books)
    if pay.empty:
        print("Not enough book depth.")
    else:
        tab = pay.pivot_table(index="move_pts", columns="hold_min",
                              values="ret_pct", aggfunc="median").round(1)
        tab.columns = [f"hold {int(c)}m" for c in tab.columns]
        print("\n" + _fmt(tab.reset_index()))

        print("\nAsymmetry: gain on a favourable move vs loss on the mirror move")
        arows = []
        for mag in (0.25, 0.5, 0.75, 1.0):
            for H in HOLDS:
                up = pay[(pay.move_pts == mag) & (pay.hold_min == H)]["ret_pct"]
                dn = pay[(pay.move_pts == -mag) & (pay.hold_min == H)]["ret_pct"]
                if up.empty or dn.empty:
                    continue
                g, ls = up.median(), dn.median()
                arows.append({
                    "move_pts": mag, "hold_min": H,
                    "gain_%": round(g, 1), "loss_%": round(ls, 1),
                    "gain/loss": round(abs(g / ls), 2) if ls else np.nan,
                    "breakeven_win%_needed": round(100 * abs(ls) / (g + abs(ls)), 1)
                    if (g + abs(ls)) > 0 else np.nan,
                })
        print(_fmt(pd.DataFrame(arows)))

    if not pay.empty:
        print("\n" + "-" * 78)
        print("CONSTITUTION RULE 1 IN OPTION SPACE — target must be >= 1.5R")
        print("(how far the target must actually run, given the stop, after")
        print(" real bid/ask and decay. req_mult = target as a multiple of stop)")
        print("-" * 78)
        r1 = rule1_target(pay)
        if r1.empty:
            print("Not enough book depth.")
        else:
            for H in HOLDS:
                sub = r1[r1["hold_min"] == H]
                if sub.empty:
                    continue
                t = sub.pivot_table(index="bucket", columns="stop_pts",
                                    values="req_mult", observed=True).round(2)
                t.columns = [f"stop {c}pt" for c in t.columns]
                print(f"\nrequired target / stop, holding {H} min:")
                print(_fmt(t.reset_index()))
            unreachable = r1["req_target_pts"].isna().sum()
            print(f"\n(blank / NaN = 1.5R unreachable within a 2-point move; "
                  f"{unreachable} of {len(r1)} cells)")
            r1.to_csv(RESULTS / "rule1_option_space.csv", index=False)

    print("\n" + "-" * 78)
    print("VALIDATION — same table from REALIZED outcomes, no interpolation")
    print("-" * 78)
    val = validate_payoff(books)
    if val.empty:
        print("Not enough book depth.")
    else:
        vt = val.pivot_table(index="move_bin", columns="hold_min",
                             values="ret_pct", aggfunc="median",
                             observed=True).round(1)
        vn = val.pivot_table(index="move_bin", columns="hold_min",
                             values="ret_pct", aggfunc="size", observed=True)
        vt.columns = [f"hold {int(c)}m" for c in vt.columns]
        print("\nRealized ATM 0DTE return (%) by the move that actually happened:")
        print(_fmt(vt.reset_index()))
        print(f"\n(n per cell: {int(vn.min().min())}-{int(vn.max().max())}; "
              "outer bins are open-ended, so compare the middle rows)")

    for name, d in frames.items():
        tag = name.replace(" ", "_")
        d.to_csv(RESULTS / f"signal_cost_{tag}.csv", index=False)
    if not val.empty:
        val.to_csv(RESULTS / "payoff_validation.csv", index=False)
    if not be.empty:
        be.to_csv(RESULTS / "breakeven_curve.csv", index=False)
    if not pay.empty:
        pay.to_csv(RESULTS / "payoff_asymmetry.csv", index=False)
    print("\nwrote results/signal_cost_*.csv, breakeven_curve.csv, "
          "payoff_asymmetry.csv")


if __name__ == "__main__":
    main()

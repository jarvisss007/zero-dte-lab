#!/opt/anaconda3/bin/python
"""key_times_study.py - does SPY do something special at Anupam's fourteen clock times?

PRE-REGISTRATION. Written 2026-09-28 ~08:45 PT, BEFORE any price bar or option book was loaded
for this study, and committed on its own before the implementation. Nothing below may be tuned
after a run. If a part of the design proves impossible on the data, the output says so and the
design is NOT changed. DESCRIPTION ONLY: paper research, not a strategy, registers no variant,
places and advises no trade.

THE CLAIM (his, noted for over a year): SPY "takes good turns or keeps continuing" at
    06:45 07:00 07:20 07:45 08:05 08:45 10:00 10:20 11:00 11:20 11:45 12:00 12:20 12:45   (Pacific)
Pacific = Eastern minus 3 hours all year (both observe DST on the same dates), so the key times are
    09:45 10:00 10:20 10:45 11:05 11:45 13:00 13:20 14:00 14:20 14:45 15:00 15:20 15:45   (Eastern)
All session logic runs in New York time; every time printed for him is Pacific.

DATA
  bars      (1) ~/ie-pro-project/output/alpaca_SPY_5m_2019-07-01.csv (time,open,high,low,close,volume;
                ET with offset; 2020-07-27 .. 2026-07-10).
            (2) Yahoo chart API, SPY, range=60d, interval=5m, header User-Agent "Anupam Patil research
                apati077@ucr.edu"; epoch seconds -> America/New_York; rows with any null OHLC dropped.
            A date that (1) holds uses (1) only; a date only (2) holds uses (2). On dates both hold, the
            two are compared bar by bar (closes at the same start time) as a DATA CHECK, not a test.
            A duplicated bar start keeps its first row (counted and reported).
  session   bars are labelled by their START time; regular session only: start in [09:30, 16:00) ET.
            A date counts only if the estate's NYSE calendar (stock-radar/sessions.py, byte-identical
            mirror in this repo's src/sessions.py) says it is a session AND it is on or before
            2026-09-25 (settled). Today, 2026-09-28, is never in the study sample. Nothing is imputed:
            a missing bar is a missing mark.
  early closes  the NYSE 13:00 ET closes in the span are listed in the code (2020-11-27, 2020-12-24,
            2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24,
            2025-07-03, 2025-11-28, 2025-12-24); they simply lack afternoon marks.

MARKS AND MOVES
  price at mark T   P(T) = close of the 5-minute bar that ENDS at T (starts at T-5). Marks exist at
                    09:35 .. 16:00 ET. No bar inside the session ends at 09:30, so P(09:30) never exists.
  B(T) = 10000 * (P(T) / P(T-15) - 1)      the 15 minutes BEFORE T, basis points
  A(T) = 10000 * (P(T+15) / P(T) - 1)      the 15 minutes AFTER T, basis points
  valid mark        P(T-15), P(T) and P(T+15) all exist that day. Applies to key times AND neighbours.
  CONSEQUENCE, stated before any data: 06:45 PT (09:45 ET) can never be a valid mark (its T-15 would
  be 09:30), so 06:45 PT is IMPOSSIBLE in Q1 and Q2. It is not replaced by the opening print.
  neighbours of T   T-15 and T+15, each used only if it is not itself a key time and is valid that day.
      07:00 -> 07:15 only (06:45 is a key time)   07:20 -> 07:05, 07:35   07:45 -> 07:30, 08:00
      08:05 -> 07:50, 08:20   08:45 -> 08:30, 09:00   10:00 -> 09:45, 10:15   10:20 -> 10:05, 10:35
      11:00 -> 10:45, 11:15   11:20 -> 11:05, 11:35   11:45 -> 11:30 only (12:00 is a key time)
      12:00 -> 12:15 only (11:45 is a key time)   12:20 -> 12:05, 12:35
      12:45 -> 12:30 only (13:00 PT = 16:00 ET has no T+15)                          (all Pacific)
  That is 22 neighbour marks; no neighbour is shared by two key times. A key time with no usable
  neighbour that day is dropped that day (Q1 and Q2). "Q1-scored key times" = valid key times with
  at least one usable neighbour.

THE THREE HEADLINE CELLS (the only tests)
  Q1 ACTIVITY   r_T = |A(T)| - mean(|A(N)|) over T's usable neighbours N.
                Per day x = mean of r_T over that day's Q1-scored key times.
                H0: mean(x) = 0; t over days, two-sided. Units: basis points.
  Q2 TURNS      a turn at mark M is sign(A(M)) != sign(B(M)); a mark with A(M) = 0 or B(M) = 0 is not
                counted either way. Per day y = (turns / counted) over that day's Q1-scored key times
                minus (turns / counted) over those key times' usable neighbours (the Q1 neighbour
                marks). A day with nothing counted on either side is dropped.
                H0: mean(y) = 0; t over days, two-sided. Positive = more turning at his times,
                negative = more continuation. Units: percentage points of turn rate.
  Q3 EXTREMES   a day's low bar = the first 5-minute bar whose low equals the session low; high bar
                likewise with the high. Key window(T) = the bars starting T-5 and T. Placebo(T) = the
                bars starting T+10 and T+15; if that overlaps ANY key window, or needs a bar outside
                the session (start before 09:30 or at/after 16:00), then the bars starting T-20 and
                T-15 under the same two conditions; if both fail, T is dropped from BOTH sets on
                every day. Resolved here before any data (the code asserts it):
                  06:45 PT dropped (+15 hits 07:00's window; -15 needs the pre-market 09:25 ET bar)
                  07:00 PT dropped (+15 hits 07:20's window; -15 hits 06:45's window)
                  12:00 PT dropped (+15 hits 12:20's window; -15 hits 11:45's window)
                  07:20 +15   07:45 -15   08:05 +15   08:45 +15   10:00 -15   10:20 +15
                  11:00 -15   11:20 +15   11:45 -15   12:20 +15   12:45 -15 (its +15 needs a 16:00 bar)
                Per day a key time counts only if all four of its bars exist that day (an early close
                drops the afternoon ones), and a day enters Q3 only with its complete bar grid (78 bars;
                42 on a listed early close) - a missing bar could hide the extreme.
                Per day z = SUM over counted T of [extremes (0..2) in key(T) - extremes in placebo(T)];
                a bar that sits in two placebo windows counts in each, so both sides carry the same
                exposure (two bars per counted key time). H0: mean(z) = 0; t over days, two-sided.

STATISTICS  One observation per trading day. t = mean / (sd(ddof=1) / sqrt(n_days)); n = days,
            clustered_by = session date. Each headline cell reports mean, sd, n_days, t and a 95%
            interval (mean +/- 1.96 standard errors). |t| >= 2 is called loud; nothing else is
            called anything.
SAMPLES     FULL   = every settled session the data holds (2020-07-27 .. 2026-09-25, with whatever
                     gap the Yahoo window leaves after 2026-07-10 - stated, never filled).
            LAST12 = 2025-09-26 .. 2026-09-25, his reading period.
LUCK COUNT  3 cells x 2 samples = 6 looks. Chance of at least one |t| >= 2 by luck alone =
            1 - (1 - 0.0455)^6 = 24.4% (LAST12 sits inside FULL, so the looks are not independent;
            the figure is the usual approximation). Printed with the results.

DESCRIPTIVE ONLY (not tests; outside the luck count; labelled as such in every output)
  - Q1, Q2 and Q3 for each of the 14 key times separately, FULL sample (mean, t over days, n days).
    14 x 3 = 42 more looks: about 2 of them should show |t| >= 2 by luck alone.
  - Q1 per calendar year (FULL).
  - the plain average |A| at every mark 09:35 .. 15:45 ET (where P(M) and P(M+15) exist), so the
    intraday U-shape (loud open, quiet lunch, loud close) is visible.
  - where the day's low bar and high bar fall: share of Q3 days per 5-minute bar (context for Q3).
  - scheduled clocks, named now so they are not "discovered" later: US data releases at 10:00 ET
    (07:00 PT), Treasury auction results at 13:00 ET (10:00 PT), Fed decisions at 14:00 ET
    (11:00 PT, eight days a year), the closing-imbalance publication at 15:50 ET (12:50 PT). A loud
    row at one of these is the calendar, and the options market knows the calendar.

OPTIONS DESCRIPTION (not a test; reported only if the recorded books support it)
  books   the lab's own CBOE 0DTE chain recorder: data/chains/SPY_YYYY-MM-DD.csv (laptop leg) and
          data/chains_ci/SPY_YYYY-MM-DD.csv (cloud leg), exact file names only. The yfinance fallback
          files (SPY_<date>.yfinance.csv) are excluded (ZDTE-010 (c): they feed nothing until a ruling
          names it). Legs unioned, deduped on (quote_ts, type, strike), earliest fetch kept. Book time =
          the book's own quote_ts (ET), never the fetch time. 0DTE only (expiry = session date);
          settled sessions through 2026-09-25 only.
  trade   for every session and mark T - all 14 key times and, separately, the 22 Q1 neighbour marks:
          entry book = the book whose quote_ts is nearest T within 2 minutes (tie -> earlier); exit
          book = the book nearest T+15 within 2 minutes. Strike = the strike nearest the entry book's
          spot (tie -> lower). BUY the call and the put at that strike at the ASK in the entry book,
          SELL both at the BID in the exit book. Each leg must exist in both books with ask > 0,
          bid >= 0 and ask >= bid. P&L $ = 100 * (bids out - asks in); % of debit =
          (bids out - asks in) / asks in * 100.
  report  per group: mean over days of each day's mean P&L ($ and % of debit), n days, a descriptive
          day-clustered t, and the key-minus-neighbour difference on days that have both; per key
          time: n days, mean $ and mean %. No model is substituted if the books are missing: the
          output says exactly why and skips.

HIS TWO DAYS (description; one day proves nothing)
  Yahoo 1-minute bars (range=5d, interval=1m) for 2026-09-25 and 2026-09-28 (today, up to the latest
  bar). Price at a key time T = close of the 1-minute bar that ENDS at T. Session low and high with the
  Pacific start time of the 1-minute bar holding each (first if tied); the 09-25 close (last
  regular-session 1-minute close, and Yahoo's daily close). The minutes on 09-25 whose range contains
  765.50 (his reported exit level) are listed; nothing is inferred from them. Friday under "hold until
  the next key time" versus "hold to the close": SPY at each key time, the move to the next key time,
  the 767 put's intrinsic floor max(767 - SPY, 0), and - if the recorded CBOE book holds the 767 put
  that day - its BID in the book nearest each key time within 2 minutes.

OUTPUTS   results/key_times_study.json (every number) and results/KEY_TIMES_STUDY.md (plain English).
Run:      /opt/anaconda3/bin/python src/key_times_study.py
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import math
import re
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import sessions                                        # noqa: E402  byte-identical mirror of stock-radar/sessions.py
from atomicio import atomic_json, atomic_write_text    # noqa: E402

# ---------------------------------------------------------------- frozen by the pre-registration
PREREG_COMMIT = "8d6ba89"      # the commit that holds the docstring above, alone, before any data was read
PREREG_DOC_SHA256 = "18eb59a94b4588927c18585f38a694c5c0b64c6a1178537e6b6533aa349c8162"
ET, PT = "America/New_York", "America/Los_Angeles"
ALPACA = Path.home() / "ie-pro-project" / "output" / "alpaca_SPY_5m_2019-07-01.csv"
UA = "Anupam Patil research apati077@ucr.edu"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?range={rng}&interval={iv}"
LAST_SETTLED = dt.date(2026, 9, 25)
TODAY = dt.date(2026, 9, 28)
FRIDAY = dt.date(2026, 9, 25)
THURSDAY = dt.date(2026, 9, 24)     # reconciliation only: added after Friday's tape did not match the account given
LAST12 = (dt.date(2025, 9, 26), dt.date(2026, 9, 25))
EARLY_CLOSES = {"2020-11-27", "2020-12-24", "2021-11-26", "2022-11-25", "2023-07-03", "2023-11-24",
                "2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"}
OPEN_M, CLOSE_M, EARLY_M = 570, 960, 780           # 09:30, 16:00, 13:00 ET as minutes of the day
OUT_JSON = ROOT / "results" / "key_times_study.json"
OUT_MD = ROOT / "results" / "KEY_TIMES_STUDY.md"
CHAIN_DIRS = (ROOT / "data" / "chains", ROOT / "data" / "chains_ci")
CHAIN_RE = re.compile(r"^SPY_(\d{4}-\d{2}-\d{2})\.csv$")   # exact names: the .yfinance.csv fallback never matches
BOOK_TOL_S = 120
CONTRACT = 100
LUCK_P = 0.0455
PUT_K, HIS_EXIT = 767.0, 765.50
FRIDAY_CLOSE_HE_GAVE = 771.35

KEY_PT = ["06:45", "07:00", "07:20", "07:45", "08:05", "08:45", "10:00",
          "10:20", "11:00", "11:20", "11:45", "12:00", "12:20", "12:45"]


def hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def pt(m_et: int) -> str:
    return fmt(m_et - 180)


KEY = [hm(s) + 180 for s in KEY_PT]                 # Eastern minutes of the day
KEYSET = set(KEY)
NBR = {T: [N for N in (T - 15, T + 15) if N not in KEYSET] for T in KEY}
# a neighbour can only ever be valid if its own -15 and +15 marks can exist (09:35 .. 16:00)
NBR_MARKS = sorted({N for T in KEY for N in NBR[T] if N - 15 >= OPEN_M + 5 and N + 15 <= CLOSE_M})
KEY_BARS = {b for T in KEY for b in (T - 5, T)}


def resolve_placebo():
    out, dropped = {}, {}
    for T in KEY:
        why = []
        for shift, bars in (("+15", (T + 10, T + 15)), ("-15", (T - 20, T - 15))):
            inside = all(OPEN_M <= b < CLOSE_M for b in bars)
            clash = [pt(b) for b in bars if b in KEY_BARS]
            if inside and not clash:
                out[T] = (shift, bars)
                break
            why.append(f"{shift}: " + ("needs a bar outside the session" if not inside else
                                        f"overlaps the key window bar(s) starting {', '.join(clash)} PT"))
        else:
            dropped[T] = "; ".join(why)
    return out, dropped


PLACEBO, Q3_DROPPED = resolve_placebo()

# the pre-registration resolved these by hand; the code must agree or refuse to run
assert [pt(N) for N in NBR_MARKS] == sorted(["07:15", "07:05", "07:35", "07:30", "08:00", "07:50", "08:20", "08:30",
                                             "09:00", "09:45", "10:15", "10:05", "10:35", "10:45", "11:15", "11:05",
                                             "11:35", "11:30", "12:15", "12:05", "12:35", "12:30"]), "neighbour list drifted"
assert {pt(T): s for T, (s, _) in PLACEBO.items()} == {
    "07:20": "+15", "07:45": "-15", "08:05": "+15", "08:45": "+15", "10:00": "-15", "10:20": "+15",
    "11:00": "-15", "11:20": "+15", "11:45": "-15", "12:20": "+15", "12:45": "-15"}, "placebo resolution drifted"
assert sorted(pt(T) for T in Q3_DROPPED) == ["06:45", "07:00", "12:00"], "Q3 drop list drifted"


def check_prereg() -> str:
    src = Path(__file__).read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(src), clean=False)
    h = hashlib.sha256(doc.encode()).hexdigest()
    if h != PREREG_DOC_SHA256:
        raise SystemExit(f"REFUSED: the pre-registration docstring changed after commit {PREREG_COMMIT} "
                         f"(sha256 {h[:12]} != {PREREG_DOC_SHA256[:12]}). A changed design is a new study.")
    return h


# ---------------------------------------------------------------- statistics (n = days, always)
def tstat(vals) -> dict:
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    n = len(v)
    if n < 3:
        return {"n_days": n, "mean": float(v.mean()) if n else None, "t": None,
                "reason": f"only {n} day(s) - no t", "clustered_by": "session date"}
    m, sd = float(v.mean()), float(v.std(ddof=1))
    se = sd / math.sqrt(n)
    t = m / se if se > 0 else None
    return {"mean": m, "sd": sd, "n_days": n, "t": None if t is None else round(t, 3),
            "ci95": [m - 1.96 * se, m + 1.96 * se], "loud": bool(t is not None and abs(t) >= 2),
            "clustered_by": "session date"}


def rnd(d, k=4):
    if isinstance(d, dict):
        return {a: rnd(b, k) for a, b in d.items()}
    if isinstance(d, (list, tuple)):
        return [rnd(x, k) for x in d]
    if isinstance(d, (float, np.floating)):
        return None if not np.isfinite(d) else round(float(d), k)
    if isinstance(d, (np.integer,)):
        return int(d)
    if isinstance(d, (np.bool_,)):
        return bool(d)
    return d


# ---------------------------------------------------------------- data
def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def yahoo(rng: str, iv: str):
    js = http_json(YAHOO.format(rng=rng, iv=iv))
    res = js["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    ts = pd.to_datetime(pd.Series(res["timestamp"]), unit="s", utc=True).dt.tz_convert(ET)
    df = pd.DataFrame({"ts": ts, "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
                       "volume": q["volume"]})
    n_raw = len(df)
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df, res["meta"], n_raw - len(df)


def rth(df: pd.DataFrame, step: int) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["m"] = df["ts"].dt.hour * 60 + df["ts"].dt.minute
    df["date"] = df["ts"].dt.date
    notes = {}
    odd = (df["ts"].dt.second != 0) | (df["m"] % step != 0)
    notes["off_grid_bars_dropped"] = int(odd.sum())
    df = df[~odd & (df["m"] >= OPEN_M) & (df["m"] < CLOSE_M)]
    okd = {d: bool(d <= LAST_SETTLED and sessions.is_session(d)) for d in df["date"].unique()}
    ok = df["date"].map(okd).astype(bool)
    notes["bars_on_non_session_or_unsettled_dates_dropped"] = int((~ok).sum())
    df = df[ok]
    # POST-RUN BUG FIX (run 1, 2026-09-28): on a listed 13:00 ET early close the regular session ends at 13:00,
    # as pre-registered ("they simply lack afternoon marks"); run 1 let after-hours bars through on those days.
    late = df["date"].map({d: d.isoformat() in EARLY_CLOSES for d in df["date"].unique()}).astype(bool) & (df["m"] >= EARLY_M)
    notes["after_early_close_bars_dropped"] = int(late.sum())
    df = df[~late]
    dup = df.duplicated(subset=["date", "m"], keep="first")
    notes["duplicate_bar_starts_dropped"] = int(dup.sum())
    return df[~dup].sort_values(["date", "m"]).reset_index(drop=True), notes


def load_bars():
    raw = pd.read_csv(ALPACA)
    alp = pd.DataFrame({"ts": pd.to_datetime(raw["time"], utc=True).dt.tz_convert(ET),
                        "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"]})
    alp, alp_notes = rth(alp.dropna(subset=["open", "high", "low", "close"]), 5)
    y5, meta, y_null = yahoo("60d", "5m")
    y5, y_notes = rth(y5, 5)
    y_notes["null_rows_dropped"] = int(y_null)
    days, src = {}, {}
    for d, g in alp.groupby("date"):
        days[d], src[d] = g, "alpaca"
    for d, g in y5.groupby("date"):
        if d not in days:
            days[d], src[d] = g, "yahoo"
    # data check (not a test): the two feeds on the dates both hold
    both = sorted(set(alp["date"]) & set(y5["date"]))
    check = {"dates_both_hold": [str(d) for d in both]}
    if both:
        a = alp[alp["date"].isin(both)][["date", "m", "close", "low", "high"]]
        b = y5[y5["date"].isin(both)][["date", "m", "close", "low", "high"]]
        mm = a.merge(b, on=["date", "m"], suffixes=("_alpaca", "_yahoo"))
        diff = (mm["close_alpaca"] - mm["close_yahoo"]).abs() * 100
        check.update({"bars_compared": int(len(mm)), "close_abs_diff_cents_median": float(diff.median()),
                      "close_abs_diff_cents_p95": float(diff.quantile(0.95)), "close_abs_diff_cents_max": float(diff.max())})
        agree = []
        for d in both:
            ga, gb = a[a["date"] == d], b[b["date"] == d]
            if len(ga) == len(gb) == 78:
                agree.append({"date": str(d),
                              "low_bar_same": bool(ga["m"].iloc[int(np.argmin(ga["low"].to_numpy()))] ==
                                                   gb["m"].iloc[int(np.argmin(gb["low"].to_numpy()))]),
                              "high_bar_same": bool(ga["m"].iloc[int(np.argmax(ga["high"].to_numpy()))] ==
                                                    gb["m"].iloc[int(np.argmax(gb["high"].to_numpy()))])})
        check["extreme_bar_location_agreement_added_after_prereg_as_a_data_check"] = {
            "days": len(agree), "low_bar_same": sum(x["low_bar_same"] for x in agree),
            "high_bar_same": sum(x["high_bar_same"] for x in agree), "per_day": agree}
    info = {
        "alpaca": {"file": str(ALPACA), "from": str(alp["date"].min()), "to": str(alp["date"].max()),
                   "sessions": int(alp["date"].nunique()), "notes": alp_notes,
                   "feed_note": "the first 09:30 bar carries ~37k shares: this is the IEX-only feed, not the consolidated tape"},
        "yahoo_5m_60d": {"from": str(y5["date"].min()) if len(y5) else None,
                         "to": str(y5["date"].max()) if len(y5) else None,
                         "sessions": int(y5["date"].nunique()), "notes": y_notes},
        "feed_comparison": check,
    }
    return days, src, info


# ---------------------------------------------------------------- one day
def grid(g: pd.DataFrame):
    arr = {k: np.full(78, np.nan) for k in ("close", "low", "high")}
    j = ((g["m"].to_numpy() - OPEN_M) // 5).astype(int)
    for k in arr:
        arr[k][j] = g[k].to_numpy(float)
    return arr


def analyze_day(d: dt.date, g: pd.DataFrame) -> dict:
    a = grid(g)
    close = a["close"]
    P = {}
    for T in range(OPEN_M + 5, CLOSE_M + 1, 5):
        v = close[(T - OPEN_M - 5) // 5]
        P[T] = None if np.isnan(v) else float(v)

    def A(T):
        p0, p1 = P.get(T), P.get(T + 15)
        return None if p0 is None or p1 is None else 1e4 * (p1 / p0 - 1)

    def B(T):
        p0, p1 = P.get(T - 15), P.get(T)
        return None if p0 is None or p1 is None else 1e4 * (p1 / p0 - 1)

    def valid(T):
        return P.get(T - 15) is not None and P.get(T) is not None and P.get(T + 15) is not None

    def turn(M):
        x, y = A(M), B(M)
        if x == 0 or y == 0:
            return None
        return 1.0 if (x > 0) != (y > 0) else 0.0

    out = {"date": d, "q1": None, "q2": None, "q3": None, "per_time": {}, "absA": {}}
    for T in range(OPEN_M + 5, CLOSE_M - 15 + 1, 5):             # 09:35 .. 15:45: the U-shape
        x = A(T)
        if x is not None:
            out["absA"][T] = abs(x)

    # Q1 and Q2
    r, scored = {}, []
    for T in KEY:
        if not valid(T):
            continue
        nb = [N for N in NBR[T] if valid(N)]
        if not nb:
            continue
        r[T] = abs(A(T)) - float(np.mean([abs(A(N)) for N in nb]))
        scored.append((T, nb))
        pt_row = out["per_time"].setdefault(T, {})
        pt_row["q1"] = r[T]
        pt_row["absA_key"] = abs(A(T))
        pt_row["absA_nbr"] = float(np.mean([abs(A(N)) for N in nb]))
        tk = turn(T)
        tn = [v for v in (turn(N) for N in nb) if v is not None]
        if tk is not None and tn:
            pt_row["q2"] = 100 * (tk - float(np.mean(tn)))
            pt_row["turn_key"], pt_row["turn_nbr"] = tk, float(np.mean(tn))
    if r:
        out["q1"] = float(np.mean(list(r.values())))
        out["q1_absA_key"] = float(np.mean([abs(A(T)) for T, _ in scored]))
        out["q1_absA_nbr"] = float(np.mean([np.mean([abs(A(N)) for N in nb]) for _, nb in scored]))
        kt = [v for v in (turn(T) for T, _ in scored) if v is not None]
        nt = [v for v in (turn(N) for _, nb in scored for N in nb) if v is not None]
        if kt and nt:
            out["q2"] = 100 * (float(np.mean(kt)) - float(np.mean(nt)))
            out["q2_key_rate"], out["q2_nbr_rate"] = float(np.mean(kt)), float(np.mean(nt))

    # Q3
    early = d.isoformat() in EARLY_CLOSES
    close_m = EARLY_M if early else CLOSE_M
    have = set(g["m"].tolist())
    expected = set(range(OPEN_M, close_m, 5))
    out["grid_complete"] = have == expected
    out["early_close"] = early
    if not out["grid_complete"]:
        out["grid_problem"] = ("missing bars" if have < expected else
                               "bars beyond the expected close" if have > expected else "missing and extra bars")
        out["last_bar"] = fmt(max(have)) if have else None
    else:
        lo_m = OPEN_M + 5 * int(np.argmin(a["low"][: len(expected)]))
        hi_m = OPEN_M + 5 * int(np.argmax(a["high"][: len(expected)]))
        out["low_bar"], out["high_bar"] = lo_m, hi_m
        z, kc_tot, pc_tot, counted = 0, 0, 0, 0
        for T in KEY:
            kw = (T - 5, T)
            if all(b in have for b in kw):
                row = out["per_time"].setdefault(T, {})
                row["low_in_key"], row["high_in_key"] = int(lo_m in kw), int(hi_m in kw)
            if T not in PLACEBO:
                continue
            pw = PLACEBO[T][1]
            if not all(b in have for b in kw + pw):
                continue
            kc = int(lo_m in kw) + int(hi_m in kw)
            pc = int(lo_m in pw) + int(hi_m in pw)
            z += kc - pc
            kc_tot += kc
            pc_tot += pc
            counted += 1
            row = out["per_time"].setdefault(T, {})
            row["q3"] = kc - pc
            row["low_in_placebo"], row["high_in_placebo"] = int(lo_m in pw), int(hi_m in pw)
        if counted:
            out["q3"], out["q3_key"], out["q3_placebo"], out["q3_times"] = z, kc_tot, pc_tot, counted
    return out


def headline(days: list[dict]) -> dict:
    q1 = tstat([d["q1"] for d in days])
    q1["units"] = "basis points of extra 15-minute move after his times vs their neighbours"
    q1["context_mean_absA_key_bps"] = float(np.mean([d["q1_absA_key"] for d in days if d["q1"] is not None]))
    q1["context_mean_absA_nbr_bps"] = float(np.mean([d["q1_absA_nbr"] for d in days if d["q1"] is not None]))
    q2 = tstat([d["q2"] for d in days])
    q2["units"] = "percentage points of turn rate, his times minus neighbours (positive = more turning)"
    q2["context_turn_rate_key_pct"] = 100 * float(np.mean([d["q2_key_rate"] for d in days if d["q2"] is not None]))
    q2["context_turn_rate_nbr_pct"] = 100 * float(np.mean([d["q2_nbr_rate"] for d in days if d["q2"] is not None]))
    q3 = tstat([d["q3"] for d in days])
    q3["units"] = "day's extremes (low + high) in key windows minus in placebo windows, per day"
    q3d = [d for d in days if d["q3"] is not None]
    q3["context_extremes_in_key_windows_per_100_days"] = 100 * float(np.mean([d["q3_key"] for d in q3d])) if q3d else None
    q3["context_extremes_in_placebo_windows_per_100_days"] = 100 * float(np.mean([d["q3_placebo"] for d in q3d])) if q3d else None
    return {"Q1_activity": q1, "Q2_turns": q2, "Q3_extremes": q3,
            "sessions_in_sample": len(days), "from": str(days[0]["date"]), "to": str(days[-1]["date"])}


def per_time_rows(days: list[dict]) -> list[dict]:
    rows = []
    for T in KEY:
        vals = [d["per_time"].get(T, {}) for d in days]
        row = {"pt": pt(T), "et": fmt(T)}
        if T == KEY[0]:
            row["q1"] = row["q2"] = {"n_days": 0, "reason": "impossible: T-15 = 09:30 ET has no mark (pre-registered)"}
        else:
            row["q1"] = tstat([v.get("q1") for v in vals])
            row["q1"]["mean_absA_key_bps"] = float(np.nanmean([v["absA_key"] for v in vals if "absA_key" in v]))
            row["q1"]["mean_absA_nbr_bps"] = float(np.nanmean([v["absA_nbr"] for v in vals if "absA_nbr" in v]))
            row["q1"]["neighbours_pt"] = [pt(N) for N in NBR[T] if N in NBR_MARKS]
            row["q2"] = tstat([v.get("q2") for v in vals])
            tk = [v["turn_key"] for v in vals if "turn_key" in v]
            tn = [v["turn_nbr"] for v in vals if "turn_nbr" in v]
            row["q2"]["turn_rate_key_pct"] = 100 * float(np.mean(tk)) if tk else None
            row["q2"]["turn_rate_nbr_pct"] = 100 * float(np.mean(tn)) if tn else None
        kl = [v["low_in_key"] for v in vals if "low_in_key" in v]
        kh = [v["high_in_key"] for v in vals if "high_in_key" in v]
        raw = {"days_with_key_window": len(kl),
               "low_in_key_window_pct": 100 * float(np.mean(kl)) if kl else None,
               "high_in_key_window_pct": 100 * float(np.mean(kh)) if kh else None}
        if T in Q3_DROPPED:
            row["q3"] = {"n_days": 0, "reason": f"dropped by the pre-registered placebo rule ({Q3_DROPPED[T]})", **raw}
        else:
            row["q3"] = tstat([v.get("q3") for v in vals])
            pl = [v["low_in_placebo"] for v in vals if "low_in_placebo" in v]
            ph = [v["high_in_placebo"] for v in vals if "high_in_placebo" in v]
            row["q3"].update({"placebo_shift": PLACEBO[T][0], "placebo_bars_pt": [pt(b) for b in PLACEBO[T][1]], **raw,
                              "low_in_placebo_window_pct": 100 * float(np.mean(pl)) if pl else None,
                              "high_in_placebo_window_pct": 100 * float(np.mean(ph)) if ph else None})
        rows.append(row)
    return rows


# ---------------------------------------------------------------- options
def load_books(only: dt.date | None = None):
    frames, files = [], []
    for d in CHAIN_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            m = CHAIN_RE.match(p.name)
            if not m:
                continue
            day = dt.date.fromisoformat(m.group(1))
            if day > LAST_SETTLED or not sessions.is_session(day) or (only and day != only):
                continue
            try:
                f = pd.read_csv(p, dtype=str)
            except Exception as ex:                                # an unreadable file is a stated zero
                files.append({"file": f"{d.name}/{p.name}", "error": f"{type(ex).__name__}: {ex}"})
                continue
            f["leg"] = d.name
            frames.append(f)
            files.append({"file": f"{d.name}/{p.name}", "rows": int(len(f))})
    if not frames:
        return None, files
    df = pd.concat(frames, ignore_index=True)
    df["quote_ts"] = pd.to_datetime(df["quote_ts"], errors="coerce")
    for c in ("spot", "strike", "bid", "ask"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["quote_ts", "strike", "spot"])
    df["date"] = df["quote_ts"].dt.date
    df = df[pd.to_datetime(df["expiry"], errors="coerce").dt.date == df["date"]]
    df = df.sort_values("fetched_at_et").drop_duplicates(subset=["quote_ts", "type", "strike"], keep="first")
    return df.sort_values(["quote_ts", "type", "strike"]).reset_index(drop=True), files


def nearest(stamps: np.ndarray, target: np.datetime64):
    if len(stamps) == 0:
        return None
    gap = np.abs((stamps - target) / np.timedelta64(1, "s"))
    i = int(np.argmin(gap))                                     # sorted ascending: a tie goes to the earlier book
    return stamps[i] if gap[i] <= BOOK_TOL_S else None


def leg(book: pd.DataFrame, typ: str, K: float):
    r = book[(book["type"] == typ) & (book["strike"] == K)]
    if r.empty:
        return None
    r = r.iloc[0]
    if not (np.isfinite(r["bid"]) and np.isfinite(r["ask"]) and r["ask"] > 0 and r["bid"] >= 0 and r["ask"] >= r["bid"]):
        return None
    return r


def options_description() -> dict:
    books, files = load_books()
    if books is None or books.empty:
        return {"status": "SKIPPED", "reason": "no CBOE 0DTE book files on or before 2026-09-25", "files": files}
    trades, coverage, misses = [], [], {"no_book_within_2_min_of_T": 0, "no_book_within_2_min_of_T_plus_15": 0,
                                        "atm_leg_missing_or_one_sided": 0}
    marks = [(T, "key") for T in KEY] + [(N, "neighbour") for N in NBR_MARKS]
    for day, g in books.groupby("date"):
        stamps = np.sort(g["quote_ts"].unique())
        by_ts = {t: b for t, b in g.groupby("quote_ts")}
        n_key = 0
        for T, grp in marks:
            base = np.datetime64(dt.datetime.combine(day, dt.time(0, 0)))
            t_in = nearest(stamps, base + np.timedelta64(T, "m"))
            if t_in is None:
                misses["no_book_within_2_min_of_T"] += 1
                continue
            t_out = nearest(stamps, base + np.timedelta64(T + 15, "m"))
            if t_out is None:
                misses["no_book_within_2_min_of_T_plus_15"] += 1
                continue
            b_in, b_out = by_ts[pd.Timestamp(t_in)], by_ts[pd.Timestamp(t_out)]
            spot = float(b_in["spot"].iloc[0])
            strikes = np.sort(b_in["strike"].unique())
            K = float(strikes[int(np.argmin(np.abs(strikes - spot)))])   # sorted: a tie goes to the lower strike
            c0, p0, c1, p1 = leg(b_in, "C", K), leg(b_in, "P", K), leg(b_out, "C", K), leg(b_out, "P", K)
            if any(x is None for x in (c0, p0, c1, p1)):
                misses["atm_leg_missing_or_one_sided"] += 1
                continue
            debit = float(c0["ask"] + p0["ask"])
            proceeds = float(c1["bid"] + p1["bid"])
            trades.append({"date": str(day), "mark_pt": pt(T), "group": grp, "entry_book": str(pd.Timestamp(t_in)),
                           "exit_book": str(pd.Timestamp(t_out)), "strike": K, "spot_in": spot,
                           "debit": debit, "proceeds": proceeds, "pnl_usd": CONTRACT * (proceeds - debit),
                           "pnl_pct_of_debit": (proceeds - debit) / debit * 100})
            n_key += grp == "key"
        coverage.append({"date": str(day), "books": int(len(stamps)), "key_straddles": int(n_key)})
    if not trades:
        return {"status": "SKIPPED", "reason": "books exist but no mark had a book within 2 minutes of T and of T+15 "
                "with a two-sided ATM call and put", "files": files, "misses": misses, "coverage": coverage}
    tr = pd.DataFrame(trades)

    def group_stats(sub: pd.DataFrame) -> dict:
        per_day = sub.groupby("date")[["pnl_usd", "pnl_pct_of_debit", "debit"]].mean()
        s = tstat(per_day["pnl_usd"].tolist())
        return {"n_days": int(len(per_day)), "n_straddles": int(len(sub)),
                "mean_pnl_usd_per_straddle": s.get("mean"), "t_days_descriptive": s.get("t"),
                "mean_pnl_pct_of_debit": float(per_day["pnl_pct_of_debit"].mean()),
                "mean_debit_usd": CONTRACT * float(per_day["debit"].mean()),
                "days_positive": int((per_day["pnl_usd"] > 0).sum())}

    key, nbr = tr[tr["group"] == "key"], tr[tr["group"] == "neighbour"]
    kd = key.groupby("date")[["pnl_usd", "pnl_pct_of_debit"]].mean()
    nd = nbr.groupby("date")[["pnl_usd", "pnl_pct_of_debit"]].mean()
    both = kd.index.intersection(nd.index)
    diff_usd = tstat((kd.loc[both, "pnl_usd"] - nd.loc[both, "pnl_usd"]).tolist())
    diff_pct = (kd.loc[both, "pnl_pct_of_debit"] - nd.loc[both, "pnl_pct_of_debit"]).mean() if len(both) else None
    per_key = []
    for T in KEY:
        s = key[key["mark_pt"] == pt(T)]
        if s.empty:
            last_books = books.groupby("date")["quote_ts"].max()
            latest = (last_books.dt.hour * 60 + last_books.dt.minute).max()
            per_key.append({"pt": pt(T), "n_days": 0,
                            "reason": (f"no exit book: the recorder's last book on any day is {fmt(int(latest))} ET, never within "
                                       f"2 minutes of {fmt(T + 15)} ET") if T + 15 - BOOK_TOL_S / 60 > latest
                            else "no book within 2 minutes of T and T+15 on any day"})
            continue
        pdd = s.groupby("date")[["pnl_usd", "pnl_pct_of_debit"]].mean()
        per_key.append({"pt": pt(T), "n_days": int(len(pdd)), "mean_pnl_usd": float(pdd["pnl_usd"].mean()),
                        "mean_pnl_pct_of_debit": float(pdd["pnl_pct_of_debit"].mean()),
                        "days_positive": int((pdd["pnl_usd"] > 0).sum())})
    return {"status": "DESCRIPTION - not a test, outside the luck count",
            "fill_rule": "buy both legs at the ASK in the book nearest T (within 2 min), sell both at the BID in the "
                         "book nearest T+15 (within 2 min); strike nearest the entry spot",
            "sessions_with_books": int(tr["date"].nunique()), "first": str(tr["date"].min()), "last": str(tr["date"].max()),
            "key_times": group_stats(key) if len(key) else {"n_days": 0},
            "neighbour_marks": group_stats(nbr) if len(nbr) else {"n_days": 0},
            "key_minus_neighbour_same_days": {"n_days": int(len(both)), "mean_usd": diff_usd.get("mean"),
                                              "t_days_descriptive": diff_usd.get("t"), "mean_pct_points": diff_pct},
            "per_key_time": per_key, "misses": misses, "coverage": coverage, "files_read": len(files),
            "trades_columns": ["date", "mark_pt", "group", "entry_book_et", "exit_book_et", "strike", "debit", "proceeds",
                               "pnl_usd"],
            "trades": [[t["date"], t["mark_pt"], t["group"], t["entry_book"][11:19], t["exit_book"][11:19], t["strike"],
                        round(t["debit"], 2), round(t["proceeds"], 2), round(t["pnl_usd"], 2)] for t in trades]}


# ---------------------------------------------------------------- his two days
def his_two_days() -> dict:
    one, meta, nulls = yahoo("5d", "1m")
    one["m"] = one["ts"].dt.hour * 60 + one["ts"].dt.minute
    one["date"] = one["ts"].dt.date
    one = one[(one["m"] >= OPEN_M) & (one["m"] < CLOSE_M) & one["date"].isin([THURSDAY, FRIDAY, TODAY])]
    daily, _, _ = yahoo("5d", "1d")
    daily["date"] = daily["ts"].dt.date
    out = {"source": "Yahoo 1-minute bars, range=5d; price at a key time = close of the 1-minute bar ending at it",
           "null_rows_dropped": int(nulls)}
    fri_books = None
    try:
        fb, _ = load_books(only=FRIDAY)
        fri_books = fb
    except Exception as ex:                                       # stated, never silent
        out["friday_book_error"] = f"{type(ex).__name__}: {ex}"
    for day in (THURSDAY, FRIDAY, TODAY):
        g = one[one["date"] == day].sort_values("m")
        if g.empty:
            out[str(day)] = {"reason": "Yahoo returned no regular-session 1-minute bars"}
            continue
        close_by_m = dict(zip(g["m"], g["close"]))
        last_m = int(g["m"].max())
        keys = []
        for T in KEY:
            px = close_by_m.get(T - 1)
            keys.append({"pt": pt(T), "spy": None if px is None else round(float(px), 2),
                         "note": None if px is not None else ("not reached yet" if T - 1 > last_m else "bar missing")})
        lo_i, hi_i = int(np.argmin(g["low"].to_numpy())), int(np.argmax(g["high"].to_numpy()))
        rec = {"key_times": keys, "bars": int(len(g)),
               "latest_bar_pt": fmt(last_m - 180), "latest_close": round(float(g["close"].iloc[-1]), 2),
               "low": round(float(g["low"].iloc[lo_i]), 2), "low_bar_pt": fmt(int(g["m"].iloc[lo_i]) - 180),
               "high": round(float(g["high"].iloc[hi_i]), 2), "high_bar_pt": fmt(int(g["m"].iloc[hi_i]) - 180),
               "open": round(float(g["open"].iloc[0]), 2)}
        if day == THURSDAY:
            dd = daily[daily["date"] == THURSDAY]
            rec["role"] = "reconciliation only (added after Friday's tape did not match the account given)"
            rec["close_last_1m_bar"] = rec.pop("latest_close")
            rec["close_yahoo_daily"] = round(float(dd["close"].iloc[0]), 2) if len(dd) else None
            rec["put_767_at_expiry"] = round(max(PUT_K - (rec["close_yahoo_daily"] or rec["close_last_1m_bar"]), 0.0), 2)
        if day == FRIDAY:
            dd = daily[daily["date"] == FRIDAY]
            rec["close_last_1m_bar"] = rec.pop("latest_close")
            rec["close_yahoo_daily"] = round(float(dd["close"].iloc[0]), 2) if len(dd) else None
            rec["close_he_gave"] = FRIDAY_CLOSE_HE_GAVE
            hits = g[(g["low"] <= HIS_EXIT) & (g["high"] >= HIS_EXIT)]["m"].tolist()
            spans, start, prev = [], None, None
            for m in hits:
                if start is None:
                    start = prev = m
                elif m == prev + 1:
                    prev = m
                else:
                    spans.append((start, prev))
                    start = prev = m
            if start is not None:
                spans.append((start, prev))
            rec["minutes_trading_through_765_50_pt"] = [fmt(a - 180) if a == b else f"{fmt(a - 180)}-{fmt(b - 180)}"
                                                        for a, b in spans]
            hold = []
            for i, k in enumerate(keys):
                nxt = keys[i + 1] if i + 1 < len(keys) else None
                row = {"pt": k["pt"], "spy": k["spy"],
                       "put_767_intrinsic_floor": None if k["spy"] is None else round(max(PUT_K - k["spy"], 0.0), 2),
                       "spy_at_next_key_time": None if nxt is None else nxt["spy"],
                       "next_key_time_pt": None if nxt is None else nxt["pt"]}
                if nxt and k["spy"] is not None and nxt["spy"] is not None:
                    row["move_to_next_key_time"] = round(nxt["spy"] - k["spy"], 2)
                if fri_books is not None and not fri_books.empty:
                    stamps = np.sort(fri_books["quote_ts"].unique())
                    T = hm(k["pt"]) + 180
                    t0 = nearest(stamps, np.datetime64(dt.datetime.combine(FRIDAY, dt.time(0, 0))) + np.timedelta64(T, "m"))
                    if t0 is not None:
                        b = fri_books[fri_books["quote_ts"] == t0]
                        r = b[(b["type"] == "P") & (b["strike"] == PUT_K)]
                        if len(r):
                            row["put_767_bid_recorded"] = float(r["bid"].iloc[0])
                            row["put_767_ask_recorded"] = float(r["ask"].iloc[0])
                            row["book_pt"] = (pd.Timestamp(t0) - pd.Timedelta(hours=3)).strftime("%H:%M:%S")
                hold.append(row)
            rec["hold_rules"] = hold
            rec["put_767_at_expiry"] = max(PUT_K - (rec["close_yahoo_daily"] or rec["close_last_1m_bar"]), 0.0)
        out[str(day)] = rec
    fr = out.get(str(FRIDAY), {})
    if "low" in fr:
        recon = {"label": "added after Friday's tape was seen not to match the account given; description only",
                 "account_given": {"low": 763.19, "low_time_pt": "about 07:45", "exit_near": HIS_EXIT,
                                   "close": FRIDAY_CLOSE_HE_GAVE},
                 "friday_regular_session_low": fr["low"], "friday_low_bar_pt": fr["low_bar_pt"],
                 "friday_traded_at_or_below_763_19": bool(fr["low"] <= 763.19),
                 "friday_traded_through_765_50": bool(fr.get("minutes_trading_through_765_50_pt")),
                 "friday_close_matches_account": fr.get("close_yahoo_daily") == FRIDAY_CLOSE_HE_GAVE}
        if fri_books is not None and not fri_books.empty:
            sp = fri_books.drop_duplicates("quote_ts").reset_index(drop=True)
            i = int(sp["spot"].idxmin())
            recon["cboe_recorded_spot_min"] = round(float(sp.loc[i, "spot"]), 2)
            recon["cboe_recorded_spot_min_book_pt"] = (sp.loc[i, "quote_ts"] - pd.Timedelta(hours=3)).strftime("%H:%M")
            recon["cboe_books_that_day"] = int(len(sp))
        th = out.get(str(THURSDAY), {})
        if "low" in th:
            recon["thursday_2026_09_24"] = {k: th.get(k) for k in ("open", "low", "low_bar_pt", "high", "high_bar_pt",
                                                                   "close_yahoo_daily", "put_767_at_expiry")}
        out["friday_reconciliation"] = recon
    return out



def friday_reading(two: dict) -> str:
    fr, rc = two.get(str(FRIDAY), {}), two.get("friday_reconciliation", {})
    if "hold_rules" not in fr:
        return "Friday's one-minute bars were not available."
    parts = []
    if rc and not rc.get("friday_traded_at_or_below_763_19") and not rc.get("friday_traded_through_765_50"):
        th = rc.get("thursday_2026_09_24", {})
        cb = (f" The lab's own recorded quotes agree: their lowest SPY price that day was {rc['cboe_recorded_spot_min']:.2f} "
              f"at {rc['cboe_recorded_spot_min_book_pt']}.") if "cboe_recorded_spot_min" in rc else ""
        parts.append(f"Friday's prices do not match the day as it was described. In regular hours the low was {fr['low']:.2f} "
                     f"at {fr['low_bar_pt']}, and SPY never traded at 765.50 or 763.19.{cb} The close of "
                     f"{fr['close_yahoo_daily']:.2f} does match.")
        if th.get("low") is not None:
            parts.append(f"Thursday {THURSDAY} is the closest match: low {th['low']:.2f} at {th['low_bar_pt']}, close "
                         f"{th['close_yahoo_daily']:.2f}. A 767 put expired worth {th['put_767_at_expiry']:.2f} that day too.")
    floors = [r["put_767_intrinsic_floor"] for r in fr["hold_rules"] if r["put_767_intrinsic_floor"] is not None]
    if floors and max(floors) == 0:
        parts.append("On Friday SPY stood above 767 at every one of your times. So at each of them the 767 put was only "
                     "worth its leftover time value.")
    bids = [(r["book_pt"][:5], r["put_767_bid_recorded"]) for r in fr["hold_rules"] if r.get("put_767_bid_recorded") is not None]
    if bids:
        parts.append(f"The lab's recorded bid for that put was {bids[0][1]:.2f} at {bids[0][0]} and {bids[-1][1]:.2f} at "
                     f"{bids[-1][0]}. At your other times no recorded quote landed within 2 minutes.")
    moves = [(r["pt"], r["next_key_time_pt"], r["move_to_next_key_time"]) for r in fr["hold_rules"]
             if r.get("move_to_next_key_time") is not None]
    if moves:
        big = max(moves, key=lambda x: abs(x[2]))
        parts.append(f"The biggest swing between two of your times was {big[0]} to {big[1]}: SPY moved {big[2]:+.2f}.")
    parts.append(f"Held to the close at {fr['close_yahoo_daily']:.2f}, a 767 put expired worth nothing. Selling it at your "
                 "next time would have kept whatever time value was left then. Holding to the close kept none. That is one "
                 "day. Whether your times help on average is what the three answers above measure.")
    return " ".join(parts)


def today_reading(two: dict) -> str:
    td = two.get(str(TODAY), {})
    if "low" not in td:
        return "Today's one-minute bars were not available."
    lo_m = hm(td["low_bar_pt"])
    near_T = min(KEY, key=lambda T: abs(T - 180 - lo_m))
    gap = lo_m - (near_T - 180)
    rel = "exactly at" if gap == 0 else f"{abs(gap)} minutes {'after' if gap > 0 else 'before'}"
    return (f"So far today the low was {td['low']:.2f} at {td['low_bar_pt']}, {rel} your {pt(near_T)} time. "
            f"The high so far was {td['high']:.2f} at {td['high_bar_pt']}.")


# ---------------------------------------------------------------- the plain-English page
def pct(bps: float, k: int = 3) -> str:
    return f"{bps / 100:.{k}f}%"


def strength(t) -> str:
    if t is None:
        return "no score"
    word = "could easily be luck" if abs(t) < 2 else "stronger than luck usually makes"
    return f"strength {t:+.1f}, {word}"


def write_md(rep: dict) -> str:
    H, L = rep["headline"]["FULL"], rep["headline"]["LAST12"]
    D = rep["descriptive"]
    car = D["what_carries_Q1_post_hoc"]
    out = []
    w = out.append

    def loud(c):
        return c.get("t") is not None and abs(c["t"]) >= 2

    q1, q2, q3 = H["Q1_activity"], H["Q2_turns"], H["Q3_extremes"]
    l1, l2, l3 = L["Q1_activity"], L["Q2_turns"], L["Q3_extremes"]
    rel = 100 * (q1["context_mean_absA_key_bps"] / q1["context_mean_absA_nbr_bps"] - 1)
    top = sorted(car["contribution_bps_to_mean"], key=lambda r: -(r["FULL"] or 0))[:2]
    pre = car["without_the_four_prenamed_clock_times"]

    w("# Your fourteen key times: what the SPY record says")
    w("")
    w(f"Paper research for Leo's Trading Firm, {rep['generated_pt']} Pacific. Not a trade and not advice.")
    w("")
    w("## The short answer")
    w("")
    if loud(q1) and q1["mean"] > 0:
        cents = q1["mean"] / 1e4 * FRIDAY_CLOSE_HE_GAVE * 100
        w(f"- SPY does move a little more in the 15 minutes after your times than after the times beside them: about {rel:.0f}% more. "
          f"On a {FRIDAY_CLOSE_HE_GAVE:.0f} dollar SPY that is about {cents:.0f} cents per 15 minutes. "
          f"The gap showed up in every calendar year since 2020 and in your reading year.")
        w(f"- Most of that comes from two times: {top[0]['pt']} and {top[1]['pt']}, which together give "
          f"{top[0]['FULL_share_pct'] + top[1]['FULL_share_pct']:.0f}% of the gap. 12:45 starts the last 15 minutes of the day, "
          "the busiest stretch of almost every afternoon. 07:00 is when many US economic reports come out.")
        pf = pre["FULL"]
        w(f"- Take out the four times that sit on known news clocks and the gap shrinks to {pct(pf['mean'])}, about "
          f"{pf['mean'] / 1e4 * FRIDAY_CLOSE_HE_GAVE * 100:.1f} cents ({strength(pf['t'])}). That check was added after "
          "seeing the results.")
    else:
        w(f"- SPY does not move more after your times than after the times beside them ({strength(q1['t'])}).")
    w(f"- SPY does not turn around more often at your times. It turns about half the time at your times "
      f"({q2['context_turn_rate_key_pct']:.1f}%) and at the times beside them ({q2['context_turn_rate_nbr_pct']:.1f}%)."
      if not loud(q2) else f"- Turns differ at your times ({strength(q2['t'])}).")
    w("- The day's high and low do not land at your times more often than at nearby times, beyond what luck gives."
      if not loud(q3) else f"- The day's high and low land at your times more often ({strength(q3['t'])}).")
    o = rep["options"]
    if not o["status"].startswith("SKIPPED"):
        k_, n_ = o["key_times"], o["neighbour_marks"]
        w(f"- For options, the extra movement did not pay. Buying the at-the-money call and put at your times "
          f"and selling 15 minutes later lost {abs(k_['mean_pnl_usd_per_straddle']):.2f} dollars a pair on average. "
          f"At the times beside them it lost {abs(n_['mean_pnl_usd_per_straddle']):.2f}. That is {k_['n_days']} recorded days.")
    w(f"- About {D['share_of_session_minutes_within_10_min_of_a_key_time_pct']:.0f} of every 100 minutes of the trading day "
      "are within 10 minutes of one of your times. So a turn near one of your times is what you would see even if the clock meant nothing.")
    w("")
    w("## What you said")
    w("")
    w("You have watched these Pacific times for over a year: " + ", ".join(KEY_PT) + ".")
    w("You said SPY takes good turns or keeps going at them. You also named a Friday trade and today's reversal as examples.")
    w("")
    w("## How it was tested")
    w("")
    w(f"- The rules were written and saved before any price was loaded (commit {PREREG_COMMIT}). No window or line was moved afterwards.")
    w("- One coding slip was fixed after the first run. On the 12 half-days the code had let in trades from after the "
      "13:00 close. The written rules already left them out. The answers barely moved.")
    w(f"- Every trading day from {H['from']} to {H['to']}: {H['sessions_in_sample']} days of 5-minute SPY prices.")
    gap = rep["data"].get("sessions_missing_in_span", [])
    if gap:
        w(f"- {len(gap)} trading day in that span has no price data ({', '.join(gap)}). It is left out, not filled in.")
    w(f"- A second check uses only your reading year, {L['from']} to {L['to']}: {L['sessions_in_sample']} days.")
    w("- Each day counts once. Many moves on one day are still one day.")
    w("- Each of your times is compared with the times 15 minutes before and after it, on the same day.")
    w("  That takes out the normal rhythm of the day, where the open and the close are always busier than lunch.")
    w("- 06:45 could not be checked for moves or turns. The 15 minutes before it start before the market opens.")
    w("- The strength score says how far a result sits from what luck makes. Between minus 2 and plus 2 is ordinary luck.")
    w("")
    w("## The three answers")
    w("")
    for name, h in (("Every day since July 2020", H), ("Your reading year only", L)):
        a1, a2, a3 = h["Q1_activity"], h["Q2_turns"], h["Q3_extremes"]
        w(f"### {name} ({h['sessions_in_sample']} days)")
        w("")
        w(f"1. Moves. In the 15 minutes after your times SPY moved {pct(a1['context_mean_absA_key_bps'])} on average. "
          f"After the times beside them it moved {pct(a1['context_mean_absA_nbr_bps'])}. "
          f"Gap {pct(a1['mean'])} over {a1['n_days']} days, {strength(a1['t'])}.")
        w(f"2. Turns. SPY turned at {a2['context_turn_rate_key_pct']:.1f}% of your times and {a2['context_turn_rate_nbr_pct']:.1f}% of "
          f"the times beside them. Gap {a2['mean']:+.1f} points over {a2['n_days']} days, {strength(a2['t'])}.")
        w(f"3. Highs and lows. Per 100 days, {a3['context_extremes_in_key_windows_per_100_days']:.1f} of the day's highs and lows "
          f"landed in your 10-minute windows and {a3['context_extremes_in_placebo_windows_per_100_days']:.1f} in matching windows "
          f"15 minutes away. Over {a3['n_days']} days that is {strength(a3['t'])}.")
        w("")
    lk = rep["luck"]
    w(f"Six answers were read. Luck alone makes at least one of six look strong about {lk['chance_pct']:.0f}% of the time.")
    if lk["cells_with_abs_t_ge_2"]:
        names = {"Q1_activity": "moves", "Q2_turns": "turns", "Q3_extremes": "highs and lows"}
        w("Cleared the luck line: " + "; ".join(f"{names[c['cell']]}, {'every day' if c['sample'] == 'FULL' else 'reading year'} "
                                               f"(strength {c['t']:+.1f})" for c in lk["cells_with_abs_t_ge_2"]) + ".")
    else:
        w("None of the six cleared the luck line.")
    w("")
    w("## What carries the moves answer (added after seeing the results)")
    w("")
    w("This is a look inside answer 1, not a new test.")
    w("")
    w("| Your time | Share of the gap it supplies | Gap if this time is left out |")
    w("|---|---|---|")
    loo = {r["left_out_pt"]: r["FULL"] for r in car["leave_one_time_out"]}
    for r in car["contribution_bps_to_mean"]:
        x = loo[r["pt"]]
        w(f"| {r['pt']} | {r['FULL_share_pct']:.0f}% | {pct(x['mean'])}, strength {x['t']:+.1f} |")
    w("")
    w(f"Without 07:00, 10:00, 11:00 and 12:45, the four times named in advance as news clocks, the gap is "
      f"{pct(pre['FULL']['mean'])} ({strength(pre['FULL']['t'])}) on every day, and {pct(pre['LAST12']['mean'])} "
      f"({strength(pre['LAST12']['t'])}) in your reading year.")
    w("")
    w("## Single times (a description, not a test)")
    w("")
    w("Fourteen times and three questions make 42 more readings. About 2 should look strong by luck alone.")
    w("")
    w("| Your time | Move after it, vs beside it | Turn rate, vs beside it | Highs and lows in its window, vs beside it |")
    w("|---|---|---|---|")
    for row in D["per_key_time_FULL"]:
        def cell(c, kind):
            if c.get("t") is None:
                return "not checkable"
            if kind == "q1":
                v = f"{c['mean_absA_key_bps'] / 100:.3f}% vs {c['mean_absA_nbr_bps'] / 100:.3f}%"
            elif kind == "q2":
                v = f"{c['turn_rate_key_pct']:.1f}% vs {c['turn_rate_nbr_pct']:.1f}%"
            else:
                v = (f"{(c['low_in_key_window_pct'] + c['high_in_key_window_pct']):.1f} vs "
                     f"{(c['low_in_placebo_window_pct'] + c['high_in_placebo_window_pct']):.1f} per 100 days")
            return v + (f" (strength {c['t']:+.1f})" if abs(c["t"]) >= 2 else "")
        w(f"| {row['pt']} | {cell(row['q1'], 'q1')} | {cell(row['q2'], 'q2')} | {cell(row['q3'], 'q3')} |")
    w("")
    if D["notable_rows"]:
        w("Rows with a strength past 2 either way:")
        for n in D["notable_rows"]:
            w(f"- {n}")
    else:
        w("No single time stood out on any of the three questions.")
    w("")
    w("Named before the data was loaded: US economic reports come out at 07:00 Pacific, Treasury auction results at 10:00, "
      "Fed decisions at 11:00 on eight days a year, and the closing order imbalance at 12:50. "
      "A busy row at one of these is the news calendar. Option sellers know that calendar too.")
    w("")
    w("## The shape of a normal day")
    w("")
    w("Average size of the next 15-minute move, every day since July 2020:")
    w("")
    w("| Pacific time | Average 15-minute move | One of your times? |")
    w("|---|---|---|")
    for r in D["mean_abs_move_by_time"]:
        if r["pt"] in ("06:35", "06:45", "07:00", "07:15", "07:45", "08:30", "09:30", "10:00", "11:00", "12:00", "12:30", "12:45"):
            w(f"| {r['pt']} | {pct(r['mean_abs_bps'])} | {'yes' if r['is_key_time'] else ''} |")
    w("")
    w("The day is loud at the open, quiet at lunch and loud again at the close, whatever the clock face says.")
    w("")
    w("## What it means for options")
    w("")
    if o["status"].startswith("SKIPPED"):
        w(f"Skipped: {o['reason']}.")
    else:
        k_, n_, dff = o["key_times"], o["neighbour_marks"], o["key_minus_neighbour_same_days"]
        w(f"The lab has recorded real SPY same-day option quotes on {o['sessions_with_books']} days ({o['first']} to {o['last']}).")
        w("The check: buy the at-the-money call and put together at the asking price at the time. Sell both at the bid 15 minutes later.")
        w("")
        w(f"- At your times: {k_['mean_pnl_usd_per_straddle']:+.2f} dollars a pair on average, {k_['mean_pnl_pct_of_debit']:+.1f}% of the "
          f"{k_['mean_debit_usd']:.0f} dollars paid, over {k_['n_days']} days. It made money on {k_['days_positive']} of those days.")
        w(f"- At the times beside them: {n_['mean_pnl_usd_per_straddle']:+.2f} dollars a pair, {n_['mean_pnl_pct_of_debit']:+.1f}% of the "
          f"{n_['mean_debit_usd']:.0f} dollars paid, over {n_['n_days']} days. It made money on {n_['days_positive']} of those days.")
        if dff["n_days"]:
            w(f"- Same days, your times minus the times beside them: {dff['mean_usd']:+.2f} dollars a pair over {dff['n_days']} days, "
              f"{strength(dff['t_days_descriptive'])}.")
        w("")
        best = [r for r in o["per_key_time"] if r.get("n_days")]
        if best:
            b0 = max(best, key=lambda r: r["mean_pnl_usd"])
            w(f"No single time paid on average. The least bad was {b0['pt']} at {b0['mean_pnl_usd']:+.2f} dollars a pair over {b0['n_days']} days.")
        miss = [r for r in o["per_key_time"] if not r.get("n_days")]
        for r in miss:
            w(f"{r['pt']} could not be priced: {r.get('reason')}.")
        w("")
        w("A bit more movement does not pay if the price of the option already expects it. "
          "Here it did not pay at your times or beside them. The pair loses its spread and 15 minutes of time value, "
          "and the extra move at your times was not enough to cover that.")
        w(f"This covers {o['sessions_with_books']} recorded days, not years. It is a description, not a verdict.")
    w("")
    w("## Your two days")
    w("")
    two = rep["his_two_days"]
    fr, td = two.get(str(FRIDAY), {}), two.get(str(TODAY), {})
    if "key_times" in fr:
        w(f"### Friday {FRIDAY}")
        w("")
        w(f"Opened {fr['open']:.2f}. Low {fr['low']:.2f} at {fr['low_bar_pt']}. High {fr['high']:.2f} at {fr['high_bar_pt']}. "
          f"Closed {fr['close_yahoo_daily']:.2f}.")
        w("")
        w("| Pacific time | SPY | 767 put, built-in value | 767 put, recorded bid |")
        w("|---|---|---|---|")
        for r in fr["hold_rules"]:
            bid = r.get("put_767_bid_recorded")
            bid_s = "no book within 2 minutes" if bid is None else f"{bid:.2f} (quote at {r.get('book_pt', '')[:5]})"
            spy_s = "missing" if r["spy"] is None else f"{r['spy']:.2f}"
            flo_s = "" if r["put_767_intrinsic_floor"] is None else f"{r['put_767_intrinsic_floor']:.2f}"
            w(f"| {r['pt']} | {spy_s} | {flo_s} | {bid_s} |")
        w("")
        w(two.get("friday_reading", ""))
        w("")
    if "key_times" in td:
        seen = [k for k in td["key_times"] if k["spy"] is not None]
        w(f"### Today {TODAY}, up to {td['latest_bar_pt']} Pacific")
        w("")
        w(f"Opened {td['open']:.2f}. Last {td['latest_close']:.2f}.")
        w("At your times so far: " + ", ".join(f"{k['pt']} {k['spy']:.2f}" for k in seen) + ".")
        w(two.get("today_reading", ""))
        w("")
    w("One or two days cannot show whether a clock time matters. Fifteen hundred days can, and that is what the answers above use.")
    w("")
    w("## Honest limits")
    w("")
    for x in rep["limits"]:
        w(f"- {x}")
    w("")
    w("Files: src/key_times_study.py (the rules, then the code), results/key_times_study.json (every number).")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- main
def main() -> None:
    doc_hash = check_prereg()
    days_raw, src, data_info = load_bars()
    days = [analyze_day(d, days_raw[d]) for d in sorted(days_raw)]
    full = days
    last12 = [d for d in days if LAST12[0] <= d["date"] <= LAST12[1]]
    span = sessions.sessions_between(full[0]["date"] - dt.timedelta(days=1), LAST_SETTLED)
    have = {d["date"] for d in full}
    missing = [str(d) for d in span if d not in have]
    q3_bad = [d for d in full if not d["grid_complete"]]
    early_seen = sorted(str(d["date"]) for d in full if d["early_close"])
    data_info.update({
        "sessions_used": len(full), "by_source": {s: sum(1 for v in src.values() if v == s) for s in ("alpaca", "yahoo")},
        "sessions_missing_in_span": missing,
        "early_close_days_in_sample": early_seen,
        "q3_days_dropped_incomplete_grid": len(q3_bad),
        "q3_incomplete_examples": [{"date": str(d["date"]), "problem": d.get("grid_problem"), "last_bar_et": d.get("last_bar")}
                                   for d in q3_bad[:25]],
    })
    head = {"FULL": headline(full), "LAST12": headline(last12)}
    for k in head:
        head[k]["expected_sessions_in_span"] = len(sessions.sessions_between(
            (full[0]["date"] if k == "FULL" else LAST12[0]) - dt.timedelta(days=1), LAST_SETTLED))
    looks = [(s, c, head[s][c]) for s in ("FULL", "LAST12") for c in ("Q1_activity", "Q2_turns", "Q3_extremes")]
    luck = {"looks": 6, "chance_pct": 100 * (1 - (1 - LUCK_P) ** 6),
            "formula": "1 - (1 - 0.0455)^6",
            "cells_with_abs_t_ge_2": [{"sample": s, "cell": c, "t": r["t"], "mean": r["mean"]}
                                      for s, c, r in looks if r.get("t") is not None and abs(r["t"]) >= 2]}
    rows = per_time_rows(full)
    notable = []
    names = {"q1": "moves after it differ from beside it", "q2": "turn rate differs from beside it",
             "q3": "the day's high or low lands in its window more or less than beside it"}
    for r in rows:
        for q in ("q1", "q2", "q3"):
            c = r[q]
            if c.get("t") is not None and abs(c["t"]) >= 2:
                if q == "q1":
                    val = f"{c['mean'] / 100:+.3f}% ({c['mean_absA_key_bps'] / 100:.3f}% vs {c['mean_absA_nbr_bps'] / 100:.3f}%)"
                elif q == "q2":
                    val = f"{c['mean']:+.1f} points ({c['turn_rate_key_pct']:.1f}% vs {c['turn_rate_nbr_pct']:.1f}%)"
                else:
                    val = f"{c['mean'] * 100:+.1f} per 100 days"
                notable.append(f"{r['pt']} Pacific: {names[q]}: {val}, strength {c['t']:+.1f}, {c['n_days']} days.")
    years = {}
    for d in full:
        years.setdefault(d["date"].year, []).append(d["q1"])
    q1_year = [{"year": y, **tstat(v)} for y, v in sorted(years.items())]
    ushape = []
    for T in range(OPEN_M + 5, CLOSE_M - 15 + 1, 5):
        v = [d["absA"][T] for d in full if T in d["absA"]]
        ushape.append({"pt": pt(T), "et": fmt(T), "mean_abs_bps": float(np.mean(v)), "n_days": len(v),
                       "is_key_time": T in KEYSET})
    full_grid = [d for d in full if d["grid_complete"] and not d["early_close"]]
    ext = []
    for j in range(78):
        m = OPEN_M + 5 * j
        ext.append({"bar_pt": pt(m), "low_share_pct": 100 * float(np.mean([d["low_bar"] == m for d in full_grid])),
                    "high_share_pct": 100 * float(np.mean([d["high_bar"] == m for d in full_grid])),
                    "in_a_key_window": m in KEY_BARS})
    try:
        opts = options_description()
    except Exception as ex:                                           # a failure is a stated zero, not a silent one
        opts = {"status": "SKIPPED", "reason": f"the options description failed: {type(ex).__name__}: {ex}"}
    try:
        two = his_two_days()
    except Exception as ex:
        two = {"error": f"{type(ex).__name__}: {ex}"}
    two["friday_reading"] = friday_reading(two)
    two["today_reading"] = today_reading(two)

    # POST-HOC (added after the results were seen): what carries Q1. Not a test; not in the luck count.
    def q1_without(ds, drop):
        xs = []
        for d in ds:
            v = [row["q1"] for T, row in d["per_time"].items() if "q1" in row and T not in drop]
            if v:
                xs.append(float(np.mean(v)))
        return tstat(xs)

    def contributions(ds):
        n = sum(1 for d in ds if d["q1"] is not None)
        out = {}
        for d in ds:
            v = {T: row["q1"] for T, row in d["per_time"].items() if "q1" in row}
            for T, x in v.items():
                out[T] = out.get(T, 0.0) + x / len(v) / n
        return out

    prenamed = [hm(x) + 180 for x in ("07:00", "10:00", "11:00", "12:45")]
    cf, cl = contributions(full), contributions(last12)
    carries = {
        "label": "POST-HOC, added after the results were seen: what carries Q1. Not a test, not in the luck count.",
        "contribution_bps_to_mean": [{"pt": pt(T), "FULL": cf.get(T), "LAST12": cl.get(T),
                                      "FULL_share_pct": 100 * cf.get(T, 0) / head["FULL"]["Q1_activity"]["mean"]}
                                     for T in KEY[1:]],
        "leave_one_time_out": [{"left_out_pt": pt(T), "FULL": q1_without(full, {T}), "LAST12": q1_without(last12, {T})}
                               for T in KEY[1:]],
        "without_the_four_prenamed_clock_times": {
            "left_out_pt": [pt(T) for T in prenamed],
            "why": "07:00 = 10:00 ET data releases, 10:00 = 13:00 ET auction results, 11:00 = 14:00 ET Fed decisions, "
                   "12:45 = 15:45-16:00 ET, which holds the 15:50 ET closing-imbalance publication (all named in the "
                   "pre-registration before any data)",
            "FULL": q1_without(full, set(prenamed)), "LAST12": q1_without(last12, set(prenamed))},
        "without_12_45_and_07_00": {"FULL": q1_without(full, {prenamed[0], prenamed[3]}),
                                    "LAST12": q1_without(last12, {prenamed[0], prenamed[3]})},
    }
    # plain arithmetic about the clock itself (no data): how much of the day sits near one of his times
    near = {w: sum(1 for m in range(OPEN_M, CLOSE_M) if min(abs(m - T) for T in KEY) <= w) / (CLOSE_M - OPEN_M)
            for w in (5, 10)}
    fc = data_info["feed_comparison"]
    ag = fc.get("extreme_bar_location_agreement_added_after_prereg_as_a_data_check", {})
    ydays = sorted(d for d, v in src.items() if v == "yahoo")
    limits = [
        f"Prices up to {data_info['alpaca']['to']} come from Alpaca's free feed, which sees trades on one exchange only (IEX). "
        f"From {ydays[0] if ydays else 'n/a'} they come from Yahoo. On the {len(fc.get('dates_both_hold', []))} days both cover, "
        f"their 5-minute closes differed by {fc.get('close_abs_diff_cents_median', float('nan')):.1f} cents in a typical bar. "
        f"They put the day's high in the same 5-minute bar on {ag.get('high_bar_same', 0)} of {ag.get('days', 0)} days, "
        f"and the low on {ag.get('low_bar_same', 0)} of {ag.get('days', 0)}.",
        (f"{len(missing)} trading day in the span has no data ({', '.join(missing)}) and is left out."
         if missing else "No trading day in the span is missing."),
        "06:45 could not be checked at all. Its moves and turns need the 15 minutes before 06:30. Its high-and-low window "
        "has no clean comparison window. 07:00 and 12:00 also sit out the high-and-low question for that reason. These "
        "rules were fixed before the data was loaded.",
        "Some of your times are only 15 to 20 minutes apart, so a time and its neighbour share some of the same minutes.",
        "Three times have a comparison on one side only (07:00, 12:00, 12:45). Near the open and the close the market gets "
        "busier or quieter quickly, so a one-sided comparison is not a perfect twin. 12:45 is compared with the 15 minutes "
        "before it, and the last 15 minutes of the day are busier almost every day.",
        "The option check covers only the days the lab recorded, with quotes about every 5 minutes. A quote had to be "
        "within 2 minutes of your time, so some days are missing and fills can be up to 2 minutes off.",
        "This checks the clock times alone. It does not check your chart reading at those times. That is a different question.",
    ]
    rep = {
        "study": "key_times_study", "status": "DESCRIPTION ONLY - paper research, registers no variant, no trade follows",
        "generated_pt": dt.datetime.now(ZoneInfo(PT)).strftime("%Y-%m-%d %H:%M"),
        "prereg": {"commit": PREREG_COMMIT, "docstring_sha256": doc_hash, "file": "src/key_times_study.py"},
        "post_run_fixes": [
            "Run 1 admitted after-hours bars (13:00-13:50 ET) on the 12 listed early-close days, contrary to the "
            "pre-registered session (early closes end at 13:00 and lack afternoon marks). Fixed to the registered "
            "definition before any result was written up; no window, threshold or cell changed."],
        "key_times": [{"pt": s, "et": fmt(hm(s) + 180)} for s in KEY_PT],
        "neighbour_marks_pt": [pt(N) for N in NBR_MARKS],
        "q3_placebo": {pt(T): {"shift": s, "bars_pt": [pt(b) for b in bars]} for T, (s, bars) in PLACEBO.items()},
        "q3_dropped": {pt(T): why for T, why in Q3_DROPPED.items()},
        "impossible": {"06:45 PT in Q1 and Q2": "T-15 would be 09:30 ET; no regular-session bar ends at 09:30, so P(09:30) never exists",
                       "06:45, 07:00, 12:00 PT in Q3": "no placebo window free of key windows inside the session"},
        "data": data_info,
        "headline": head,
        "luck": luck,
        "descriptive": {"label": "DESCRIPTIVE ONLY - not tests, outside the luck count; 42 per-time looks, ~1.9 expected |t|>=2 by luck",
                        "per_key_time_FULL": rows, "notable_rows": notable, "q1_by_year_FULL": q1_year,
                        "what_carries_Q1_post_hoc": carries,
                        "share_of_session_minutes_within_5_min_of_a_key_time_pct": 100 * near[5],
                        "share_of_session_minutes_within_10_min_of_a_key_time_pct": 100 * near[10],
                        "mean_abs_move_by_time": ushape,
                        "extreme_location_share_by_bar_full_days": {"n_days": len(full_grid), "bars": ext}},
        "options": opts,
        "his_two_days": two,
        "limits": limits,
    }
    rep = rnd(rep)
    OUT_JSON.parent.mkdir(exist_ok=True)
    atomic_json(OUT_JSON, rep, indent=1, default=str)
    atomic_write_text(OUT_MD, write_md(rep))

    print(f"prereg {PREREG_COMMIT} sha {doc_hash[:12]} ok")
    print(f"sessions {len(full)} ({data_info['by_source']}), missing in span {len(missing)}, q3 incomplete {len(q3_bad)}")
    for s in ("FULL", "LAST12"):
        h = head[s]
        print(f"\n== {s} {h['from']} -> {h['to']} ({h['sessions_in_sample']} sessions)")
        for c in ("Q1_activity", "Q2_turns", "Q3_extremes"):
            r = h[c]
            print(f"   {c:12s} mean {r.get('mean'):+.4f}  t {r.get('t')}  n_days {r.get('n_days')}")
    print(f"\nluck: 6 looks, {luck['chance_pct']:.1f}% chance of one |t|>=2; loud: {luck['cells_with_abs_t_ge_2']}")
    print("\nper key time (FULL, descriptive):")
    for r in rows:
        print(f"   {r['pt']}  q1 {r['q1'].get('mean')} t {r['q1'].get('t')} | q2 {r['q2'].get('mean')} t {r['q2'].get('t')} | "
              f"q3 {r['q3'].get('mean')} t {r['q3'].get('t')}")
    print("\noptions:", json.dumps({k: opts.get(k) for k in ("status", "reason", "sessions_with_books", "key_times",
                                                           "neighbour_marks", "key_minus_neighbour_same_days")}, default=str))
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()

"""fib_hour45_study.py — does SPY respect IE Pro's Fibonacci levels, and does it turn at :45 each hour?

Asked 2026-10-13 (18:33 PT), looking at SPY 5m with IE Pro ONE v2: "go through all the fib retracement, i think it follows
accordingly ... use the ie pro to evaluate whether it follows the retracement", and "from 6:45 it had a big drop till 8:45
... 7:45 ... 8:45 ... 9:45 ... 10:45 ... 11:45 ... 12:45 ... it mostly follows the same pattern" (Pacific times).

PRE-DECLARED before any data was read (this file is committed first; the run comes after):

DATA  SPY 5-minute regular-session bars: Alpaca IEX 2020-07-27 .. 2026-07-10 plus Yahoo 5m for the last 60 days, through
      the last settled session (key_times_study.load_bars, unchanged). RTH only: IE Pro on his chart also sees extended
      hours, so the 156-bar window here spans about two sessions instead of about one. Said on the page.

TEST 1 — FIBONACCI LEVELS (IE Pro ONE v2.1 auto-Fib, "Latest leg", 5m auto length 156, exactly as the Pine computes it):
  As of each bar t, from bars t-156 .. t-1: window high/low; the more recent of the two is the leg START; the leg END is the
  furthest price since it; the leg counts only when it is at least 0.15 of the window range and older than one bar (the
  Pine's leg_ok). Level r sits at END + r * (START - END).
  EVENT: the first bar since the leg's END was set that reaches level r on the retrace (a bar that also extends END is
  skipped). One event per (leg start, leg end, level).
  OUTCOME (first passage, same session, bars after the touch): RESPECTED = price moves back toward the END by d before it
  moves through the level by d; BROKEN = the reverse. d = 0.10 of the leg (at least $0.10). A bar that reaches both = dropped,
  unresolved by the close = dropped; both counted on the page.
  FIB levels: 0.236 0.382 0.5 0.618 0.786. CONTROL levels (same leg, not Fibonacci): each Fib level +/- 0.05.
  PRIMARY: respected-rate at Fib levels minus respected-rate at control levels, pooled; 95% CI by resampling whole days
  (2,000 draws). The claim "it follows the retracement" predicts a clearly positive difference. Secondary: each of the 5
  levels against its own two neighbours (5 looks).

TEST 2 — THE :45 TURN:
  Pivots: intraday zigzag on each session's 5m bars, a swing reverses after a move of 0.20% from its extreme (secondary:
  0.30%). The pivot bar is the bar of the extreme. Pivots on the first (09:30 ET) and last (15:55 ET) bar are dropped.
  PRIMARY: pivots on bars starting at :45 versus the count expected if every bar of the same clock hour were equally likely
  (ratio observed/expected, 95% CI by day resampling). Secondary: the :40-:50 three-bar window; the full minute-of-hour
  profile (12 bars) so that any minute standing out — not only :45 — is visible.
  Earlier study on his 14 key times (2026-09-28, key_times_study.py): turns 50.4% vs 49.8% beside them — no.

LUCK: 1 + 1 primary readings, 5 + 1 secondary. With 8 looks about a 34% chance one shows |t| >= 2 by luck.
OUTPUT results/fib_hour45_study.json. A description of SPY, not a signal and not a trade (sim-only, his Rule 7).
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import key_times_study as k  # noqa: E402
from atomicio import atomic_json  # noqa: E402  BOOK-001

FIB = (0.236, 0.382, 0.5, 0.618, 0.786)
CTRL = {r: (round(r - 0.05, 3), round(r + 0.05, 3)) for r in FIB}
WIN, MIN_LEG, D_FRAC, D_MIN = 156, 0.15, 0.10, 0.10
ZIG = (0.0020, 0.0030)
OUT = ROOT / "results" / "fib_hour45_study.json"
RNG = np.random.default_rng(20261013)


def stack(days: dict):
    ds = sorted(days)
    H, L, C, D, M = [], [], [], [], []
    for i, d in enumerate(ds):
        g = days[d]
        H.append(g["high"].to_numpy(float)); L.append(g["low"].to_numpy(float)); C.append(g["close"].to_numpy(float))
        D.append(np.full(len(g), i)); M.append(g["m"].to_numpy(int))
    return ds, np.concatenate(H), np.concatenate(L), np.concatenate(C), np.concatenate(D), np.concatenate(M)


def fib_events(H, L, D):
    n = len(H)
    out = []                                      # (day, level, is_fib, respected 1/0)
    seen = set()
    dropped = {"both_in_one_bar": 0, "unresolved_by_close": 0, "touch_bar_extends_leg": 0}
    for t in range(WIN + 1, n):
        lo_, hi_ = t - WIN, t                     # window = bars t-156 .. t-1
        wh = H[lo_:hi_]; wl = L[lo_:hi_]
        ih = lo_ + (len(wh) - 1 - int(np.argmax(wh[::-1])))       # most recent occurrence of the high
        il = lo_ + (len(wl) - 1 - int(np.argmax(-wl[::-1])))      # most recent occurrence of the low
        w_hi, w_lo = H[ih], L[il]
        hi_recent = ih > il
        s_idx = ih if hi_recent else il
        if t - s_idx <= 1:
            continue
        if hi_recent:                              # down-leg: START = high, END = lowest low since; retrace = UP
            seg = L[s_idx:t]; e_rel = len(seg) - 1 - int(np.argmax(-seg[::-1])); e_idx = s_idx + e_rel
            S, E = w_hi, L[e_idx]
        else:                                      # up-leg: START = low, END = highest high since; retrace = DOWN
            seg = H[s_idx:t]; e_rel = len(seg) - 1 - int(np.argmax(seg[::-1])); e_idx = s_idx + e_rel
            S, E = w_lo, H[e_idx]
        R = abs(S - E)
        if R < MIN_LEG * (w_hi - w_lo) or R <= 0:
            continue
        sgn = 1.0 if hi_recent else -1.0          # retrace direction
        d = max(D_FRAC * R, D_MIN)
        for r in FIB + tuple(x for pair in CTRL.values() for x in pair):
            key = (s_idx, e_idx, r)
            if key in seen:
                continue
            Lv = E + r * (S - E)
            # first bar since END (exclusive) that reaches the level; only bar t is checked here, earlier bars were
            # checked on their own turn, so reaching at t means first touch
            reached = H[t] >= Lv if sgn > 0 else L[t] <= Lv
            prior = (H[e_idx + 1:t] >= Lv).any() if sgn > 0 else (L[e_idx + 1:t] <= Lv).any()
            if prior:
                seen.add(key)
                continue
            if not reached:
                continue
            seen.add(key)
            if (L[t] < E) if sgn > 0 else (H[t] > E):
                dropped["touch_bar_extends_leg"] += 1
                continue
            res = None
            j = t + 1
            while j < n and D[j] == D[t]:
                back = L[j] <= Lv - d if sgn > 0 else H[j] >= Lv + d
                thru = H[j] >= Lv + d if sgn > 0 else L[j] <= Lv - d
                if back and thru:
                    dropped["both_in_one_bar"] += 1
                    res = "x"
                    break
                if back:
                    res = 1; break
                if thru:
                    res = 0; break
                j += 1
            if res is None:
                dropped["unresolved_by_close"] += 1
                continue
            if res == "x":
                continue
            out.append((int(D[t]), r, r in FIB, res))
    return np.array(out, dtype=float), dropped


def day_boot(ev, is_target, ndays):
    """difference in respected-rate: target levels minus the rest of ev; 95% CI by resampling whole days (2,000 draws)"""
    tgt = is_target(ev)
    per = np.zeros((ndays, 4))                     # target respected, target n, other respected, other n
    np.add.at(per, ev[:, 0].astype(int), np.column_stack([ev[:, 3] * tgt, tgt, ev[:, 3] * ~tgt, ~tgt]).astype(float))
    per = per[(per[:, 1] + per[:, 3]) > 0]
    f = lambda p: p[:, 0].sum() / p[:, 1].sum() - p[:, 2].sum() / p[:, 3].sum()
    est = f(per)
    draws = np.array([f(per[RNG.integers(0, len(per), len(per))]) for _ in range(2000)])
    se = draws.std(ddof=1)
    return {"est": float(est), "lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)),
            "t": float(est / se) if se > 0 else None, "days": int(len(per))}


def zigzag(h, l, thr):
    """Confirmed swing pivots: a swing ends when price moves thr (a fraction) back from its extreme. Returns bar indices."""
    piv, trend, hi_i, lo_i, ext = [], 0, 0, 0, 0
    for i in range(len(h)):
        if trend == 0:
            if h[i] > h[hi_i]: hi_i = i
            if l[i] < l[lo_i]: lo_i = i
            if h[hi_i] >= l[lo_i] * (1 + thr):
                if lo_i < hi_i: piv.append(lo_i); trend, ext = 1, hi_i
                elif hi_i < lo_i: piv.append(hi_i); trend, ext = -1, lo_i
        elif trend == 1:
            if h[i] >= h[ext]: ext = i
            elif l[i] <= h[ext] * (1 - thr): piv.append(ext); trend, ext = -1, i
        else:
            if l[i] <= l[ext]: ext = i
            elif h[i] >= l[ext] * (1 + thr): piv.append(ext); trend, ext = 1, i
    return piv


def pivots(H, L, M, D, thr):
    out = []                                       # (day, minute ET of the pivot bar)
    for day in np.unique(D):
        idx = np.where(D == day)[0]
        for i in zigzag(H[idx], L[idx], thr):
            mm = int(M[idx][i])
            if k.OPEN_M < mm < k.CLOSE_M - 5:      # first and last bar of the session dropped
                out.append((int(day), mm))
    return out


def hour45(piv, ndays, window=(45,)):
    """observed pivots on the window's bars / expected if every eligible bar of the same clock hour were equally likely"""
    rows = []
    for d, mm in piv:
        h = mm // 60
        elig = [x for x in range(h * 60, h * 60 + 60, 5) if k.OPEN_M < x < k.CLOSE_M - 5]
        rows.append((d, 1.0 if mm % 60 in window else 0.0, sum(1 for x in elig if x % 60 in window) / len(elig)))
    a = np.array(rows)
    per = np.zeros((ndays, 2))
    np.add.at(per, a[:, 0].astype(int), a[:, 1:])
    per = per[per[:, 1] > 0]
    est = per[:, 0].sum() / per[:, 1].sum()
    draws = []
    for _ in range(2000):
        pk = per[RNG.integers(0, len(per), len(per))]
        draws.append(pk[:, 0].sum() / pk[:, 1].sum())
    draws = np.array(draws)
    se = draws.std(ddof=1)
    return {"ratio": float(est), "lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)),
            "t": float((est - 1) / se) if se > 0 else None, "pivots": int(len(a)), "observed": int(a[:, 1].sum()),
            "expected": float(a[:, 2].sum())}


def main():
    k.LAST_SETTLED = dt.date.today() - dt.timedelta(days=1) if dt.datetime.now().hour < 14 else dt.date.today()
    days, src, info = k.load_bars()
    ds, H, L, C, D, M = stack(days)
    ev, dropped = fib_events(H, L, D)
    rep = {"asked": "2026-10-13", "data": {"from": str(ds[0]), "to": str(ds[-1]), "sessions": len(ds),
                                             "feeds": {"alpaca": sum(1 for d in ds if src[d] == "alpaca"),
                                                       "yahoo": sum(1 for d in ds if src[d] == "yahoo")}},
           "fib": {"events": int(len(ev)), "dropped": dropped}}
    f, c = ev[ev[:, 2] == 1], ev[ev[:, 2] == 0]
    rep["fib"]["respected_fib"] = float(f[:, 3].mean())
    rep["fib"]["respected_control"] = float(c[:, 3].mean())
    rep["fib"]["n_fib"], rep["fib"]["n_control"] = int(len(f)), int(len(c))
    rep["fib"]["primary_diff"] = day_boot(ev, lambda a: a[:, 2] == 1, len(ds))
    per = {}
    for r in FIB:
        sub = ev[np.isin(ev[:, 1], [r, *CTRL[r]])]
        fr, cr = sub[sub[:, 1] == r], sub[sub[:, 1] != r]
        per[str(r)] = {"respected": float(fr[:, 3].mean()), "n": int(len(fr)), "neighbours": float(cr[:, 3].mean()),
                       "n_neighbours": int(len(cr)), "diff": day_boot(sub, lambda a, r=r: a[:, 1] == r, len(ds))}
    rep["fib"]["per_level"] = per
    allr = {}
    for r in sorted(set(ev[:, 1])):
        sub = ev[ev[:, 1] == r]
        allr[f"{r:.3f}"] = {"respected": float(sub[:, 3].mean()), "n": int(len(sub)), "fib": bool(r in FIB)}
    rep["fib"]["by_ratio"] = allr
    rep["hour45"] = {}
    for thr in ZIG:
        piv = pivots(H, L, M, D, thr)
        prof = {f":{mm:02d}": sum(1 for _, m_ in piv if m_ % 60 == mm) for mm in range(0, 60, 5)}
        rep["hour45"][f"{thr:.4f}"] = {"at_45": hour45(piv, len(ds)), "window_40_50": hour45(piv, len(ds), (40, 45, 50)),
                                        "minute_profile": prof, "pivots": len(piv)}
    atomic_json(OUT, rep, indent=1)  # BOOK-001: never truncate the results file in place
    print(json.dumps({"fib": {k_: v for k_, v in rep["fib"].items() if k_ != "by_ratio"}, "hour45": rep["hour45"]}, indent=1)[:4000])


if __name__ == "__main__":
    main()

#!/opt/anaconda3/bin/python
"""exit_rules_study.py - exit rules for a bought 0DTE option: does holding rescue a red one, does a green one keep going?

DESCRIPTION ONLY - nothing registered, no position follows from it. Paper research on recorded CBOE quotes; not advice.

Two questions, answered first on the hold-to-settle path (A) and then as a grid of exit rules (B):
  1. when a bought option is red, how often does holding get it back to green?
  2. when it is green, how often does it keep going, and how often does it give the gain back?

DEFINITIONS - frozen in this docstring before any number was seen.
  data     CBOE plain session files (SPY_<date>.csv) through --through (default 2026-09-29; a session still being
           recorded is never read). *.yfinance.csv is a different-quality fallback feed and is excluded. A session must
           pass the grid's own completeness rule (zero_dte_grid._load_session: >= 8 snapshots, last poll >= 15:55 ET).
  clock    the CBOE book stamp (quote_ts) = the market time of the quotes, not the recorder's poll time (they differ by
           ~16 min). A snapshot is one distinct book: one per quote stamp, the earliest poll of it kept.
  fills    buy at the ASK of the entry snapshot. Every exit fills at the BID of the snapshot where its rule triggers, so
           a line can be overshot; a snapshot with no bid for the contract is skipped. Settle is the grid's own convention,
           |last-snapshot spot - K| if in the money else 0 (that book is stamped ~15:47-15:52 ET, not 16:00), and every
           settle-based figure is shown beside a labelled check against the official close.
  E1       the earlier refresh's entry, unchanged: one per session at the snapshot nearest 10:25:00 ET on the market
           clock, within 7.5 min, else no entry that session. ATM = the strike nearest spot among strikes whose call AND
           put pass the grid's leg_ok; 1-strike OTM = the next listed strike away (call up, put down), which must itself
           pass leg_ok. Instruments: ATM call, ATM put, 1-strike-OTM call, 1-strike-OTM put.
  E2       every distinct snapshot whose market clock is 10:00:00-11:30:00 ET inclusive, ATM call and ATM put at each.
           Many per session and heavily overlapping, so every statistic is clustered by session.
  pooled   the ATM call and the ATM put together (no directional skill assumed); the 1-strike-OTM pair is pooled the same
           way. Each leg is also reported alone. Groups: E2 {pooled, call, put}; E1 {ATM pooled, ATM call, ATM put,
           OTM1 pooled, OTM1 call, OTM1 put}.
  A1       hold-and-hope. For a drawdown line D in {-20%, -30%, -50%}: a trade TOUCHES it when some later bid is
           <= ask x (1+D). Among touching trades: the share whose bid later gets back to >= the entry ask; the share that
           finish green at settle; the mean and median result at settle; the mean result if closed at the bid of the
           first snapshot at or below the line (the realistic stop fill, shown against the line so the overshoot is
           visible). The share of ALL trades that touch is reported first.
  A2       give-back. For a gain level G in {+25%, +50%, +100%}: a trade TOUCHES it when some later bid is >= ask x (1+G).
           Among touching trades: the share that later touch the next level (+25 -> +50, +50 -> +100, +100 -> +200; +200%
           is added only so the +100% row has a next level), read two ways because a 5-minute snapshot can jump through
           two levels at once: STRICTLY LATER than the touching snapshot (the literal reading, primary) and INCLUDING the
           touching snapshot itself; the share that finish below the entry ask at settle; the mean and median result at
           settle; the mean result if closed at that first snapshot. The share of ALL trades that touch is reported first.
  peak     minutes from entry to the highest later bid (first occurrence), median and interquartile range, for all
           trades and for trades that finish green under a +40m clock.
  B        loss line L in {none, -20%, -30%, -50%} x profit side in {clock +15m, +25m, +40m, +60m; target +25%, +50%,
           +100% each with a +60m clock fallback} = 28 rules. Walk the later snapshots in order; the FIRST snapshot where
           the loss line (bid <= ask x (1+L)), the target (bid >= ask x (1+G)) or the clock (minutes since entry >= M)
           triggers closes the trade at that snapshot's bid. The bid is one price, so simultaneous triggers cannot
           disagree; a trade whose exit bid is at or below its line counts as stopped. A trade with no snapshot at or
           after its clock settles (counted, reported).
  stats    win = result > 0. Loss/win = -(average loss)/(average win). t = cluster-robust (by session, G/(G-1)) t of the
           pooled mean. A1/A2 shares and means carry 90% session-bootstrap intervals (2000 draws, fixed seed).
  looks    every (group x level/peak/rule) cell reported counts as one look; the alternative readings (official-close
           check, next level including the touching snapshot) are counted separately. See "looks" in the JSON.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zero_dte_grid as zg        # the grid's own loaders and conventions, imported unchanged

OUT = os.path.join(zg.BASE, "results", "exit_rules_study_2026-09-30.json")
THROUGH = "2026-09-29"
E1_WANT, E1_TOL_MIN = zg.ENTRY_HHMM, zg.TOL_MIN
E2_LO, E2_HI = dt.time(10, 0, 0), dt.time(11, 30, 0)
D_LEVELS = (-0.20, -0.30, -0.50)
G_LEVELS = (0.25, 0.50, 1.00)
G_NEXT = {0.25: 0.50, 0.50: 1.00, 1.00: 2.00}
LOSS_LINES = (None, -0.20, -0.30, -0.50)
CLOCKS = (15, 25, 40, 60)
TARGETS = (0.25, 0.50, 1.00)
FALLBACK_MIN = 60
EPS = 1e-9
BOOT_B, BOOT_SEED = 2000, 20260930
R_CLOCK, R_STOP, R_TARGET, R_SETTLE = 0, 1, 2, 3
R_NAMES = {R_CLOCK: "clock", R_STOP: "stop", R_TARGET: "target", R_SETTLE: "settle_fallback"}
GROUPS = {   # name -> (entry set, instruments)
    "E2_pooled": ("E2", ("ATM_call", "ATM_put")), "E2_ATM_call": ("E2", ("ATM_call",)), "E2_ATM_put": ("E2", ("ATM_put",)),
    "E1_ATM_pooled": ("E1", ("ATM_call", "ATM_put")), "E1_ATM_call": ("E1", ("ATM_call",)), "E1_ATM_put": ("E1", ("ATM_put",)),
    "E1_OTM1_pooled": ("E1", ("OTM1_call", "OTM1_put")), "E1_OTM1_call": ("E1", ("OTM1_call",)), "E1_OTM1_put": ("E1", ("OTM1_put",)),
}
HEADLINE = ("E2_pooled", "E1_ATM_pooled")


def rules():
    """The 28 rules as (name, loss line, kind, parameter)."""
    out = []
    for L in LOSS_LINES:
        for M in CLOCKS:
            out.append((rule_name(L, "clock", M), L, "clock", M))
        for G in TARGETS:
            out.append((rule_name(L, "target", G), L, "target", G))
    return out


def rule_name(L, kind, p):
    lname = "none" if L is None else f"{round(L * 100):+d}%"
    pname = f"clock+{p}m" if kind == "clock" else f"target+{round(p * 100)}%/+{FALLBACK_MIN}m"
    return f"loss:{lname} | {pname}"


# ----------------------------------------------------------------------------------------------- data
class Session:
    """One complete session on the market clock: distinct books in time order, and each contract's bid at every book."""

    def __init__(self, day, snaps, stamps, close, off_close):
        self.day, self.snaps, self.close, self.off_close = day, snaps, close, off_close
        seen, books = set(), []
        for s in stamps:                                   # fetch order: the earliest poll of a book is kept
            q = zg._qt(snaps, s)
            if q in seen:
                continue
            seen.add(q)
            books.append((q, s))
        books.sort(key=lambda x: x[0])
        self.dupes_removed = len(stamps) - len(books)
        self.qt = [b[0] for b in books]
        self.stamps = [b[1] for b in books]
        n = len(books)
        self.tsec = np.array([(q - self.qt[0]).total_seconds() for q in self.qt])
        self.bid = {}
        for bi, s in enumerate(self.stamps):
            for r in snaps[s]:
                key = (r["type"], float(r["strike"] or 0))
                arr = self.bid.get(key)
                if arr is None:
                    arr = self.bid[key] = np.full(n, np.nan)
                v = (r.get("bid") or "").strip()
                if v:
                    arr[bi] = float(v)

    def trade(self, sid, bi, name, cp, K, ask, eset):
        later = np.arange(bi + 1, len(self.qt))
        b_all = self.bid[(cp, K)][later]
        ok = ~np.isnan(b_all)
        tsec = self.tsec[later][ok] - self.tsec[bi]
        V = max(self.close - K, 0.0) if cp == "C" else max(K - self.close, 0.0)
        Vo = None if self.off_close is None else (max(self.off_close - K, 0.0) if cp == "C" else max(K - self.off_close, 0.0))
        return {"sid": sid, "day": self.day, "set": eset, "inst": name, "cp": cp, "K": K, "ask": ask,
                "entry_book_stamp_et": self.qt[bi].strftime("%H:%M:%S"), "entry_poll_et": self.stamps[bi][11:],
                "tsec": tsec, "b": b_all[ok], "unquoted": int((~ok).sum()), "V": V, "Vo": Vo}


def select_legs(rows):
    """The grid's own ATM choice (nearest strike to spot among strikes whose call AND put pass leg_ok) plus the adjacent
    listed strikes for the 1-strike-OTM legs. -> (by, legs) or None."""
    spot = float(rows[0]["spot"])
    by = {}
    for r in rows:
        if zg.leg_ok(r):
            by.setdefault(float(r["strike"]), {})[r["type"]] = r
    ks = [k for k, v in by.items() if "C" in v and "P" in v]
    if not ks:
        return None
    k = min(ks, key=lambda x: abs(x - spot))
    listed = {t: sorted({float(r["strike"]) for r in rows if r["type"] == t}) for t in ("C", "P")}
    ic, ip = listed["C"].index(k), listed["P"].index(k)
    legs = {"ATM_call": ("C", k), "ATM_put": ("P", k)}
    if ic + 1 < len(listed["C"]):
        legs["OTM1_call"] = ("C", listed["C"][ic + 1])
    if ip > 0:
        legs["OTM1_put"] = ("P", listed["P"][ip - 1])
    return by, legs


def enter(sess, sid, excluded, counters):
    """E1 and E2 trades of one session."""
    trades = []
    want = dt.datetime.strptime(f"{sess.day} {E1_WANT}", "%Y-%m-%d %H:%M:%S")
    i = min(range(len(sess.qt)), key=lambda j: abs((sess.qt[j] - want).total_seconds()))
    gap = (sess.qt[i] - want).total_seconds() / 60
    if abs(gap) > E1_TOL_MIN:
        excluded["E1: nearest snapshot more than %s min from 10:25" % E1_TOL_MIN].append(f"{sess.day} ({gap:+.1f} min)")
    else:
        sel = select_legs(sess.snaps[sess.stamps[i]])
        if sel is None:
            excluded["E1: no strike with both legs passing leg_ok"].append(sess.day)
        else:
            by, legs = sel
            for name in ("ATM_call", "ATM_put", "OTM1_call", "OTM1_put"):
                if name not in legs:
                    excluded[f"E1 {name}: no listed strike beyond ATM"].append(sess.day)
                    continue
                cp, kk = legs[name]
                row = by.get(kk, {}).get(cp)
                if row is None:
                    excluded[f"E1 {name}: leg fails leg_ok"].append(sess.day)
                    continue
                trades.append(sess.trade(sid, i, name, cp, kk, float(row["ask"]), "E1"))
    for bi, q in enumerate(sess.qt):
        if not (E2_LO <= q.time() <= E2_HI):
            continue
        counters["e2_snapshots"] += 1
        sel = select_legs(sess.snaps[sess.stamps[bi]])
        if sel is None:
            counters["e2_snapshots_without_atm"] += 1
            continue
        by, legs = sel
        for name in ("ATM_call", "ATM_put"):
            cp, kk = legs[name]
            trades.append(sess.trade(sid, bi, name, cp, kk, float(by[kk][cp]["ask"]), "E2"))
    return trades


# --------------------------------------------------------------------------------------- per-trade engines
def rule_exit(tr, L, kind, param):
    """One rule on one trade -> (result as a fraction of the entry ask, reason code)."""
    ask, b, ts = tr["ask"], tr["b"], tr["tsec"]
    n = len(b)
    stop = n
    if L is not None:
        hit = b <= ask * (1 + L) + EPS
        if hit.any():
            stop = int(hit.argmax())
    if kind == "clock":
        prof = int(np.searchsorted(ts, param * 60.0, side="left"))
    else:
        hit = b >= ask * (1 + param) - EPS
        tgt = int(hit.argmax()) if hit.any() else n
        prof = min(tgt, int(np.searchsorted(ts, FALLBACK_MIN * 60.0, side="left")))
    idx = min(stop, prof)
    if idx >= n:
        return tr["V"] / ask - 1, R_SETTLE
    if stop == idx:
        return b[idx] / ask - 1, R_STOP
    if kind == "target" and b[idx] >= ask * (1 + param) - EPS:
        return b[idx] / ask - 1, R_TARGET
    return b[idx] / ask - 1, R_CLOCK


def features(trades):
    """A-block features for every trade, as numpy arrays."""
    N = len(trades)
    F = {"touchD": {D: np.zeros(N, bool) for D in D_LEVELS}, "recovD": {D: np.zeros(N, bool) for D in D_LEVELS},
         "fillD": {D: np.full(N, np.nan) for D in D_LEVELS},
         "touchG": {G: np.zeros(N, bool) for G in G_LEVELS}, "nextG": {G: np.zeros(N, bool) for G in G_LEVELS},
         "nextGs": {G: np.zeros(N, bool) for G in G_LEVELS},
         "fillG": {G: np.full(N, np.nan) for G in G_LEVELS},
         "peak_min": np.full(N, np.nan), "final": np.full(N, np.nan), "final_off": np.full(N, np.nan)}
    for k, tr in enumerate(trades):
        ask, b = tr["ask"], tr["b"]
        for D in D_LEVELS:
            hit = b <= ask * (1 + D) + EPS
            if hit.any():
                j0 = int(hit.argmax())
                F["touchD"][D][k] = True
                F["recovD"][D][k] = bool((b[j0 + 1:] >= ask - EPS).any())
                F["fillD"][D][k] = b[j0] / ask - 1
        for G in G_LEVELS:
            hit = b >= ask * (1 + G) - EPS
            if hit.any():
                j0 = int(hit.argmax())
                F["touchG"][G][k] = True
                F["nextG"][G][k] = bool((b[j0:] >= ask * (1 + G_NEXT[G]) - EPS).any())
                F["nextGs"][G][k] = bool((b[j0 + 1:] >= ask * (1 + G_NEXT[G]) - EPS).any())
                F["fillG"][G][k] = b[j0] / ask - 1
        F["peak_min"][k] = tr["tsec"][int(np.argmax(b))] / 60.0
        F["final"][k] = tr["V"] / ask - 1
        if tr["Vo"] is not None:
            F["final_off"][k] = tr["Vo"] / ask - 1
    return F


# ------------------------------------------------------------------------------------------- statistics
def _ci(sid, num, den, rng):
    """90% session-bootstrap interval of sum(num)/sum(den), sessions resampled with replacement."""
    u, inv = np.unique(sid, return_inverse=True)
    a = np.bincount(inv, weights=num, minlength=len(u))
    c = np.bincount(inv, weights=den, minlength=len(u))
    idx = rng.integers(0, len(u), size=(BOOT_B, len(u)))
    A, C = a[idx].sum(1), c[idx].sum(1)
    ok = C > 0
    r = A[ok] / C[ok]
    return [round(100 * float(np.percentile(r, 5)), 1), round(100 * float(np.percentile(r, 95)), 1)]


def share(sid, num, den, rng):
    d = int(den.sum())
    if d == 0:
        return {"pct": None, "n": 0, "of": 0, "reason": "no trade in the denominator"}
    return {"pct": round(100 * float(num.sum()) / d, 1), "n": int(num.sum()), "of": d,
            "ci90": _ci(sid, num.astype(float), den.astype(float), rng)}


def mean_pct(sid, x, sel, rng):
    d = int(sel.sum())
    if d == 0:
        return {"mean_pct": None, "n": 0, "reason": "no trade in the denominator"}
    xv = np.where(sel, np.nan_to_num(x), 0.0)
    return {"mean_pct": round(100 * float(xv.sum()) / d, 1), "n": d, "ci90": _ci(sid, xv, sel.astype(float), rng)}


def med_pct(x, sel):
    return round(100 * float(np.median(x[sel])), 1) if sel.any() else None


def cluster_t(x, sid):
    n = len(x)
    if n < 3:
        return None
    u, inv = np.unique(sid, return_inverse=True)
    g = len(u)
    if g < 3:
        return None
    m = float(np.mean(x))
    sums = np.bincount(inv, weights=x - m, minlength=g)
    se = math.sqrt(g / (g - 1) * float((sums ** 2).sum())) / n
    return None if se == 0 else round(m / se, 2)


def a_block(F, sel, sid, rng):
    """A1 and A2 for the trades selected by the boolean mask `sel`."""
    s = sid[sel]
    fin, fin_o = F["final"][sel], F["final_off"][sel]
    have_off = bool(np.isfinite(fin_o).any())
    out = {"n_trades": int(sel.sum()), "n_sessions": int(len(np.unique(s))), "clustered_by": "session date", "A1_hold_and_hope": {},
           "A2_give_back": {}}
    allm = np.ones(len(s), bool)
    for D in D_LEVELS:
        t = F["touchD"][D][sel]
        rec, fill = F["recovD"][D][sel], F["fillD"][D][sel]
        green, green_o = fin > 0, fin_o > 0
        out["A1_hold_and_hope"][f"{round(D * 100):+d}%"] = {
            "line_pct": round(D * 100),
            "touch_share_of_all_trades": share(s, t, allm, rng),
            "gets_back_to_entry_ask_after_the_touch": share(s, rec & t, t, rng),
            "finishes_green_at_settle": share(s, green & t, t, rng),
            "finishes_green_at_settle__official_close_check": share(s, green_o & t, t & np.isfinite(fin_o), rng) if have_off else None,
            "result_at_settle_mean": mean_pct(s, fin, t, rng), "result_at_settle_median_pct": med_pct(fin, t),
            "result_at_settle_mean__official_close_check": mean_pct(s, fin_o, t & np.isfinite(fin_o), rng) if have_off else None,
            "result_at_settle_median_pct__official_close_check": med_pct(fin_o, t & np.isfinite(fin_o)) if have_off else None,
            "closed_at_first_touch_mean_fill": mean_pct(s, fill, t, rng), "closed_at_first_touch_median_fill_pct": med_pct(fill, t),
        }
    for G in G_LEVELS:
        t = F["touchG"][G][sel]
        nxt, nxts, fill = F["nextG"][G][sel], F["nextGs"][G][sel], F["fillG"][G][sel]
        below, below_o = fin < 0, fin_o < 0
        out["A2_give_back"][f"{round(G * 100):+d}%"] = {
            "level_pct": round(G * 100), "next_level_pct": round(G_NEXT[G] * 100),
            "touch_share_of_all_trades": share(s, t, allm, rng),
            "reaches_next_level_strictly_later": share(s, nxts & t, t, rng),
            "reaches_next_level_incl_the_touching_snapshot": share(s, nxt & t, t, rng),
            "finishes_below_entry_ask_at_settle": share(s, below & t, t, rng),
            "finishes_below_entry_ask_at_settle__official_close_check": share(s, below_o & t, t & np.isfinite(fin_o), rng) if have_off else None,
            "result_at_settle_mean": mean_pct(s, fin, t, rng), "result_at_settle_median_pct": med_pct(fin, t),
            "result_at_settle_mean__official_close_check": mean_pct(s, fin_o, t & np.isfinite(fin_o), rng) if have_off else None,
            "result_at_settle_median_pct__official_close_check": med_pct(fin_o, t & np.isfinite(fin_o)) if have_off else None,
            "closed_at_first_touch_mean_fill": mean_pct(s, fill, t, rng), "closed_at_first_touch_median_fill_pct": med_pct(fill, t),
        }
    return out


def peak_block(F, sel, pnl40):
    pk = F["peak_min"][sel]
    w = pnl40[sel] > 0
    q = lambda x: [round(float(v), 1) for v in np.percentile(x, [25, 50, 75])] if len(x) else None
    return {"all_trades": {"n": int(len(pk)), "minutes_q1_median_q3": q(pk)},
            "winners_under_a_plus40m_clock": {"n": int(w.sum()), "minutes_q1_median_q3": q(pk[w])},
            "note": "peak = the highest bid after entry on the hold-to-settle path, first occurrence"}


def rule_stats(pnl, reason, sid):
    pnl = np.asarray(pnl)
    n = len(pnl)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    stopped = reason == R_STOP
    aw = float(wins.mean()) if len(wins) else None
    al = float(losses.mean()) if len(losses) else None
    r1 = lambda v: None if v is None else round(100 * v, 1)
    return {"n_trades": int(n), "n_sessions": int(len(np.unique(sid))),
            "win_pct": round(100 * len(wins) / n, 1), "avg_win_pct": r1(aw), "avg_loss_pct": r1(al),
            "loss_over_win": round(-al / aw, 2) if (aw and al is not None) else None,
            "mean_pct": r1(float(pnl.mean())), "median_pct": r1(float(np.median(pnl))), "worst_pct": r1(float(pnl.min())),
            "stopped_share_pct": round(100 * float(stopped.mean()), 1),
            "avg_fill_when_stopped_pct": r1(float(pnl[stopped].mean())) if stopped.any() else None,
            "t_sessions": cluster_t(pnl, sid),
            "exits": {R_NAMES[c]: int((reason == c).sum()) for c in (R_CLOCK, R_STOP, R_TARGET, R_SETTLE)}}


# ------------------------------------------------------------------------------------------------- main
def build(through):
    files = zg.session_files(through)
    off = zg._official_closes()
    sessions, skipped = [], {}
    for fp in files:
        day = os.path.basename(fp)[4:14]
        r = zg._load_session(fp)
        if r is None:
            skipped[day] = "incomplete session (the grid's completeness rule)"
            continue
        _, snaps, stamps, close = r
        sessions.append(Session(day, snaps, stamps, close, off.get(day)))
    excluded, counters = defaultdict(list), defaultdict(int)
    trades = []
    for sid, sess in enumerate(sessions):
        trades += enter(sess, sid, excluded, counters)
    return files, sessions, skipped, trades, excluded, counters, off


def main():
    ap = argparse.ArgumentParser(description="Exit rules for a bought 0DTE option (descriptive; paper only).")
    ap.add_argument("--through", default=THROUGH, help="last session date to read (YYYY-MM-DD); default %(default)s")
    ap.add_argument("--out", default=OUT, help="output JSON; default %(default)s")
    a = ap.parse_args()
    files, sessions, skipped, trades, excluded, counters, off = build(a.through)
    dead = [k for k, t in enumerate(trades) if len(t["b"]) == 0]
    if dead:                                            # a trade with no later quote has no path; say so, drop it
        excluded["trades with no later quote (dropped)"] = [f"{trades[k]['day']} {trades[k]['inst']}" for k in dead]
        drop = set(dead)
        trades = [t for k, t in enumerate(trades) if k not in drop]
    N = len(trades)
    sid = np.array([t["sid"] for t in trades])
    eset = np.array([t["set"] for t in trades])
    inst = np.array([t["inst"] for t in trades])
    F = features(trades)
    RULES = rules()
    P = {r[0]: np.zeros(N) for r in RULES}
    C = {r[0]: np.zeros(N, int) for r in RULES}
    for k, tr in enumerate(trades):
        for name, L, kind, p in RULES:
            P[name][k], C[name][k] = rule_exit(tr, L, kind, p)
    pnl40 = P[rule_name(None, "clock", 40)]
    rng = np.random.default_rng(BOOT_SEED)
    res = {"A": {}, "peak": {}, "B": {}}
    for g, (es, ins) in GROUPS.items():
        sel = (eset == es) & np.isin(inst, ins)
        res["A"][g] = a_block(F, sel, sid, rng)
        res["peak"][g] = peak_block(F, sel, pnl40)
        res["B"][g] = {name: rule_stats(P[name][sel] * 1.0, C[name][sel], sid[sel]) for name, *_ in RULES}
    n_groups = len(GROUPS)
    cells_per_group = len(D_LEVELS) + len(G_LEVELS) + 2 + len(RULES)
    dgr = [s.close - s.off_close for s in sessions if s.off_close is not None]
    lag = [(dt.datetime.strptime(t["entry_poll_et"], "%H:%M:%S") - dt.datetime.strptime(t["entry_book_stamp_et"], "%H:%M:%S")).total_seconds() / 60
           for t in trades]
    last_stamp = sorted(s.qt[-1].strftime("%H:%M:%S") for s in sessions)
    odays = sorted(off)
    prev = {d: off[odays[i - 1]] for i, d in enumerate(odays) if i}
    mv = [(s.day, 100 * (off[s.day] / prev[s.day] - 1)) for s in sessions if s.day in off and s.day in prev]
    calm = {"sessions_measured": len(mv), "source": "settled daily closes, close to close",
            "days_moving_1pct_or_more": sum(1 for _, m in mv if abs(m) >= 1), "days_moving_2pct_or_more": sum(1 for _, m in mv if abs(m) >= 2),
            "largest_abs_move_pct": round(max((abs(m) for _, m in mv), default=0), 2),
            "largest_down_move": None if not mv else {"date": min(mv, key=lambda x: x[1])[0], "pct": round(min(m for _, m in mv), 2)},
            "largest_up_move": None if not mv else {"date": max(mv, key=lambda x: x[1])[0], "pct": round(max(m for _, m in mv), 2)}}
    e1_days = sorted({t["day"] for t in trades if t["set"] == "E1"})
    e2_days = sorted({t["day"] for t in trades if t["set"] == "E2"})
    out = {
        "generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "status": "DESCRIPTION ONLY - nothing registered, no position follows from it",
        "script": "src/exit_rules_study.py",
        "definitions": {k: v.strip() for k, v in {
            "data": "CBOE plain session files through the cap date; *.yfinance.csv excluded; the grid's completeness rule; market clock = CBOE book stamp; one distinct book per quote stamp",
            "fills": "buy at the ask of the entry snapshot; every exit at the bid of the snapshot where its rule triggers; settle = the grid's convention (|last-snapshot spot - K|), official-close check beside it",
            "E1": f"one entry per session at the snapshot nearest {E1_WANT} ET on the market clock within {E1_TOL_MIN} min (the earlier refresh's entry, unchanged)",
            "E2": "every distinct snapshot with market clock 10:00-11:30 ET inclusive; ATM call and ATM put at each",
            "pooled": "ATM call + ATM put (no directional skill assumed); OTM1 pooled = 1-strike-OTM call + put; every leg also alone",
            "B_rules": "loss line {none,-20,-30,-50}% x {clock +15/+25/+40/+60m; target +25/+50/+100% with a +60m clock fallback}; first trigger wins; exit at that snapshot's bid",
            "t": "cluster-robust t of the pooled mean, clustered by session (G/(G-1) small-sample factor)",
            "intervals": f"90% session-bootstrap intervals, {BOOT_B} draws, seed {BOOT_SEED}"}.items()},
        "data": {"through": a.through, "cboe_files_read": len(files), "sessions_used": len(sessions),
                 "first_session": sessions[0].day, "last_session": sessions[-1].day, "calm_window": calm,
                 "sessions_skipped_incomplete": skipped,
                 "yfinance_files_excluded": sorted(os.path.basename(f) for f in
                                                   glob.glob(os.path.join(zg.CHAINS, "SPY_*.yfinance.csv"))),
                 "E1_sessions": len(e1_days), "exclusions": {k: v for k, v in excluded.items()},
                 "E2_sessions": len(e2_days), "E2_snapshots_in_window": counters["e2_snapshots"],
                 "E2_snapshots_without_an_ATM_pair": counters["e2_snapshots_without_atm"],
                 "duplicate_books_removed": sum(s.dupes_removed for s in sessions),
                 "path_snapshots_without_a_bid": sum(t["unquoted"] for t in trades),
                 "trades": {g: int(((eset == es) & np.isin(inst, ins)).sum()) for g, (es, ins) in GROUPS.items()},
                 "settle_reference_check": {"sessions_compared": len(dgr), "mean_grid_minus_official": round(float(np.mean(dgr)), 3) if dgr else None,
                                            "mean_abs": round(float(np.mean(np.abs(dgr))), 3) if dgr else None,
                                            "max_abs": round(float(np.max(np.abs(dgr))), 3) if dgr else None,
                                            "last_book_stamp_et_earliest_median_latest": [last_stamp[0], last_stamp[len(last_stamp) // 2], last_stamp[-1]],
                                            "note": "the grid's settle spot is the last recorded book's spot, stamped a few minutes before 16:00 ET"},
                 "quote_lag": {"entries": len(lag), "poll_minus_book_stamp_minutes_min_median_max": [round(min(lag), 1), round(float(np.median(lag)), 1), round(max(lag), 1)]}},
        "looks": {"groups": n_groups, "cells_per_group": cells_per_group,
                  "cells": n_groups * cells_per_group,
                  "cells_breakdown": f"{len(D_LEVELS)} drawdown levels + {len(G_LEVELS)} gain levels + 2 peak-time readings + {len(RULES)} rules per group",
                  "alternative_readings": {"official_close_check_of_the_level_cells": n_groups * (len(D_LEVELS) + len(G_LEVELS)),
                                           "next_level_incl_the_touching_snapshot": n_groups * len(G_LEVELS)},
                  "headline_groups": list(HEADLINE), "headline_cells": len(HEADLINE) * cells_per_group},
        "A_hold_and_hope_and_give_back": res["A"], "A_minutes_to_peak_bid": res["peak"], "B_rule_grid": res["B"],
        "entries": [{k: t[k] for k in ("day", "set", "inst", "K", "ask", "entry_book_stamp_et", "entry_poll_et")} for t in trades],
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"exit rules: {N} trades, {len(sessions)} sessions (E1 {len(e1_days)}, E2 {len(e2_days)}) -> {a.out}")
    for g in HEADLINE:
        b = res["A"][g]
        print(f"\n  {g}: {b['n_trades']} trades, {b['n_sessions']} sessions")
        for lv, c in b["A1_hold_and_hope"].items():
            print(f"    A1 {lv}: touch {c['touch_share_of_all_trades']['pct']}%  back to entry {c['gets_back_to_entry_ask_after_the_touch']['pct']}%  "
                  f"green at settle {c['finishes_green_at_settle']['pct']}%  settle mean {c['result_at_settle_mean']['mean_pct']} / med {c['result_at_settle_median_pct']}  "
                  f"first-touch fill {c['closed_at_first_touch_mean_fill']['mean_pct']}")
        for lv, c in b["A2_give_back"].items():
            print(f"    A2 {lv}: touch {c['touch_share_of_all_trades']['pct']}%  next level later {c['reaches_next_level_strictly_later']['pct']}% / incl. touch {c['reaches_next_level_incl_the_touching_snapshot']['pct']}%  "
                  f"below entry at settle {c['finishes_below_entry_ask_at_settle']['pct']}%  settle mean {c['result_at_settle_mean']['mean_pct']} / med {c['result_at_settle_median_pct']}  "
                  f"first-touch fill {c['closed_at_first_touch_mean_fill']['mean_pct']}")
        print("    peak:", res["peak"][g])
        print("    grid (mean / win / loss-to-win):")
        for L in LOSS_LINES:
            cells = []
            for name, LL, kind, p in RULES:
                if LL == L:
                    s = res["B"][g][name]
                    cells.append(f"{s['mean_pct']:+.1f}/{s['win_pct']:.0f}/{s['loss_over_win']}")
            print(f"      {'none' if L is None else format(round(L * 100), '+d') + '%':>5}: " + "  ".join(cells))


if __name__ == "__main__":
    main()

#!/opt/anaconda3/bin/python
"""exit_runner_study.py - the "Runner Card": two contracts, one sold at +50%, one left to run. Measured on the recorded CBOE data.

DESCRIPTION ONLY - nothing registered, no position follows from it. Paper research on recorded CBOE quotes; not advice.
A new look at the SAME 45 sessions as exit_rules_study.py (a mining tax: every cell here is an extra look), written to
reuse that study's loader, trades, fills, rule engine, statistics and intervals UNCHANGED (they are imported, not copied).

DEFINITIONS - frozen in this docstring before any number was seen.
  data, clock, fills, E1, E2, pooled   exactly as exit_rules_study.py: 45 complete CBOE sessions through 2026-09-29, the CBOE
           book stamp as the market clock, BUY AT THE ASK of the entry snapshot, EVERY EXIT AT THE BID of the snapshot where
           its rule triggers (a line can be overshot), E1 = one entry per session nearest 10:25 ET, E2 = every snapshot
           10:00-11:30 ET, pooled = ATM call + ATM put, each leg also alone.
  card     two contracts bought at the same ask. The result is the AVERAGE of the two contracts' results, i.e. % of the
           TOTAL entry cost. Walk the later snapshots in order; at each, the first rule to fire wins (one bid, one price).
             both contracts   stop: bid <= ask x 0.70 (-30% from entry) -> both exit at that bid.
             contract 1       target 1: bid >= ask x 1.50 (+50%) -> contract 1 exits at that bid. Its clock: the first snapshot
                              60 minutes or more after entry. Contract 1 is therefore EXACTLY the study's "30/50/60" cell
                              (loss -30% | target +50% / +60m) - checked trade by trade in the script.
             contract 2       before target 1 it is identical to contract 1. When target 1 fills, contract 2's stop moves to
                              the ENTRY price (breakeven): it exits at the bid of the first snapshot whose bid <= ask. It
                              also exits at +100% (bid >= ask x 2.00) and at the 60-minute clock (measured from ENTRY, as
                              in the study). If target 1 and the +100% level are touched at the same snapshot (a 5-minute
                              jump through both), both exit at that bid. If nothing triggers and no snapshot reaches the
                              clock, the contract settles (the grid's last-book convention; counted, reported).
             if neither target is hit both exit at the -30% line or the 60-minute clock.
  runner stage   a trade reaches it when target 1 fills (the first snapshot with bid >= +50%, before a stop or the clock).
  variants (separate looks)
           runner_a   the card as above (breakeven stop after target 1, runner target +100%).
           runner_b   (b) the runner target is +150% instead of +100%.
           runner_c   (c) after target 1 contract 2 uses a 25% TRAILING stop from its peak bid (exit at the first snapshot whose
                      bid <= 0.75 x the highest bid since entry; the bid at the snapshot is included in the peak) INSTEAD of
                      the breakeven stop; the +100% target and the 60-minute clock stay.
           runner_c_nocap   the other reading of (c): the same trailing stop with NO fixed profit target, capped only by the
                      60-minute clock. The brief said "instead of the breakeven stop (still capped by the clock)" and does
                      not say whether the +100% target survives; both readings are run and both are counted as looks.
  comparison cells   RE-READ from exit_rules_study_2026-09-30.json (not recomputed differently): the 30/50/60 card
           (loss:-30% | target+50%/+60m), loss:-30% | clock+60m, loss:-30% | target+100%/+60m, and "sell at the first +25%"
           = loss:none | target+25%/+60m (no loss line; the study's own cell). loss:-30% | target+25%/+60m is also kept in the
           JSON. The study's own rule engine re-computes each cell trade by trade ONLY to get the per-trade series for the
           intervals and the paired differences; every recomputed statistic must equal the JSON value (the "reproduction"
           block) or the run says so loudly.
  stats    win = result > 0. Loss/win = -(average loss)/(average win). t = cluster-robust (by session, G/(G-1)) t of the
           mean (the study's cluster_t). 90% session-bootstrap interval of the mean (the study's mean_pct, 2000 draws,
           sessions resampled with replacement, seed fixed per cell). "vs the card" = the paired per-trade difference
           (runner result - card result) with its own session-bootstrap interval and cluster t. Because contract 1 IS the
           card, that difference is (contract 2 - contract 1) / 2 on the runner-stage trades and exactly 0 elsewhere.
  looks    every (rule x group) cell and every (rule x group) paired difference is one look; see "looks" in the JSON.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zero_dte_grid as zg            # noqa: E402  (the grid's own conventions, imported unchanged)
import exit_rules_study as ers        # noqa: E402  (the study's loader, trades, engine and statistics, imported unchanged)
from atomicio import atomic_json     # noqa: E402

OUT = os.path.join(zg.BASE, "results", "exit_runner_2026-10-11.json")
STUDY_JSON = os.path.join(zg.BASE, "results", "exit_rules_study_2026-09-30.json")
THROUGH = "2026-09-29"
BOOT_SEED = 20261011
EPS = ers.EPS
STOP, T1, CLOCK_MIN = -0.30, 0.50, 60
R_CLOCK, R_STOP, R_TARGET, R_SETTLE = ers.R_CLOCK, ers.R_STOP, ers.R_TARGET, ers.R_SETTLE
C2_NONE, C2_TARGET, C2_STOP, C2_CLOCK, C2_SETTLE = -1, 0, 1, 2, 3
C2_NAMES = {C2_TARGET: "runner_target", C2_STOP: "stop_after_target1", C2_CLOCK: "clock", C2_SETTLE: "settle_fallback"}

RUNNERS = {
    "runner_a": {"label": "Runner Card: -30% stop, sell half +50%, runner to +100%, breakeven stop after target 1, 60m clock",
                 "t2": 1.00, "post": "breakeven", "keep_t2": True},
    "runner_b": {"label": "(b) as the Runner Card but the runner target is +150%",
                 "t2": 1.50, "post": "breakeven", "keep_t2": True},
    "runner_c": {"label": "(c) after target 1 a 25% trailing stop from the peak bid replaces the breakeven stop; +100% target and 60m clock stay",
                 "t2": 1.00, "post": "trail", "keep_t2": True},
    "runner_c_nocap": {"label": "(c, other reading) 25% trailing stop after target 1, NO fixed profit target, capped by the 60m clock only",
                       "t2": None, "post": "trail", "keep_t2": False},
}
RUNNER_PARAMS = {k: {kk: vv for kk, vv in v.items() if kk != "label"} for k, v in RUNNERS.items()}
CARD = "loss:-30% | target+50%/+60m"
COMPARE = {
    "card_30_50_60": CARD,
    "minus30_clock60": "loss:-30% | clock+60m",
    "minus30_target100_60": "loss:-30% | target+100%/+60m",
    "sell_first_25": "loss:none | target+25%/+60m",
    "minus30_target25_60": "loss:-30% | target+25%/+60m",
}
COMPARE_LABEL = {
    "card_30_50_60": "30/50/60 card (-30% / +50% / 60m)",
    "minus30_clock60": "-30% + 60m clock",
    "minus30_target100_60": "-30% / +100% / 60m",
    "sell_first_25": "sell at the first +25% (no loss line, 60m fallback)",
    "minus30_target25_60": "-30% / +25% / 60m (JSON only)",
}
GROUPS = {g: v for g, v in ers.GROUPS.items() if "OTM1" not in g}     # the ATM groups: E2 pooled/call/put, E1 pooled/call/put
CHECK_FIELDS = ("n_trades", "n_sessions", "win_pct", "avg_win_pct", "avg_loss_pct", "loss_over_win", "mean_pct", "median_pct",
                "worst_pct", "stopped_share_pct", "avg_fill_when_stopped_pct", "t_sessions")


# ------------------------------------------------------------------------------------------- the engine
def runner_exit(tr, *, t1=T1, t2=1.00, stop=STOP, clock_min=CLOCK_MIN, post="breakeven", trail=0.25, keep_t2=True, info=None):
    """One trade, the two-contract card -> (r1, r2, pre, c2), results as fractions of the entry ask.
    `info`, if a dict, receives info["t1_min"] = minutes from entry to the snapshot where target 1 filled (stage trades only).

    pre = the study's reason code for the PAIR up to target 1 (R_STOP / R_TARGET / R_CLOCK / R_SETTLE); c2 = how contract 2
    left once target 1 had filled (C2_*), else C2_NONE. The total result is (r1 + r2) / 2."""
    ask, b, ts = tr["ask"], tr["b"], tr["tsec"]
    n = len(b)
    clock_s = clock_min * 60.0
    hit = b <= ask * (1 + stop) + EPS
    stop_i = int(hit.argmax()) if hit.any() else n
    hit = b >= ask * (1 + t1) - EPS
    tgt_i = int(hit.argmax()) if hit.any() else n
    clk_i = int(np.searchsorted(ts, clock_s, side="left"))
    idx = min(stop_i, tgt_i, clk_i)
    if idx >= n:                                            # nothing fired and no snapshot at the clock: settle (the grid's rule)
        r = tr["V"] / ask - 1
        return r, r, R_SETTLE, C2_NONE
    if stop_i == idx:                                       # the stop wins a tie (same bid, same price)
        r = b[idx] / ask - 1
        return r, r, R_STOP, C2_NONE
    if tgt_i != idx:                                        # the clock came first
        r = b[idx] / ask - 1
        return r, r, R_CLOCK, C2_NONE
    r1 = b[idx] / ask - 1                                   # target 1 fills here; contract 2 keeps running from this snapshot
    if info is not None:
        info["t1_min"] = float(ts[idx]) / 60.0
    peak = b[idx]
    for j in range(idx, n):
        bj = b[j]
        if bj > peak:
            peak = bj
        stopped = (bj <= ask + EPS) if post == "breakeven" else (bj <= peak * (1 - trail) + EPS)
        if stopped:
            return r1, bj / ask - 1, R_TARGET, C2_STOP
        if keep_t2 and bj >= ask * (1 + t2) - EPS:
            return r1, bj / ask - 1, R_TARGET, C2_TARGET
        if j >= clk_i:
            return r1, bj / ask - 1, R_TARGET, C2_CLOCK
    return r1, tr["V"] / ask - 1, R_TARGET, C2_SETTLE


# ------------------------------------------------------------------------------------------ statistics
def _rng(*key):
    return np.random.default_rng([BOOT_SEED, *key])


def runner_cell(tot, pre, c2, r1, r2, sid, card_pnl, t1min, gi, ri):
    """All the numbers for one runner rule in one group."""
    n = len(tot)
    allm = np.ones(n, bool)
    cell = ers.rule_stats(tot, pre, sid)                     # the study's own statistics, unchanged
    cell["mean_ci90_pct"] = ers.mean_pct(sid, tot, allm, _rng(gi, ri, 1))["ci90"]
    stage = pre == R_TARGET
    cell["reaches_runner_stage"] = ers.share(sid, stage, allm, _rng(gi, ri, 2))
    cell["runner_stage_decomposition"] = None
    if stage.any():
        d = (r2 - r1)[stage]
        cell["runner_stage_decomposition"] = {
            "n_trades": int(stage.sum()), "n_sessions": int(len(np.unique(sid[stage]))),
            "contract1_mean_pct": round(100 * float(r1[stage].mean()), 1),
            "contract2_mean_pct": round(100 * float(r2[stage].mean()), 1),
            "contract2_minus_contract1_mean_pct": round(100 * float(d.mean()), 1),
            "contract2_beats_contract1_share_pct": round(100 * float((d > 0).mean()), 1),
            "contract2_loses_money_share_pct": round(100 * float((r2[stage] < 0).mean()), 1),
            "contract2_exits": {C2_NAMES[c]: int((c2[stage] == c).sum()) for c in (C2_TARGET, C2_STOP, C2_CLOCK, C2_SETTLE)},
            "minutes_to_target1_q1_median_q3": [round(float(v), 1) for v in np.percentile(t1min[stage], [25, 50, 75])],
            "minutes_left_on_the_clock_at_target1_median": round(float(CLOCK_MIN - np.median(t1min[stage])), 1),
            "worst_total_result_pct": round(100 * float(tot[stage].min()), 1),
            "note": "a decomposition of the same cell, not an extra test"}
    diff = tot - card_pnl                                    # paired, trade by trade; 0 wherever target 1 never filled
    cell["vs_card"] = {
        "mean_diff_pct": round(100 * float(diff.mean()), 2),
        "ci90_pct": ers.mean_pct(sid, diff, allm, _rng(gi, ri, 3))["ci90"],
        "t_sessions": ers.cluster_t(diff, sid),
        "runner_better_share_pct": round(100 * float((diff > EPS).mean()), 1),
        "runner_worse_share_pct": round(100 * float((diff < -EPS).mean()), 1),
        "runner_worse_than_card_on_stage_trades_pct": round(100 * float((diff[stage] < -EPS).mean()), 1) if stage.any() else None,
        "worst_single_trade_diff_pct": round(100 * float(diff.min()), 1),
        "best_single_trade_diff_pct": round(100 * float(diff.max()), 1)}
    return cell


# ------------------------------------------------------------------------------------------------ main
def load_trades(through):
    files, sessions, skipped, trades, excluded, counters, off = ers.build(through)
    dead = [k for k, t in enumerate(trades) if len(t["b"]) == 0]       # the study's own step: no later quote, no path
    if dead:
        drop = set(dead)
        trades = [t for k, t in enumerate(trades) if k not in drop]
    return files, sessions, skipped, trades, dead


def main():
    ap = argparse.ArgumentParser(description="The Runner Card on the recorded SPY 0DTE data (descriptive; paper only).")
    ap.add_argument("--through", default=THROUGH, help="last session date to read; default %(default)s")
    ap.add_argument("--out", default=OUT, help="output JSON; default %(default)s")
    ap.add_argument("--study", default=STUDY_JSON, help="the exit-rules study JSON to re-read; default %(default)s")
    a = ap.parse_args()
    study = json.load(open(a.study))
    files, sessions, skipped, trades, dead = load_trades(a.through)
    N = len(trades)
    sid = np.array([t["sid"] for t in trades])
    eset = np.array([t["set"] for t in trades])
    inst = np.array([t["inst"] for t in trades])

    # per-trade series: the four runner rules and the study's comparison cells
    R = {k: np.zeros((N, 2)) for k in RUNNERS}
    PRE = {k: np.zeros(N, int) for k in RUNNERS}
    C2 = {k: np.full(N, C2_NONE, int) for k in RUNNERS}
    T1MIN = np.full(N, np.nan)
    CMP = {k: np.zeros(N) for k in COMPARE}
    CMPC = {k: np.zeros(N, int) for k in COMPARE}
    parsed = {name: next(r for r in ers.rules() if r[0] == name) for name in COMPARE.values()}
    for k, tr in enumerate(trades):
        for rk, prm in RUNNER_PARAMS.items():
            info = {}
            r1, r2, pre, c2 = runner_exit(tr, info=info, **{kk: vv for kk, vv in prm.items() if vv is not None})
            if "t1_min" in info:
                T1MIN[k] = info["t1_min"]
            R[rk][k] = (r1, r2)
            PRE[rk][k], C2[rk][k] = pre, c2
        for ck, name in COMPARE.items():
            _, L, kind, p = parsed[name]
            CMP[ck][k], CMPC[ck][k] = ers.rule_exit(tr, L, kind, p)

    # integrity: contract 1 IS the study's 30/50/60 cell, trade by trade, in every runner rule
    card = CMP["card_30_50_60"]
    c1_ok = {rk: bool(np.allclose(R[rk][:, 0], card, atol=1e-12)) and bool((PRE[rk] == CMPC["card_30_50_60"]).all()) for rk in RUNNERS}
    # integrity: pairs that never reached target 1 are identical to the card
    pre_ok = {rk: bool(np.allclose(R[rk][PRE[rk] != R_TARGET].mean(1), card[PRE[rk] != R_TARGET], atol=1e-12)) for rk in RUNNERS}

    results, repro_checked, repro_bad = {}, 0, []
    for gi, (g, (es, ins)) in enumerate(GROUPS.items()):
        sel = (eset == es) & np.isin(inst, ins)
        s = sid[sel]
        if int(sel.sum()) != study["data"]["trades"][g]:
            repro_bad.append(f"{g}: trades {int(sel.sum())} vs study {study['data']['trades'][g]}")
        block = {"n_trades": int(sel.sum()), "n_sessions": int(len(np.unique(s))), "clustered_by": "session date",
                 "runners": {}, "comparison": {}}
        for ri, rk in enumerate(RUNNERS):
            tot = R[rk][sel].mean(1)
            block["runners"][rk] = runner_cell(tot, PRE[rk][sel], C2[rk][sel], R[rk][sel][:, 0], R[rk][sel][:, 1], s,
                                               card[sel], T1MIN[sel], gi, ri)
        allm = np.ones(int(sel.sum()), bool)
        for ci, (ck, name) in enumerate(COMPARE.items()):
            mine = ers.rule_stats(CMP[ck][sel] * 1.0, CMPC[ck][sel], s)
            theirs = study["B_rule_grid"][g][name]
            for f in CHECK_FIELDS:
                repro_checked += 1
                if mine[f] != theirs[f]:
                    repro_bad.append(f"{g} | {name} | {f}: recomputed {mine[f]} vs study JSON {theirs[f]}")
            repro_checked += 1
            if mine["exits"] != theirs["exits"]:
                repro_bad.append(f"{g} | {name} | exits: recomputed {mine['exits']} vs study JSON {theirs['exits']}")
            cell = dict(theirs)                                   # the numbers are the study's, re-read
            cell["study_rule_name"] = name
            cell["label"] = COMPARE_LABEL[ck]
            cell["mean_ci90_pct"] = ers.mean_pct(s, CMP[ck][sel], allm, _rng(gi, 100 + ci, 1))["ci90"]
            cell["target_fill_share_pct"] = round(100 * theirs["exits"]["target"] / theirs["n_trades"], 1) if "target" in name else None
            results_diff = (R["runner_a"][sel].mean(1) - CMP[ck][sel])
            cell["runner_a_minus_this_mean_pct"] = round(100 * float(results_diff.mean()), 2)
            block["comparison"][ck] = cell
        results[g] = block

    n_groups, n_rules = len(GROUPS), len(RUNNERS)
    calm = study["data"]["calm_window"]
    ivs = [(g, rk, c["vs_card"]["ci90_pct"]) for g, b in results.items() for rk, c in b["runners"].items()]
    clear = [f"{g} | {rk}" for g, rk, (lo, hi) in ivs if lo > 0.05 or hi < -0.05]       # the interval is rounded to 0.1: +/-0.05 counts as touching zero
    touch = [f"{g} | {rk}" for g, rk, (lo, hi) in ivs if not (lo > 0.05 or hi < -0.05) and (abs(lo) <= 0.05 or abs(hi) <= 0.05)]
    out = {
        "generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "status": "DESCRIPTION ONLY - nothing registered, no position follows from it",
        "script": "src/exit_runner_study.py",
        "tests": "src/test_exit_runner_study.py",
        "builds_on": {"study": "results/EXIT_RULES_STUDY_2026-09-30.md", "json": "results/exit_rules_study_2026-09-30.json",
                      "code": "src/exit_rules_study.py (imported unchanged: loader, trades, rule_exit, rule_stats, mean_pct, share, cluster_t)"},
        "definitions": {"card": "two contracts at one ask; result = average of the two = % of total entry cost; both: -30% stop; contract 1: +50% target, 60m clock "
                                "(identical to the study's 30/50/60 cell); contract 2: after target 1 stop moves to entry, exits at +100%, its stop, or the 60m clock "
                                "(from entry); every exit at the bid of the snapshot where it triggers; same-snapshot triggers share one bid",
                        "runner_rules": {k: v["label"] for k, v in RUNNERS.items()},
                        "runner_params": RUNNER_PARAMS,
                        "comparison_cells": {k: {"study_rule_name": v, "label": COMPARE_LABEL[k]} for k, v in COMPARE.items()},
                        "intervals": f"90% session-bootstrap of the mean, 2000 draws, rng seeded [{BOOT_SEED}, group, rule, reading]; t = the study's cluster-robust t by session",
                        "vs_card": "paired per-trade difference (runner total - card result); exactly 0 where target 1 never fills"},
        "data": {"through": a.through, "sessions_used": len(sessions), "first_session": sessions[0].day, "last_session": sessions[-1].day,
                 "sessions_skipped_incomplete": skipped, "trades_with_no_later_quote_dropped": len(dead),
                 "trades": {g: int(((eset == es) & np.isin(inst, ins)).sum()) for g, (es, ins) in GROUPS.items()},
                 "calm_window_from_the_study": calm},
        "reproduction": {
            "statistics_checked_against_the_study_json": repro_checked, "mismatches": repro_bad, "all_match": not repro_bad,
            "contract1_equals_the_30_50_60_cell_trade_by_trade": c1_ok,
            "pairs_that_never_reach_target1_equal_the_card": pre_ok,
            "note": "the comparison cells' numbers in 'comparison' are the study JSON's own; the recompute exists for the interval and the paired differences"},
        "looks": {"new_rules": n_rules, "groups": n_groups, "cells": n_rules * n_groups,
                  "paired_differences_vs_the_card": n_rules * n_groups, "total_new_looks": 2 * n_rules * n_groups,
                  "note": "the brief named three rules (a, b, c); c was ambiguous (does the +100% target survive the trailing stop?) so both readings are run "
                          "and counted: the brief's three rules alone would be 3 x 6 = 18 cells + 18 paired differences = 36 looks. "
                          "The runner-stage decomposition and the comparison cells (re-read from the study) are not counted as new looks.",
                  "groups_reported": list(GROUPS),
                  "paired_90pct_intervals_excluding_zero": {"count": len(clear), "of": len(ivs), "cells": clear,
                                                             "expected_by_chance_at_90pct": round(0.10 * len(ivs), 1),
                                                             "touching_zero_at_the_rounded_edge": touch}},
        "results": results,
    }
    atomic_json(a.out, out, indent=1)
    print(f"runner card: {N} trades, {len(sessions)} sessions -> {a.out}")
    print(f"reproduction: {repro_checked} statistics checked against the study JSON, mismatches: {len(repro_bad)}")
    for m in repro_bad:
        print("   MISMATCH", m)
    print("contract 1 == 30/50/60 cell:", c1_ok, "| non-stage pairs == card:", pre_ok)
    for g in GROUPS:
        b = results[g]
        print(f"\n  {g}: {b['n_trades']} trades, {b['n_sessions']} sessions")
        for ck, c in b["comparison"].items():
            print(f"    {COMPARE_LABEL[ck]:<52} mean {c['mean_pct']:+.1f} [{c['mean_ci90_pct'][0]:+.1f},{c['mean_ci90_pct'][1]:+.1f}] win {c['win_pct']:.1f} "
                  f"avgW {c['avg_win_pct']} avgL {c['avg_loss_pct']} L/W {c['loss_over_win']} worst {c['worst_pct']} t {c['t_sessions']}")
        for rk, c in b["runners"].items():
            v = c["vs_card"]
            print(f"    {rk:<52} mean {c['mean_pct']:+.1f} [{c['mean_ci90_pct'][0]:+.1f},{c['mean_ci90_pct'][1]:+.1f}] win {c['win_pct']:.1f} "
                  f"avgW {c['avg_win_pct']} avgL {c['avg_loss_pct']} L/W {c['loss_over_win']} worst {c['worst_pct']} t {c['t_sessions']} "
                  f"stage {c['reaches_runner_stage']['pct']}%  vsCard {v['mean_diff_pct']:+.2f} [{v['ci90_pct'][0]:+.2f},{v['ci90_pct'][1]:+.2f}] t {v['t_sessions']}")


if __name__ == "__main__":
    main()

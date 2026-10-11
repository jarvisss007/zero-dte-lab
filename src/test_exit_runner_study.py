"""Hand-made price-path tests for exit_runner_study.py (the Runner Card).
Run: /opt/anaconda3/bin/python -m pytest -q src/test_exit_runner_study.py

Every path is a list of BIDS at 5-minute snapshots after entry; the entry ask is 1.00, so a bid is also the contract's gross
result + 1. The total result is the average of the two contracts (% of the total entry cost)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_rules_study as ers  # noqa: E402
import exit_runner_study as rs  # noqa: E402


def trade(bids, ask=1.0, step=300.0, settle=0.0):
    """A trade dict as the study builds them: snapshots 5 minutes apart, the first one `step` seconds after entry."""
    b = np.array(bids, float)
    return {"ask": ask, "b": b, "tsec": step * np.arange(1, len(b) + 1), "V": settle}


def total(tr, **kw):
    r1, r2, pre, c2 = rs.runner_exit(tr, **kw)
    return (r1 + r2) / 2, r1, r2, pre, c2


# --- the three paths the brief asks for ---------------------------------------------------------------------------------
def test_target1_then_back_to_entry_ends_at_plus_25():
    t, r1, r2, pre, c2 = total(trade([1.2, 1.5, 1.3, 1.0, 0.8]))
    assert abs(r1 - 0.50) < 1e-12 and abs(r2 - 0.0) < 1e-12          # contract 2 stopped at breakeven (the bid exactly at entry)
    assert abs(t - 0.25) < 1e-12
    assert pre == rs.R_TARGET and c2 == rs.C2_STOP


def test_target1_then_target2_ends_at_plus_75():
    t, r1, r2, pre, c2 = total(trade([1.2, 1.5, 1.8, 2.0, 0.5]))
    assert abs(r1 - 0.50) < 1e-12 and abs(r2 - 1.00) < 1e-12
    assert abs(t - 0.75) < 1e-12
    assert pre == rs.R_TARGET and c2 == rs.C2_TARGET


def test_minus_30_first_ends_at_minus_30():
    t, r1, r2, pre, c2 = total(trade([0.9, 0.7, 1.6, 2.5]))        # the 0.70 bid touches the line exactly; later bids never matter
    assert abs(t - (-0.30)) < 1e-12 and abs(r1 - r2) < 1e-12
    assert pre == rs.R_STOP and c2 == rs.C2_NONE


def test_minus_30_overshoot_is_real():
    t, *_ = total(trade([0.9, 0.62, 1.6]))                          # the snapshot is past the line: filled at that bid, -38%
    assert abs(t - (-0.38)) < 1e-12


# --- the rest of the rule ----------------------------------------------------------------------------------------------
def test_breakeven_stop_also_overshoots():
    t, r1, r2, *_ = total(trade([1.5, 0.8]))                        # contract 2 fills at the 0.80 bid, below entry
    assert abs(r1 - 0.5) < 1e-12 and abs(r2 - (-0.2)) < 1e-12 and abs(t - 0.15) < 1e-12


def test_a_jump_through_both_targets_fills_both_at_that_bid():
    t, r1, r2, pre, c2 = total(trade([1.0, 2.3, 0.2]))
    assert abs(r1 - 1.3) < 1e-12 and abs(r2 - 1.3) < 1e-12 and abs(t - 1.3) < 1e-12
    assert pre == rs.R_TARGET and c2 == rs.C2_TARGET


def test_stop_ahead_of_target_on_a_slow_path():
    t, *_ = total(trade([1.1, 0.95, 0.69, 1.6]))                    # -31% before +50%: both stopped
    assert abs(t - (-0.31)) < 1e-12


def test_clock_exit_both_contracts_when_neither_target_hits():
    bids = [1.1] * 11 + [1.2, 1.4, 3.0]                              # snapshot 12 (index 11) is 60 minutes after entry
    t, r1, r2, pre, c2 = total(trade(bids))
    assert pre == rs.R_CLOCK and abs(t - 0.2) < 1e-12 and abs(r1 - r2) < 1e-12


def test_runner_hits_the_clock_after_target1():
    bids = [1.5] + [1.2] * 10 + [1.4, 1.2]                           # target 1 at 5m; contract 2 holds above entry until the 60m clock
    t, r1, r2, pre, c2 = total(trade(bids))
    assert pre == rs.R_TARGET and c2 == rs.C2_CLOCK
    assert abs(r1 - 0.5) < 1e-12 and abs(r2 - 0.4) < 1e-12 and abs(t - 0.45) < 1e-12


def test_target1_and_the_clock_on_the_same_snapshot():
    bids = [1.1] * 11 + [1.6, 1.0]                                   # the first snapshot at 60m is the one that fills +50%
    t, r1, r2, pre, c2 = total(trade(bids))
    assert pre == rs.R_TARGET and c2 == rs.C2_CLOCK and abs(t - 0.6) < 1e-12


def test_settle_when_nothing_fires_and_no_snapshot_reaches_the_clock():
    t, r1, r2, pre, c2 = total(trade([1.1, 1.0, 0.9], settle=0.4))   # path ends at 15 minutes: both settle at 0.40
    assert pre == rs.R_SETTLE and abs(t - (-0.6)) < 1e-12


def test_runner_settles_when_the_path_ends_before_any_runner_exit():
    t, r1, r2, pre, c2 = total(trade([1.5, 1.6, 1.7], settle=1.3))
    assert pre == rs.R_TARGET and c2 == rs.C2_SETTLE and abs(r2 - 0.3) < 1e-12 and abs(t - 0.4) < 1e-12


def test_variant_b_runner_target_150():
    path = trade([1.5, 2.0, 2.4, 2.6, 0.5])
    t_a = total(path)[0]
    t_b = total(path, t2=1.5)[0]
    assert abs(t_a - 0.75) < 1e-12                                   # (a) sells the runner at 2.0 -> (50+100)/2
    assert abs(t_b - 1.05) < 1e-12                                   # (b) holds to 2.6 -> (50+160)/2


def test_variant_c_trailing_stop_from_peak_bid():
    path = trade([1.5, 1.8, 2.4, 1.9, 1.7, 3.0])
    t, r1, r2, pre, c2 = total(path, post="trail", trail=0.25, keep_t2=False)
    assert c2 == rs.C2_STOP and abs(r2 - 0.7) < 1e-12 and abs(t - 0.6) < 1e-12   # peak 2.4 -> line 1.8 -> 1.7 exits at +70%
    t2_, r1b, r2b, preb, c2b = total(path, post="trail", trail=0.25, keep_t2=True)
    assert c2b == rs.C2_TARGET and abs(r2b - 1.4) < 1e-12 and abs(t2_ - 0.95) < 1e-12   # with the +100% cap it sells the 2.4 bid


def test_variant_c_trail_is_above_breakeven_while_the_runner_is_at_least_plus_50():
    t, r1, r2, pre, c2 = total(trade([1.5, 1.1, 5.0]), post="trail", trail=0.25, keep_t2=False)
    assert c2 == rs.C2_STOP and abs(r2 - 0.1) < 1e-12               # 1.1 <= 0.75 x 1.5: out at +10%, not held to breakeven


# --- integrity against the study's own engine, on random paths -------------------------------------------------------------
def _walk(rng, n):
    steps = rng.normal(0.0, rng.choice([0.04, 0.10, 0.20]), n)
    p = 1.0 * np.exp(np.cumsum(steps))
    return np.round(np.maximum(p, 0.0), 2)


def test_contract_1_is_exactly_the_study_30_50_60_cell_on_random_paths():
    rng = np.random.default_rng(7)
    name = "loss:-30% | target+50%/+60m"
    _, L, kind, p = next(r for r in ers.rules() if r[0] == name)
    for _ in range(3000):
        n = int(rng.integers(1, 90))
        tr = trade(_walk(rng, n), ask=1.0, settle=float(rng.choice([0.0, 0.7, 2.0])))
        study_res, study_code = ers.rule_exit(tr, L, kind, p)
        for prm in rs.RUNNER_PARAMS.values():
            r1, r2, pre, c2 = rs.runner_exit(tr, **{k: v for k, v in prm.items() if v is not None})
            assert abs(r1 - study_res) < 1e-12 and pre == study_code
            if pre != rs.R_TARGET:
                assert abs(r2 - r1) < 1e-12                          # a pair that never reached the runner stage is the card


def _naive(tr, t2, post, trail, keep_t2):
    """An independent re-statement: two separate positions, each stepped through the snapshots with its own state."""
    ask, b, ts = tr["ask"], tr["b"], tr["tsec"]
    done = [None, None]
    t1_filled = False
    peak = 0.0
    for j in range(len(b)):
        bj = b[j]
        peak = max(peak, bj)
        clock = ts[j] >= 3600
        if done[0] is None:
            if bj <= 0.7 * ask + 1e-9:
                done[0] = bj / ask - 1
            elif bj >= 1.5 * ask - 1e-9:
                done[0] = bj / ask - 1
                t1_filled = True
            elif clock:
                done[0] = bj / ask - 1
        if done[1] is None:
            if not t1_filled:
                if bj <= 0.7 * ask + 1e-9 or clock:
                    done[1] = bj / ask - 1
            else:
                line = ask if post == "breakeven" else peak * (1 - trail)
                if bj <= line + 1e-9:
                    done[1] = bj / ask - 1
                elif keep_t2 and bj >= ask * (1 + t2) - 1e-9:
                    done[1] = bj / ask - 1
                elif clock:
                    done[1] = bj / ask - 1
    return done


def test_matches_an_independent_two_position_simulator_on_random_paths():
    rng = np.random.default_rng(11)
    for _ in range(4000):
        n = int(rng.integers(1, 90))
        tr = trade(_walk(rng, n), ask=1.0, settle=float(rng.choice([0.0, 0.7, 2.0])))
        for prm in rs.RUNNER_PARAMS.values():
            kw = {k: v for k, v in prm.items() if v is not None}
            r1, r2, pre, c2 = rs.runner_exit(tr, **kw)
            d = _naive(tr, prm["t2"] if prm["t2"] is not None else 1.0, prm["post"], 0.25, prm["keep_t2"])
            e1 = d[0] if d[0] is not None else tr["V"] / tr["ask"] - 1       # nothing fired: both settle
            e2 = d[1] if d[1] is not None else tr["V"] / tr["ask"] - 1
            assert abs(r1 - e1) < 1e-12 and abs(r2 - e2) < 1e-12, (prm, tr["b"], r1, r2, e1, e2)

#!/opt/anaconda3/bin/python
"""day_high_retest_study.py - two more replay observations, counted (2026-09-19).

Anupam, watching SPY 5m in bar replay with IE Pro ONE drawn on it:
  1. "if it makes the day's high and again goes to the day's high and doesn't break it, it will fall
     from that point"
  2. "more red zone than green zone ... when the candle comes to the high again the accumulation has
     had enough, now it's time to release"

PRE-DECLARED before any number was seen. Nothing below was tuned after a run.
  day's high  the regular session's running high as of the bar BEFORE the retest bar (H).
  retest      H is at least 3 bars old, price has since traded at least 1 ATR below it, and this is the
              first bar whose high comes back within 0.1 ATR of H. It may poke through: that is the sweep.
              A third touch counts again only after another 1 ATR pullback.
  Q-e1  at the touch   enter next open: -1 ATR below H (reject) or +1 ATR above H (break) first?
                       The claim is REJECT.
  Q-e2  his version    only when the retest bar CLOSES back below H, so the failure is visible at that
                       close: short next open, stop = the higher of H and that bar's high, + 0.1 ATR;
                       target = twice the stop distance. The claim is TARGET first. A walk with no
                       memory gets there 33.3% of the time, which is also where 2:1 breaks even.
  colour      the boxes IE Pro ONE has live at the retest bar's close, ported rule for rule from the
              Pine: order blocks, breaker blocks, fair value gaps (>= 0.25 ATR, removed when filled,
              8 kept) and volume order blocks where the sample has volume. red = bearish boxes,
              green = bullish. The claim is that MORE RED THAN GREEN raises the rejection rate.
  mirror      the day's LOW retest (claim = it bounces; more GREEN should help) is scored the same way.
              It is the drift control.
  same session only; timeouts count at their fractional position; entries at the next bar's open;
  both barriers in one bar = ambiguous, dropped and counted; n = independent SESSION DATES.
A description of what these pictures have been worth. Not a strategy; registers no variant.
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atomicio import atomic_json                                     # noqa: E402
from data_utils import atr, load_minute_closes, minute_to_pseudo_ohlc  # noqa: E402
from zone_rotation_study import NAMES, first_passage, yahoo          # noqa: E402

OUT = HERE.parent / "results" / "day_high_retest_study.json"
INDEX_FUNDS = ("SPY", "QQQ", "IWM")
PULLBACK_ATR, NEAR_ATR, MIN_AGE, STOP_BUF, RR = 1.0, 0.1, 3, 0.1, 2.0


def zone_colours(df: pd.DataFrame, piv=5, ob_look=20, fvg_min=0.25, keep=8, vob_len=5):
    """(red, green) live IE Pro ONE boxes as of each bar's close - the Pine's bookkeeping, in its order."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float) if "volume" in df and df["volume"].notna().any() else None
    a = atr(df).to_numpy()
    n = len(df)
    red, green = np.zeros(n, int), np.zeros(n, int)
    lastSH = lastSL = None
    bullOB = bearOB = None                       # (top, bottom) of the one live order block per side
    bullBrk = bearBrk = False                    # a breaker, once drawn, stays until it is replaced
    fvg_up, fvg_dn, vob_up, vob_dn = [], [], [], []
    for i in range(n):
        if i >= 2 * piv:
            k = i - piv
            wh, wl = h[k - piv:i + 1], l[k - piv:i + 1]
            if h[k] == wh.max() and (wh == h[k]).sum() == 1:
                lastSH = h[k]
            if l[k] == wl.min() and (wl == l[k]).sum() == 1:
                lastSL = l[k]
        up = i > 0 and lastSH is not None and c[i] > lastSH and c[i - 1] <= lastSH
        dn = i > 0 and lastSL is not None and c[i] < lastSL and c[i - 1] >= lastSL
        if up:
            for j in range(1, min(ob_look, i) + 1):
                if c[i - j] < o[i - j]:
                    bullOB = (h[i - j], l[i - j])
                    break
        if dn:
            for j in range(1, min(ob_look, i) + 1):
                if c[i - j] > o[i - j]:
                    bearOB = (h[i - j], l[i - j])
                    break
        if bullOB is not None and c[i] < bullOB[1]:
            bearBrk, bullOB = True, None
        if bearOB is not None and c[i] > bearOB[0]:
            bullBrk, bearOB = True, None
        if i >= 2:
            if l[i] > h[i - 2] and l[i] - h[i - 2] >= fvg_min * a[i]:
                fvg_up.append((l[i], h[i - 2]))
            if h[i] < l[i - 2] and l[i - 2] - h[i] >= fvg_min * a[i]:
                fvg_dn.append((l[i - 2], h[i]))
        fvg_up = [b for b in fvg_up if l[i] > b[1]][-keep:]
        fvg_dn = [b for b in fvg_dn if h[i] < b[0]][-keep:]
        if v is not None and i >= 2 * vob_len:
            k = i - vob_len
            wv = v[k - vob_len:i + 1]
            if v[k] == wv.max() and (wv == v[k]).sum() == 1:
                mid = (h[k] + l[k]) / 2
                (vob_up if c[k] > o[k] else vob_dn).append((mid, l[k]) if c[k] > o[k] else (h[k], mid))
        vob_up = [b for b in vob_up if c[i] >= b[1]][-keep:]
        vob_dn = [b for b in vob_dn if c[i] <= b[0]][-keep:]
        red[i] = (bearOB is not None) + bearBrk + len(fvg_dn) + len(vob_dn)
        green[i] = (bullOB is not None) + bullBrk + len(fvg_up) + len(vob_up)
    return red, green


def scan(df: pd.DataFrame, name: str) -> dict[str, list]:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a14 = atr(df).to_numpy()
    red, green = zone_colours(df)
    date = df["ts"].dt.date.to_numpy()
    out = {"e1_at_the_touch": [], "e2_after_a_failed_close": []}
    skipped = {"retest_on_the_last_bar": 0, "gap_past_a_barrier": 0}
    bounds = pd.Series(np.arange(len(df))).groupby(date).agg(["min", "max"]).to_numpy()

    def record(q, side, i, e, up, dn, res):
        y, px, _, status = res
        claim_up = side == "L"                   # a day's-low retest claims the bounce, a day's-high retest the fall
        row = {"name": name, "date": str(date[i]), "side": side, "status": status,
               "red": int(red[i]), "green": int(green[i])}
        with_claim = red[i] > green[i] if side == "H" else green[i] > red[i]
        against = green[i] > red[i] if side == "H" else red[i] > green[i]
        row["colour"] = "with" if with_claim else "against" if against else "tie"
        if y is not None:
            p_up = (e - dn) / (up - dn)
            row["hit"] = y if claim_up else 1.0 - y
            row["p0"] = p_up if claim_up else 1.0 - p_up
            row["excess"] = row["hit"] - row["p0"]
            row["bps"] = (1.0 if claim_up else -1.0) * (px - e) / e * 1e4
        out[q].append(row)

    for s, e_ in bounds:
        for side in ("H", "L"):
            sign = 1.0 if side == "H" else -1.0           # work on sign*price so one loop serves both sides
            ext = (h if side == "H" else l)
            opp = (l if side == "H" else h)
            level, born, pulled, busy = ext[s], s, False, -1
            for i in range(s + 1, e_ + 1):
                a = a14[i - 1]
                near = sign * ext[i] >= sign * level - NEAR_ATR * a
                if pulled and i - born >= MIN_AGE and near and i > busy and a > 0:
                    pulled = False
                    if i + 1 > e_:
                        skipped["retest_on_the_last_bar"] += 1
                    else:
                        ent, ai = o[i + 1], a14[i]
                        if level - ai < ent < level + ai:
                            res = first_passage(o, h, l, c, i + 1, e_ + 1, level + ai, level - ai)
                            record("e1_at_the_touch", side, i, ent, level + ai, level - ai, res)
                            busy = res[2]
                        else:
                            skipped["gap_past_a_barrier"] += 1
                        failed = c[i] < level if side == "H" else c[i] > level
                        if failed:
                            worst = max(level, h[i]) if side == "H" else min(level, l[i])
                            stop = worst + sign * STOP_BUF * ai
                            dist = sign * (stop - ent)
                            if dist > 0:
                                tgt = ent - sign * RR * dist
                                up_, dn_ = (stop, tgt) if side == "H" else (tgt, stop)
                                record("e2_after_a_failed_close", side, i, ent, up_, dn_,
                                       first_passage(o, h, l, c, i + 1, e_ + 1, up_, dn_))
                            else:
                                skipped["gap_past_a_barrier"] += 1
                if sign * opp[i] <= sign * level - PULLBACK_ATR * a:
                    pulled = True
                if sign * ext[i] > sign * level:
                    level, born, pulled = ext[i], i, False
    out["_skipped"] = [skipped]
    return out


def summ(rows: list) -> dict:
    rows = [r for r in rows if r["status"] != "ambiguous"]
    if not rows:
        return {"n_events": 0, "reason": "no such event in this sample"}
    df = pd.DataFrame(rows)
    days = df.groupby("date")["excess"].mean()
    sd = days.std(ddof=1) if len(days) > 2 else float("nan")
    t = float(days.mean() / (sd / math.sqrt(len(days)))) if sd and sd > 0 else None
    return {"n_events": int(len(df)), "n_days": int(len(days)), "clustered_by": "session date, all names pooled",
            "hit_pct": round(float(df["hit"].mean()) * 100, 1), "no_memory_pct": round(float(df["p0"].mean()) * 100, 1),
            "excess_pp": round(float(df["excess"].mean()) * 100, 1), "t_days": None if t is None else round(t, 2),
            "gross_bps_per_trade": round(float(df["bps"].mean()), 2),
            "timeouts": int((df["status"] == "timeout").sum())}


def colour_gap(rows: list, seed=7) -> dict:
    """Does the colour WITH the claim beat the colour AGAINST it? Difference in excess, days resampled."""
    df = pd.DataFrame([r for r in rows if r["status"] != "ambiguous" and r["colour"] != "tie"])
    if df.empty or df["colour"].nunique() < 2:
        return {"reason": "one colour state never occurred"}
    df["w"] = (df["colour"] == "with").astype(float)
    g = df.assign(sw=df["excess"] * df["w"], sa=df["excess"] * (1 - df["w"]), na=1 - df["w"]) \
          .groupby("date")[["sw", "w", "sa", "na"]].sum().to_numpy()
    gap = lambda m: m[..., 0] / m[..., 1] - m[..., 2] / m[..., 3]
    point = float(gap(g.sum(axis=0)))
    rng = np.random.default_rng(seed)
    with np.errstate(divide="ignore", invalid="ignore"):
        boots = gap(g[rng.integers(0, len(g), size=(2000, len(g)))].sum(axis=1))
    boots = boots[np.isfinite(boots)]
    se = float(np.std(boots, ddof=1))
    return {"gap_pp": round(point * 100, 1), "se_pp": round(se * 100, 1),
            "t_days_bootstrap": round(point / se, 2) if se > 0 else None,
            "n_with": int(df["w"].sum()), "n_against": int((1 - df["w"]).sum()),
            "n_days": int(len(g)), "clustered_by": "session date (2,000 resamples of days)"}


def pack(pooled: dict, keep=lambda r: True) -> dict:
    res = {}
    for q, rows in pooled.items():
        rows = [r for r in rows if keep(r)]
        H = [r for r in rows if r["side"] == "H"]
        res[q] = {
            "days_high_retest": summ(H), "days_low_retest_mirror": summ([r for r in rows if r["side"] == "L"]),
            "high_retest_when_more_red": summ([r for r in H if r["colour"] == "with"]),
            "high_retest_when_more_green": summ([r for r in H if r["colour"] == "against"]),
            "colour_with_vs_against_both_sides": colour_gap(rows),
            "colour_with_vs_against_high_only": colour_gap(H)}
    return res


def run(frames: dict):
    pooled = {"e1_at_the_touch": [], "e2_after_a_failed_close": []}
    skipped: dict[str, int] = {}
    for nm, d in frames.items():
        r = scan(d, nm)
        for q in pooled:
            pooled[q] += r[q]
        for k, v in r["_skipped"][0].items():
            skipped[k] = skipped.get(k, 0) + v
    return pooled, skipped


def main():
    samples = {}
    spy = minute_to_pseudo_ohlc(load_minute_closes())
    pooled, skipped = run({"SPY": spy})
    samples["spy_5m_2024_2025"] = {
        "what": "SPY 5-minute bars built from 1-minute closes; no volume, so the colour count has no volume blocks",
        "from": str(spy["ts"].min().date()), "to": str(spy["ts"].max().date()),
        "sessions": int(spy["ts"].dt.date.nunique()), "questions": pack(pooled), "events_not_scored": skipped}
    try:
        frames, dropped = yahoo(NAMES, "5m", "60d")
        pooled, skipped = run(frames)
        allts = pd.concat([d["ts"] for d in frames.values()])
        samples["his_names_5m_last_60d"] = {
            "what": "Yahoo 5-minute bars with volume, regular session, full colour count",
            "from": str(allts.min().date()), "to": str(allts.max().date()), "sessions": int(allts.dt.date.nunique()),
            "names": sorted(frames), "dropped": dropped, "questions": pack(pooled),
            "index_funds_only": pack(pooled, lambda r: r["name"] in INDEX_FUNDS), "events_not_scored": skipped}
    except Exception as ex:                                    # a fetch failure is a stated zero
        samples["his_names_5m_last_60d"] = {"n_events": 0, "reason": f"fetch failed: {type(ex).__name__}: {ex}"}

    looks = sum(12 * (1 + ("index_funds_only" in v)) for v in samples.values() if "questions" in v)
    report = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
              "rules": {"pullback_atr": PULLBACK_ATR, "near_atr": NEAR_ATR, "min_age_bars": MIN_AGE,
                        "stop_buffer_atr": STOP_BUF, "reward_to_risk_e2": RR},
              "samples": samples, "looks_in_this_file": looks, "looks_with_the_rotation_study": looks + 36,
              "chance_of_one_t2_by_luck_all_looks": round(1 - (1 - 0.0455) ** (looks + 36), 2),
              "status": "DESCRIPTION ONLY - not through edge-refute, nothing registered, no position follows from it"}
    OUT.parent.mkdir(exist_ok=True)
    atomic_json(OUT, report, indent=1)

    def line(tag, r):
        if not r.get("n_events"):
            return f"      {tag:34s} n=0 ({r.get('reason')})"
        return (f"      {tag:34s} n={r['n_events']:4d} days={r['n_days']:4d}  {r['hit_pct']:5.1f}% vs {r['no_memory_pct']:5.1f}%"
                f"  excess {r['excess_pp']:+5.1f}pp  t={r['t_days']}  gross {r['gross_bps_per_trade']:+.2f}bps")

    for s, v in samples.items():
        print(f"\n== {s}: {v.get('what')} [{v.get('from')} -> {v.get('to')}, {v.get('sessions')} sessions]")
        if "questions" not in v:
            print("   ", v.get("reason"))
            continue
        for block in ("questions", "index_funds_only"):
            if block not in v:
                continue
            print(f"   -- {block}")
            for q, r in v[block].items():
                print(f"    {q}")
                for k in ("days_high_retest", "days_low_retest_mirror", "high_retest_when_more_red",
                          "high_retest_when_more_green"):
                    print(line(k, r[k]))
                print("      colour with-vs-against, both sides:", r["colour_with_vs_against_both_sides"])
                print("      colour with-vs-against, high only :", r["colour_with_vs_against_high_only"])
        print("   not scored:", v["events_not_scored"])
    print(f"\nlooks here {looks}, with the rotation study {looks + 36}: chance of one |t|>=2 by luck "
          f"{report['chance_of_one_t2_by_luck_all_looks']}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

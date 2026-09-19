#!/opt/anaconda3/bin/python
"""zone_rotation_study.py - is the premium / equilibrium rotation seen in bar replay worth anything?

Anupam's observation (2026-09-19), from replaying charts with IE Pro ONE drawn on them:
  price travels from equilibrium to the premium zone, comes back near equilibrium and decides there;
  if it holds above the day's low and bounces it goes to premium again; at the previous high it either
  breaks or rejects.

PRE-DECLARED before any number was seen. Nothing below was tuned after a run.
  frame      exactly what IE Pro ONE draws, AS OF each bar: the rolling window high and low
             (5m: 156 bars, 1h: 120 bars); premium = top 5% of that range, equilibrium = the middle
             +/-2.5%, discount = bottom 5%.
  pattern P  the last extreme zone visited was premium, then price comes down to the equilibrium band.
  pattern D  the mirror image (discount, then up to equilibrium). It is the drift control: if a rising
             tape is doing the work, P looks good and D looks bad by the same amount.
  Q-a  at the touch          does price get BACK to the zone it came from before it reaches the far zone?
  Q-b  after a bounce bar    the same, entered only after a candle closes back beyond the band, his way.
  Q-c  his sentence          bounce bar, stop = the day's low (day's high for D) as of that bar,
                             target = the zone it came from, same session only.
  Q-d  at the prior extreme  once price is back at the old high (low): +1 ATR (break) or -1 ATR
                             (reject) first?
  benchmark  a walk with no memory reaches the upper barrier first with probability
             (entry - lower) / (upper - lower). Every event carries that number and the statistic is
             outcome minus it. A timeout counts at its fractional position between the barriers, which
             has the same expectation, so no event is dropped for being slow.
  entries    the NEXT bar's open after the decision bar. Both barriers inside one bar = ambiguous:
             dropped and counted.
  n          independent SESSION DATES. Every name on one date is one cluster. Never rows.
This describes what the zones have been worth. It is not a strategy and it registers no variant.
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
from atomicio import atomic_json                                        # noqa: E402
from data_utils import ET, atr, load_bats, load_minute_closes, minute_to_pseudo_ohlc  # noqa: E402

OUT = HERE.parent / "results" / "zone_rotation_study.json"
PREM, EQ_HALF = 0.05, 0.025
MIN_STOP = 0.02            # Q-c: the day's low must sit at least 2% of the range away from the entry
# index funds and liquid leaders, then the names he has had on the chart this month
NAMES = ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL",
         "SNDK", "RGTI", "HWM", "SOUN", "ONDS", "SMR", "AVAV", "ARM", "BE", "SPCX"]
QUESTIONS = {
    "a_at_the_touch":       "at the equilibrium touch: back to the zone it came from, before the far zone?",
    "b_after_a_bounce_bar": "after a candle closes back beyond the band: back to the zone it came from?",
    "c_his_sentence":       "bounce bar, stop at the day's low (high), target the zone, same session",
    "d_at_the_prior_extreme": "back at the old high (low): +1 ATR break before -1 ATR rejection?",
}


def first_passage(o, h, l, c, start, end, up, dn):
    """Walk bars [start, end). Returns (y, exit_px, j, status); y is 1 for the upper barrier first,
    0 for the lower, the fractional position at a timeout, None when one bar holds both."""
    for j in range(start, end):
        if o[j] >= up:
            return 1.0, o[j], j, "up"
        if o[j] <= dn:
            return 0.0, o[j], j, "down"
        hit_u, hit_d = h[j] >= up, l[j] <= dn
        if hit_u and hit_d:
            return None, None, j, "ambiguous"
        if hit_u:
            return 1.0, up, j, "up"
        if hit_d:
            return 0.0, dn, j, "down"
    j = end - 1
    return min(1.0, max(0.0, (c[j] - dn) / (up - dn))), c[j], j, "timeout"


def scan(df: pd.DataFrame, name: str, W: int, H: int, H_d: int) -> dict[str, list]:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(df)
    date = df["ts"].dt.date.to_numpy()
    hi = df["high"].rolling(W, min_periods=W).max().to_numpy()
    lo = df["low"].rolling(W, min_periods=W).min().to_numpy()
    a14 = atr(df).to_numpy()
    day_lo = df.groupby(date)["low"].cummin().to_numpy()
    day_hi = df.groupby(date)["high"].cummax().to_numpy()
    last_of_day = pd.Series(np.arange(n)).groupby(date).transform("max").to_numpy()

    out: dict[str, list] = {q: [] for q in QUESTIONS}
    skipped = {"gap_past_a_barrier": 0, "no_bounce_before_the_far_zone": 0, "bounce_on_the_last_bar": 0,
               "days_low_too_close_or_wrong_side": 0}

    def record(q, side, i, e, up, dn, res):
        y, px, _, status = res
        p_up = (e - dn) / (up - dn)
        claim_up = side == "P"                      # P claims the upper barrier, D the lower
        row = {"name": name, "date": str(date[i]), "side": side, "status": status}
        if y is not None:
            sgn = 1.0 if claim_up else -1.0
            row["hit"] = y if claim_up else 1.0 - y
            row["p0"] = p_up if claim_up else 1.0 - p_up
            row["excess"] = row["hit"] - row["p0"]
            row["bps"] = sgn * (px - e) / e * 1e4
        out[q].append(row)

    last_zone, busy_until = None, -1
    for i in range(W - 1, n - 2):
        R = hi[i] - lo[i]
        if not R > 0:
            continue
        in_p, in_d = h[i] >= hi[i] - PREM * R, l[i] <= lo[i] + PREM * R
        if in_p or in_d:
            last_zone = None if (in_p and in_d) else ("P" if in_p else "D")
            continue
        if last_zone is None or i <= busy_until:
            continue
        mid = (hi[i] + lo[i]) / 2
        touched = l[i] <= mid + EQ_HALF * R if last_zone == "P" else h[i] >= mid - EQ_HALF * R
        if not touched:
            continue

        # ---- the decision bar: freeze what he would have seen drawn on it
        side, T, B = last_zone, hi[i], lo[i]
        U, D = T - PREM * R, B + PREM * R
        busy_until = i + 1
        last_zone = None                 # the next event needs a fresh visit to a zone, not a stale one

        # Q-a
        e = o[i + 1]
        res_a = None
        if D < e < U:
            res_a = first_passage(o, h, l, c, i + 1, min(n, i + 1 + H), U, D)
            record("a_at_the_touch", side, i, e, U, D, res_a)
            busy_until = res_a[2]
        else:
            skipped["gap_past_a_barrier"] += 1

        # Q-b and Q-c share the bounce bar, judged on the frame AS OF that bar
        k_found = None
        for k in range(i, min(n - 2, i + H)):
            Rk = hi[k] - lo[k]
            if not Rk > 0:
                break
            mk = (hi[k] + lo[k]) / 2
            if side == "P":
                if l[k] <= lo[k] + PREM * Rk:
                    break
                if c[k] > mk + EQ_HALF * Rk and c[k] > o[k]:
                    k_found = k
                    break
            else:
                if h[k] >= hi[k] - PREM * Rk:
                    break
                if c[k] < mk - EQ_HALF * Rk and c[k] < o[k]:
                    k_found = k
                    break
        if k_found is None:
            skipped["no_bounce_before_the_far_zone"] += 1
        else:
            k = k_found
            Rk = hi[k] - lo[k]
            Uk, Dk = hi[k] - PREM * Rk, lo[k] + PREM * Rk
            e = o[k + 1]
            if Dk < e < Uk:
                record("b_after_a_bounce_bar", side, k, e, Uk, Dk,
                       first_passage(o, h, l, c, k + 1, min(n, k + 1 + H), Uk, Dk))
            else:
                skipped["gap_past_a_barrier"] += 1
            if k >= last_of_day[k]:
                skipped["bounce_on_the_last_bar"] += 1
            else:
                up, dn = (Uk, day_lo[k]) if side == "P" else (day_hi[k], Dk)
                near = (e - dn) if side == "P" else (up - e)
                if dn < e < up and near >= MIN_STOP * Rk:
                    record("c_his_sentence", side, k, e, up, dn,
                           first_passage(o, h, l, c, k + 1, last_of_day[k] + 1, up, dn))
                else:
                    skipped["days_low_too_close_or_wrong_side"] += 1

        # Q-d: only when Q-a got back to its zone; then wait for the old extreme itself to be touched
        if res_a is not None and res_a[3] == ("up" if side == "P" else "down"):
            level = T if side == "P" else B
            for m in range(res_a[2], min(n - 2, i + 1 + H)):
                if (side == "P" and l[m] <= D) or (side == "D" and h[m] >= U):
                    break
                if (side == "P" and h[m] >= level) or (side == "D" and l[m] <= level):
                    a = a14[m]
                    e = o[m + 1]
                    if a > 0 and level - a < e < level + a:
                        record("d_at_the_prior_extreme", side, m, e, level + a, level - a,
                               first_passage(o, h, l, c, m + 1, min(n, m + 1 + H_d), level + a, level - a))
                    break
    out["_skipped"] = [skipped]
    return out


def summarise(rows: list) -> dict:
    if not rows:
        return {"n_events": 0, "reason": "the pattern never completed in this sample"}
    df = pd.DataFrame(rows)
    amb = int((df["status"] == "ambiguous").sum())
    df = df[df["status"] != "ambiguous"]
    if df.empty:
        return {"n_events": 0, "ambiguous_dropped": amb, "reason": "every event was ambiguous"}
    days = df.groupby("date")["excess"].mean()
    sd = days.std(ddof=1) if len(days) > 2 else float("nan")
    t = float(days.mean() / (sd / math.sqrt(len(days)))) if sd and sd > 0 else None

    def part(d):
        if d.empty:
            return {"n_events": 0, "reason": "none on this side"}
        return {"n_events": int(len(d)), "hit_pct": round(float(d["hit"].mean()) * 100, 1),
                "no_memory_pct": round(float(d["p0"].mean()) * 100, 1),
                "excess_pp": round(float(d["excess"].mean()) * 100, 1),
                "gross_bps_per_trade": round(float(d["bps"].mean()), 2)}
    return {**part(df), "n_days": int(len(days)), "clustered_by": "session date, all names pooled",
            "t_days": None if t is None else round(t, 2),
            "timeouts": int((df["status"] == "timeout").sum()), "ambiguous_dropped": amb,
            "his_pattern_P": part(df[df["side"] == "P"]), "mirror_D": part(df[df["side"] == "D"])}


def yahoo(names, interval, period):
    import yfinance as yf
    got, dropped = {}, {}
    raw = yf.download(names, period=period, interval=interval, group_by="ticker", auto_adjust=False,
                      prepost=False, progress=False, threads=True)
    for nm in names:
        try:
            d = raw[nm].dropna(subset=["Open", "High", "Low", "Close"]).copy()
        except KeyError:
            dropped[nm] = "Yahoo returned no bars"
            continue
        if len(d) < 400:
            dropped[nm] = f"only {len(d)} bars"
            continue
        idx = d.index.tz_convert(ET) if d.index.tz is not None else d.index.tz_localize("UTC").tz_convert(ET)
        d = pd.DataFrame({"ts": idx, "open": d["Open"].to_numpy(), "high": d["High"].to_numpy(),
                          "low": d["Low"].to_numpy(), "close": d["Close"].to_numpy()}).reset_index(drop=True)
        mins = d["ts"].dt.hour * 60 + d["ts"].dt.minute
        d = d[(mins >= 570) & (mins < 960)].reset_index(drop=True)
        jump = (d["close"].pct_change().abs() > 0.35)
        if jump.any():
            dropped[nm] = "a bar-to-bar move above 35% (a split or a bad print) - not trusted"
            continue
        got[nm] = d
    return got, dropped


def run_sample(frames: dict, W: int, H: int, H_d: int):
    pooled: dict[str, list] = {q: [] for q in QUESTIONS}
    skipped: dict[str, int] = {}
    for nm, d in frames.items():
        res = scan(d, nm, W, H, H_d)
        for q in QUESTIONS:
            pooled[q] += res[q]
        for k, v in res["_skipped"][0].items():
            skipped[k] = skipped.get(k, 0) + v
    return pooled, skipped


def pack(pooled: dict, keep=None) -> dict:
    """Summaries for every question, optionally over a subset of the rows."""
    return {q: {"asks": QUESTIONS[q], **summarise([r for r in pooled[q] if keep is None or keep(r)])}
            for q in QUESTIONS}


def stability(rows: list) -> dict:
    """Halves and leave-one-month-out for one question: is it one stretch of the calendar?"""
    df = pd.DataFrame([r for r in rows if r["status"] != "ambiguous"])
    if len(df) < 20:
        return {"reason": f"only {len(df)} events - too few to split"}
    half = len(df) // 2
    loo = []
    for m in sorted(df["date"].str[:7].unique()):
        s = summarise(df[df["date"].str[:7] != m].to_dict("records"))
        loo.append({"month_left_out": m, "excess_pp": s["excess_pp"], "t_days": s["t_days"]})
    pick = lambda s: {k: s.get(k) for k in ("n_events", "n_days", "excess_pp", "t_days")}
    return {"first_half": {"to": df["date"].iloc[half - 1], **pick(summarise(df.iloc[:half].to_dict("records")))},
            "second_half": {"from": df["date"].iloc[half], **pick(summarise(df.iloc[half:].to_dict("records")))},
            "leave_one_month_out_weakest": min(loo, key=lambda r: r["excess_pp"]),
            "leave_one_month_out_strongest": max(loo, key=lambda r: r["excess_pp"]),
            "months_positive": int(sum(1 for _, x in df.groupby(df["date"].str[:7]) if x["excess"].mean() > 0)),
            "months": int(df["date"].str[:7].nunique())}


INDEX_FUNDS = ("SPY", "QQQ", "IWM")


def main():
    samples = {}
    spy = minute_to_pseudo_ohlc(load_minute_closes())
    span_from, span_to = str(spy["ts"].min().date()), str(spy["ts"].max().date())
    pooled, skipped = run_sample({"SPY": spy}, W=156, H=156, H_d=78)
    bats = load_bats("5")
    bats_pooled, _ = run_sample({"SPY": bats}, W=156, H=156, H_d=78)
    samples["spy_5m_2024_2025"] = {
        "what": "SPY 5-minute bars built from 1-minute closes (wicks slightly understated)",
        "from": span_from, "to": span_to, "sessions": int(spy["ts"].dt.date.nunique()), "names": ["SPY"],
        "questions": pack(pooled), "events_not_scored": skipped,
        "stability": {q: stability(pooled[q]) for q in QUESTIONS},
        "true_wicks_cross_check": {
            "what": "the same scan on a TradingView true-OHLC export", "sessions": int(bats["ts"].dt.date.nunique()),
            "from": str(bats["ts"].min().date()), "to": str(bats["ts"].max().date()), "questions": pack(bats_pooled)}}

    for key, interval, period, W, H, H_d, what in (
            ("his_names_5m_last_60d", "5m", "60d", 156, 156, 78, "Yahoo 5-minute bars, regular session"),
            ("his_names_1h_last_2y", "1h", "730d", 120, 120, 35, "Yahoo hourly bars, regular session")):
        try:
            frames, dropped = yahoo(NAMES, interval, period)
        except Exception as ex:                                  # a fetch failure is a stated zero
            samples[key] = {"what": what, "n_events": 0, "reason": f"fetch failed: {type(ex).__name__}: {ex}"}
            continue
        if not frames:
            samples[key] = {"what": what, "n_events": 0, "reason": "no name returned usable bars", "dropped": dropped}
            continue
        allts = pd.concat([d["ts"] for d in frames.values()])
        pooled, skipped = run_sample(frames, W, H, H_d)
        samples[key] = {"what": what, "from": str(allts.min().date()), "to": str(allts.max().date()),
                        "sessions": int(allts.dt.date.nunique()), "names": sorted(frames), "dropped": dropped,
                        "questions": pack(pooled), "events_not_scored": skipped,
                        "index_funds_only": pack(pooled, lambda r: r["name"] in INDEX_FUNDS),
                        "single_stocks_only": pack(pooled, lambda r: r["name"] not in INDEX_FUNDS)}
        if interval == "1h":
            # the one replication that shares no dates with the loud sample: SPY hourly OUTSIDE its span
            samples[key]["spy_outside_the_5m_span"] = {
                "what": f"SPY hourly, only dates before {span_from} or after {span_to}",
                "questions": pack(pooled, lambda r: r["name"] == "SPY" and not (span_from <= r["date"] <= span_to))}

    cells = [(s, q, v["questions"][q]) for s, v in samples.items() if "questions" in v for q in QUESTIONS]
    scored = [c for c in cells if c[2].get("t_days") is not None]
    side_looks = sum(1 for v in samples.values() for k in ("index_funds_only", "single_stocks_only",
                     "spy_outside_the_5m_span", "true_wicks_cross_check") if k in v) * len(QUESTIONS)
    looks = len(scored) + side_looks
    loud = [{"sample": s, "question": q, "t_days": r["t_days"], "excess_pp": r["excess_pp"]}
            for s, q, r in scored if abs(r["t_days"]) >= 2]

    def ex(sample, block, q):
        v = samples.get(sample, {})
        v = v.get(block, {}) if block != "questions" else v
        r = (v.get("questions", v) if block != "questions" else v.get("questions", {})).get(q, {})
        return r.get("excess_pp"), r.get("t_days"), r.get("n_events")

    verdict = {
        "rotation_back_to_the_zone_it_came_from": {
            "spy_5m_2024_2025": ex("spy_5m_2024_2025", "questions", "a_at_the_touch"),
            "spy_hourly_outside_that_span": ex("his_names_1h_last_2y", "spy_outside_the_5m_span", "a_at_the_touch"),
            "index_funds_5m_last_60d": ex("his_names_5m_last_60d", "index_funds_only", "a_at_the_touch"),
            "single_stocks_5m_last_60d": ex("his_names_5m_last_60d", "single_stocks_only", "a_at_the_touch"),
            "single_stocks_hourly_2y": ex("his_names_1h_last_2y", "single_stocks_only", "a_at_the_touch"),
            "reads_as": "(excess in points over the no-memory line, day-clustered t, events)"},
        "his_sentence_stop_at_the_days_low": {
            s: ex(s, "questions", "c_his_sentence") for s in samples},
        "break_or_reject_at_the_prior_extreme": {
            s: ex(s, "questions", "d_at_the_prior_extreme") for s in samples},
        "status": "DESCRIPTION ONLY - not through edge-refute, nothing registered, no position follows from it",
    }
    report = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "frame": {"premium_top_pct": PREM * 100, "equilibrium_half_band_pct": EQ_HALF * 100,
                  "as_of_each_bar": True, "windows": {"5m": 156, "1h": 120}},
        "benchmark": "a walk with no memory: P(upper first) = (entry - lower) / (upper - lower)",
        "samples": samples,
        "primary_cells_scored": len(scored),
        "looks_including_subsets": looks,
        "chance_of_one_t2_by_luck_primary": round(1 - (1 - 0.0455) ** len(scored), 2) if scored else None,
        "chance_of_one_t2_by_luck_all_looks": round(1 - (1 - 0.0455) ** looks, 2) if looks else None,
        "cells_with_abs_t_2_or_more": loud,
        "verdict": verdict,
    }
    OUT.parent.mkdir(exist_ok=True)
    atomic_json(OUT, report, indent=1)

    def line(tag, r):
        if not r.get("n_events"):
            return f"   {tag:34s} n=0 ({r.get('reason')})"
        P, D = r["his_pattern_P"], r["mirror_D"]
        return (f"   {tag:34s} n={r['n_events']:4d} days={r['n_days']:4d}  {r['hit_pct']:5.1f}% vs {r['no_memory_pct']:5.1f}%"
                f"  excess {r['excess_pp']:+5.1f}pp  t={r['t_days']}  | P {P.get('excess_pp')} D {D.get('excess_pp')}")

    for s, v in samples.items():
        print(f"\n== {s}: {v.get('what')} [{v.get('from')} -> {v.get('to')}, {v.get('sessions')} sessions]")
        if "questions" not in v:
            print("   ", v.get("reason"))
            continue
        if v.get("dropped"):
            print("   dropped:", sorted(v["dropped"]))
        for q, r in v["questions"].items():
            print(line(q, r))
        for block in ("index_funds_only", "single_stocks_only", "spy_outside_the_5m_span"):
            if block in v:
                qs = v[block].get("questions", v[block])
                for q in ("a_at_the_touch", "c_his_sentence"):
                    print(line(f"{block[:22]}:{q[:10]}", qs[q]))
        if "stability" in v:
            for q in ("a_at_the_touch", "b_after_a_bounce_bar"):
                st = v["stability"][q]
                print(f"   stability {q}: halves {st['first_half']['excess_pp']} -> {st['second_half']['excess_pp']}pp, "
                      f"months positive {st['months_positive']}/{st['months']}, "
                      f"weakest leave-one-out {st['leave_one_month_out_weakest']}")
    print(f"\nprimary cells {len(scored)}, all looks {looks}; luck of one |t|>=2: "
          f"{report['chance_of_one_t2_by_luck_primary']} / {report['chance_of_one_t2_by_luck_all_looks']}")
    print("loud:", loud)
    print("wrote", OUT)


if __name__ == "__main__":
    main()

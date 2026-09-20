#!/opt/anaconda3/bin/python
"""bos_followthrough_study.py - "after a break of structure, trade in that direction: high probability".

Anupam sent an SMC teaching card on 2026-09-19 (X, @nsinghal211, "SMC Trading Series day 3"): price breaks the
previous important high (low), that is a bullish (bearish) BOS, and trading WITH it is a high-probability setup.
IE Pro ONE already draws these breaks. This counts what they have been worth.

PRE-DECLARED before any number was seen. Nothing below was tuned after a run.
  structure  exactly IE Pro ONE's: 5/5 pivots, a swing is known 5 bars late; a CLOSE through the last confirmed
             swing high (low) is the break. BOS = a break WITH the standing structure (or the first one);
             CHoCH = a break AGAINST it. The card's claim is about BOS; CHoCH is scored beside it.
  Q-f1  does it keep going?   enter the next bar's open; +1.5 ATR in the break's direction, or -1.5 ATR
                              against it, first? A walk with no memory says 50%.
  Q-f2  the trade on the card enter the next open, stop at the swing that defines the structure (the last
                              confirmed low for a long) when it sits within 3 ATR, target twice that distance.
                              No memory says 33.3%, which is also where 2:1 breaks even.
  mirror     bullish and bearish breaks are pooled and also shown apart: if a rising tape is doing the work,
             the bulls look good and the bears look bad by the same amount.
  one event at a time per name; timeouts count at their fractional position; both barriers in one bar =
  ambiguous, dropped and counted; n = independent SESSION DATES, all names on a date are one cluster.
A description, not a strategy. Registers no variant.
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atomicio import atomic_json                                     # noqa: E402
from data_utils import atr, load_minute_closes, minute_to_pseudo_ohlc  # noqa: E402
from zone_rotation_study import NAMES, first_passage, yahoo          # noqa: E402

OUT = HERE.parent / "results" / "bos_followthrough_study.json"
INDEX_FUNDS = ("SPY", "QQQ", "IWM")
PIV, K_SYM, MAX_STOP_ATR, RR = 5, 1.5, 3.0, 2.0


def breaks(h, l, c):
    """[(bar, +1/-1, 'BOS'|'CHoCH', lastSL, lastSH)] - the Pine's state machine, in its order."""
    out, lastSH, lastSL, trend = [], None, None, 0
    for i in range(len(c)):
        if i >= 2 * PIV:
            k = i - PIV
            wh, wl = h[k - PIV:i + 1], l[k - PIV:i + 1]
            if h[k] == wh.max() and (wh == h[k]).sum() == 1:
                lastSH = h[k]
            if l[k] == wl.min() and (wl == l[k]).sum() == 1:
                lastSL = l[k]
        if i == 0:
            continue
        if lastSH is not None and c[i] > lastSH and c[i - 1] <= lastSH:
            out.append((i, 1, "CHoCH" if trend == -1 else "BOS", lastSL, lastSH))
            trend = 1
        if lastSL is not None and c[i] < lastSL and c[i - 1] >= lastSL:
            out.append((i, -1, "CHoCH" if trend == 1 else "BOS", lastSL, lastSH))
            trend = -1
    return out


def scan(df: pd.DataFrame, name: str, H: int) -> dict:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a14, n = atr(df).to_numpy(), len(df)
    date = df["ts"].dt.date.to_numpy()
    rows = {"f1_keeps_going": [], "f2_the_trade_on_the_card": []}
    skipped = {"structure_stop_missing_or_beyond_3_atr": 0, "gap_past_a_barrier": 0}
    busy = -1

    def record(q, i, dirn, kind, e, up, dn, res):
        y, px, _, status = res
        row = {"name": name, "date": str(date[i]), "dir": dirn, "kind": kind, "status": status}
        if y is not None:
            p_up = (e - dn) / (up - dn)
            row["hit"] = y if dirn > 0 else 1.0 - y
            row["p0"] = p_up if dirn > 0 else 1.0 - p_up
            row["excess"] = row["hit"] - row["p0"]
            row["bps"] = dirn * (px - e) / e * 1e4
        rows[q].append(row)

    for i, dirn, kind, sl, sh in breaks(h, l, c):
        if i <= busy or i + 1 >= n or not a14[i] > 0:
            continue
        e, a, end = o[i + 1], a14[i], min(n, i + 1 + H)
        res = first_passage(o, h, l, c, i + 1, end, e + K_SYM * a, e - K_SYM * a)
        record("f1_keeps_going", i, dirn, kind, e, e + K_SYM * a, e - K_SYM * a, res)
        busy = res[2]
        swing = sl if dirn > 0 else sh
        dist = None if swing is None else dirn * (e - swing)
        if dist is None or dist <= 0 or dist > MAX_STOP_ATR * a:
            skipped["structure_stop_missing_or_beyond_3_atr"] += 1
            continue
        tgt = e + dirn * RR * dist
        up, dn = (tgt, swing) if dirn > 0 else (swing, tgt)
        record("f2_the_trade_on_the_card", i, dirn, kind, e, up, dn, first_passage(o, h, l, c, i + 1, end, up, dn))
    return {"rows": rows, "skipped": skipped}


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
            "gross_bps_per_trade": round(float(df["bps"].mean()), 2)}


def pack(pooled: dict, keep=lambda r: True) -> dict:
    out = {}
    for q, rows in pooled.items():
        rows = [r for r in rows if keep(r)]
        out[q] = {"BOS_all": summ([r for r in rows if r["kind"] == "BOS"]),
                  "BOS_bullish": summ([r for r in rows if r["kind"] == "BOS" and r["dir"] > 0]),
                  "BOS_bearish": summ([r for r in rows if r["kind"] == "BOS" and r["dir"] < 0]),
                  "CHoCH_all": summ([r for r in rows if r["kind"] == "CHoCH"])}
    return out


def run(frames: dict, H: int):
    pooled = {"f1_keeps_going": [], "f2_the_trade_on_the_card": []}
    skipped: dict[str, int] = {}
    for nm, d in frames.items():
        r = scan(d, nm, H)
        for q in pooled:
            pooled[q] += r["rows"][q]
        for k, v in r["skipped"].items():
            skipped[k] = skipped.get(k, 0) + v
    return pooled, skipped


def main():
    samples = {}
    spy = minute_to_pseudo_ohlc(load_minute_closes())
    pooled, skipped = run({"SPY": spy}, 156)
    samples["spy_5m_2024_2025"] = {"what": "SPY 5-minute bars built from 1-minute closes", "sessions": int(spy["ts"].dt.date.nunique()),
                                   "from": str(spy["ts"].min().date()), "to": str(spy["ts"].max().date()),
                                   "questions": pack(pooled), "events_not_scored": skipped}
    for key, interval, period, H, what in (("his_names_5m_last_60d", "5m", "60d", 156, "Yahoo 5-minute bars, regular session"),
                                           ("his_names_1h_last_2y", "1h", "730d", 120, "Yahoo hourly bars, regular session")):
        try:
            frames, dropped = yahoo(NAMES, interval, period)
            pooled, skipped = run(frames, H)
            allts = pd.concat([d["ts"] for d in frames.values()])
            samples[key] = {"what": what, "sessions": int(allts.dt.date.nunique()), "from": str(allts.min().date()),
                            "to": str(allts.max().date()), "names": sorted(frames), "dropped": dropped,
                            "questions": pack(pooled), "index_funds_only": pack(pooled, lambda r: r["name"] in INDEX_FUNDS),
                            "single_stocks_only": pack(pooled, lambda r: r["name"] not in INDEX_FUNDS),
                            "events_not_scored": skipped}
        except Exception as ex:                                    # a fetch failure is a stated zero
            samples[key] = {"n_events": 0, "reason": f"fetch failed: {type(ex).__name__}: {ex}"}
    looks = sum(8 * (1 + 2 * ("index_funds_only" in v)) for v in samples.values() if "questions" in v)
    report = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
              "rules": {"pivot": PIV, "symmetric_barrier_atr": K_SYM, "max_structure_stop_atr": MAX_STOP_ATR, "reward_to_risk": RR},
              "samples": samples, "looks_in_this_file": looks, "looks_today_all_files": looks + 72,
              "chance_of_one_t2_by_luck_all_looks": round(1 - (1 - 0.0455) ** (looks + 72), 3),
              "status": "DESCRIPTION ONLY - not through edge-refute, nothing registered, no position follows from it"}
    OUT.parent.mkdir(exist_ok=True)
    atomic_json(OUT, report, indent=1)

    def line(tag, r):
        if not r.get("n_events"):
            return f"      {tag:14s} n=0 ({r.get('reason')})"
        return (f"      {tag:14s} n={r['n_events']:5d} days={r['n_days']:4d}  {r['hit_pct']:5.1f}% vs {r['no_memory_pct']:5.1f}%"
                f"  excess {r['excess_pp']:+5.1f}pp  t={r['t_days']}  gross {r['gross_bps_per_trade']:+.2f}bps")
    for s, v in samples.items():
        print(f"\n== {s} [{v.get('from')} -> {v.get('to')}, {v.get('sessions')} sessions]")
        if "questions" not in v:
            print("   ", v.get("reason"))
            continue
        for block in ("questions", "index_funds_only", "single_stocks_only"):
            if block in v:
                print(f"   -- {block}")
                for q, cells in v[block].items():
                    print(f"    {q}")
                    for tag, r in cells.items():
                        print(line(tag, r))
        print("   not scored:", v["events_not_scored"])
    print(f"\nlooks here {looks}; today, all files {looks + 72}: chance of one |t|>=2 by luck {report['chance_of_one_t2_by_luck_all_looks']}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

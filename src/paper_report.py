#!/opt/anaconda3/bin/python
"""PTR-001 weekly report (Sunday). PAPER ONLY. Reads data/paper/*.csv; writes two files and nothing else:
  results/PAPER_WEEKLY_<date>.md            PUBLIC: percent only; before the gate it prints counts and data health, NO profit number
  ~/Desktop/Trading/PAPER_VS_LIVE.md        PRIVATE: the paper track beside his live trades; never committed, never in this repo

The readout is PREREG_IE_PRO_PAPER.md section 9, written down before any counted session exists:
  gate     >= 60 counted sessions AND >= 100 filled trades. Before it: n, trades, skips, data gaps, "not yet readable".
  set      the first 60 counted sessions (extended session by session only if they hold fewer than 100 trades), halves by order
  stats    per-trade net %, win rate BESIDE the mean's sign and size, avg loss / avg win, worst loss, fees share, the same per half,
           day-clustered 95% bootstrap interval of mean session net (10,000 resamples of sessions, fixed seed), $0.65 fee sensitivity,
           entry-premium split (ask < / >= $0.20, descriptive), count of trades larger than the quoted ask size
  twin     paired per-trade difference (trade minus mirror twin), session-clustered interval, point estimates for long and short apart
  PASS     interval of mean session net excludes zero upward AND both halves positive AND twin difference interval excludes zero
           upward AND the twin difference is positive for longs and for shorts. Otherwise FAIL: no edge shown.
  KILL     cumulative net <= -$1,500 retires the variant (the runner enforces it; this report states it).
A PASS is never a trade instruction.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(HERE))
import atomicio  # noqa: E402

PAPER = LAB / "data" / "paper"
CAPITAL, KILL_NET = 5000.0, -1500.0
GATE_SESSIONS, GATE_TRADES = 60, 100
BOOT_N, BOOT_SEED = 10_000, 20261009
PRIVATE = Path.home() / "Desktop" / "Trading" / "PAPER_VS_LIVE.md"


def _num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def read(name: str) -> pd.DataFrame:
    p = PAPER / name
    return pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists() else pd.DataFrame()


def boot_ci(vals: np.ndarray, weights: np.ndarray | None = None) -> tuple[float, float, float]:
    """Mean and day-clustered 95% interval. vals = one number per session; with weights, the ratio sum(vals)/sum(weights)."""
    rng = np.random.default_rng(BOOT_SEED)
    n = len(vals)
    idx = rng.integers(0, n, size=(BOOT_N, n))
    if weights is None:
        m = vals[idx].mean(axis=1)
        point = vals.mean()
    else:
        den = weights[idx].sum(axis=1)
        m = np.where(den > 0, vals[idx].sum(axis=1) / np.where(den > 0, den, 1), np.nan)
        point = vals.sum() / weights.sum()
    lo, hi = np.nanpercentile(m, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def split_stats(t: pd.DataFrame) -> dict:
    w, l = t[t["net"] > 0], t[t["net"] <= 0]
    return dict(n=len(t), mean_pct=100 * t["net_pct"].mean(), median_pct=100 * t["net_pct"].median(), win_rate=100 * len(w) / len(t),
                avg_loss_over_avg_win=(abs(l["net_pct"].mean()) / w["net_pct"].mean()) if len(w) and len(l) and w["net_pct"].mean() else float("nan"),
                worst_pct=100 * t["net_pct"].min())


def readout(trades: pd.DataFrame, sess: pd.DataFrame) -> dict:
    """trades: COUNTED rows; sess: COUNTED sessions (ordered by date). Returns the section 9 numbers and the PASS/FAIL verdict."""
    sess = sess.sort_values("session").reset_index(drop=True)
    t = trades.copy()
    n_sess = GATE_SESSIONS
    while n_sess < len(sess) and t[t["session"].isin(sess["session"][:n_sess])].shape[0] < GATE_TRADES:
        n_sess += 1
    use = list(sess["session"][:n_sess])
    t = t[t["session"].isin(use)].copy()
    per = t.groupby("session")["net"].sum().reindex(use, fill_value=0.0)
    s_pct = (per / CAPITAL * 100).to_numpy()
    point, lo, hi = boot_ci(s_pct)
    half = n_sess // 2
    halves = [per.iloc[:half].mean() / CAPITAL * 100, per.iloc[half:].mean() / CAPITAL * 100]
    fees = 2 * 0.36 * t["contracts"].sum()
    out = dict(n_sessions=n_sess, n_trades=len(t), overall=split_stats(t), session_mean_pct_of_C=point, session_ci=(lo, hi),
               halves_pct_of_C=halves, fees_share_of_abs_gross=fees / t["gross"].abs().sum() if t["gross"].abs().sum() else float("nan"),
               fee065_mean_pct=100 * t["net_pct_fee065"].mean(),
               first_half=split_stats(t[t["session"].isin(use[:half])]), second_half=split_stats(t[t["session"].isin(use[half:])]),
               premium_lt_020=100 * t[t["ask_entry"] < 0.20]["net_pct"].mean(), premium_ge_020=100 * t[t["ask_entry"] >= 0.20]["net_pct"].mean(),
               n_lt_020=int((t["ask_entry"] < 0.20).sum()), size_exceeds_ask_size=int((t["size_exceeds_ask_size"] == "True").sum()))
    pair = t[(t["twin_status"] == "OK")].copy()
    pair["diff"] = pair["net_pct"] - pair["twin_net_pct"]
    ds = pair.groupby("session")["diff"].agg(["sum", "count"]).reindex(use, fill_value=0.0)
    if ds["count"].sum() > 0:
        dp, dlo, dhi = boot_ci(ds["sum"].to_numpy(), ds["count"].to_numpy().astype(float))
        by_side = {s: 100 * pair[pair["side"] == s]["diff"].mean() for s in ("long", "short")}
        out.update(twin_pairs=len(pair), twin_unfillable=int((t["twin_status"] != "OK").sum()), twin_diff_pct=100 * dp,
                   twin_ci=(100 * dlo, 100 * dhi), twin_by_side=by_side)
    else:
        dlo = -1.0
        by_side = {"long": float("nan"), "short": float("nan")}
    cond = [lo > 0, halves[0] > 0 and halves[1] > 0, dlo > 0, by_side["long"] > 0 and by_side["short"] > 0]
    out["conditions"] = dict(zip(["session interval excludes 0 upward", "both halves positive", "twin interval excludes 0 upward",
                                  "twin difference positive for longs and shorts"], [bool(c) for c in cond]))
    out["verdict"] = "PASS" if all(cond) else "FAIL: no edge shown"
    return out


def fmt_pct(x: float) -> str:
    return "n/a" if x != x else f"{x:+.2f}%"


def public_md(day: str, sess: pd.DataFrame, trades: pd.DataFrame, skips: pd.DataFrame, hb: pd.DataFrame, ro: dict | None,
              gate_note: str) -> str:
    counted = sess[sess["status"] == "COUNTED"] if len(sess) else sess
    gaps = sess[sess["status"] == "DATA_GAP"] if len(sess) else sess
    L = [f"# PTR-001 paper trader - week ending {day}", "",
         "Paper only. A forward description of the IE Pro rule on recorded data, not a claimed edge; prior: no edge. "
         "Spec `PREREG_IE_PRO_PAPER.md`. Percent only.", "",
         "## Where it stands",
         f"- counted sessions (n, clustered by session date): **{len(counted)}** of {GATE_SESSIONS} needed",
         f"- filled trades: **{len(trades)}** of {GATE_TRADES} needed",
         f"- DATA-GAP sessions (logged, not counted): {len(gaps)}" + (f" ({', '.join(gaps['session'])})" if len(gaps) else ""),
         f"- skips by reason: {skips['reason'].value_counts().to_dict() if len(skips) else 'none'}"]
    if len(hb):
        last = hb.iloc[-1]
        bad = hb[hb["status"].isin(["REFUSED", "ERROR"])]
        L.append(f"- runner heartbeat: last run {last['run_at_et']} ({last['status']}); REFUSED/ERROR rows in the book: {len(bad)}")
    else:
        L.append("- runner heartbeat: **no rows yet** (the first counted session is expected on 2026-10-12)")
    if (PAPER / "RETIRED.json").exists():
        L.append("- **KILL line reached: the variant is RETIRED; signals and twins keep being recorded.**")
    L += ["", "## Readout"]
    if ro is None:
        L += [f"**Not yet readable.** {gate_note} No profit number is shown before the gate (pre-registered)."]
    else:
        o = ro["overall"]
        L += [f"Gate met: {ro['n_sessions']} sessions, {ro['n_trades']} trades. **Verdict: {ro['verdict']}.** "
              "A PASS is never a trade instruction.", "",
              f"- per trade, net of fees: mean {fmt_pct(o['mean_pct'])}, median {fmt_pct(o['median_pct'])}; win rate {o['win_rate']:.1f}% "
              f"(read beside the mean's sign); average loss / average win {o['avg_loss_over_avg_win']:.2f}; worst {fmt_pct(o['worst_pct'])}",
              f"- mean session net: {fmt_pct(ro['session_mean_pct_of_C'])} of capital, day-clustered 95% interval "
              f"[{fmt_pct(ro['session_ci'][0])}, {fmt_pct(ro['session_ci'][1])}]",
              f"- first half {fmt_pct(ro['halves_pct_of_C'][0])}, second half {fmt_pct(ro['halves_pct_of_C'][1])} of capital per session",
              f"- fees: {100 * ro['fees_share_of_abs_gross']:.1f}% of absolute gross; at $0.65 a side the per-trade mean is {fmt_pct(ro['fee065_mean_pct'])}",
              f"- entry ask under $0.20 ({ro['n_lt_020']} trades) {fmt_pct(ro['premium_lt_020'])}, at or over {fmt_pct(ro['premium_ge_020'])} (descriptive)",
              f"- trades larger than the quoted ask size: {ro['size_exceeds_ask_size']}"]
        if "twin_diff_pct" in ro:
            L += [f"- vs the mirror twin ({ro['twin_pairs']} pairs, {ro['twin_unfillable']} twins unfillable): mean difference {fmt_pct(ro['twin_diff_pct'])} per trade, "
                  f"interval [{fmt_pct(ro['twin_ci'][0])}, {fmt_pct(ro['twin_ci'][1])}]; longs {fmt_pct(ro['twin_by_side']['long'])}, shorts {fmt_pct(ro['twin_by_side']['short'])}"]
        L += ["", "Conditions: " + "; ".join(f"{k}: {'yes' if v else 'no'}" for k, v in ro["conditions"].items())]
    L += ["", "No post-hoc slice by grade, hour or side is a finding. The only splits are those above."]
    return "\n".join(L) + "\n"


def private_md(day: str, sess: pd.DataFrame, trades: pd.DataFrame, ro: dict | None) -> str:
    counted = sess[sess["status"] == "COUNTED"] if len(sess) else sess
    L = [f"# Paper vs live - private ({day})", "", "PRIVATE. Never commit this file. The paper track is simulated, on recorded data; "
         "it is not THE ACCOUNT and not advice.", "", "## Paper track (PTR-001, IE Pro)",
         f"- counted sessions {len(counted)}, filled trades {len(trades)} (gate: {GATE_SESSIONS} sessions and {GATE_TRADES} trades)"]
    if ro is None:
        L.append("- not yet readable: no dollar or percent result is shown before the gate.")
    else:
        net = trades[trades["session"].isin(list(counted["session"][:ro["n_sessions"]]))]["net"].sum()
        L.append(f"- paper net over the readout set: ${net:,.2f} on ${CAPITAL:,.0f} capital; verdict {ro['verdict']}")
    L += ["", "## Live side", "- **Not supplied.** Give me a file of his closed live trades (date, instrument, side, entry, exit, P&L) at "
          "`~/Desktop/Trading/live_trades_for_comparison.csv`, or tell me to read them from his ledger, and this section will line the two up. "
          "I will not read his statements without being told to."]
    return "\n".join(L) + "\n"


def verify_pin() -> None:
    ap = PAPER / "APPROVED.json"
    if ap.exists():
        pin = json.loads(ap.read_text()).get("report_sha256")
        if pin and pin != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
            raise SystemExit("REFUSED: paper_report.py differs from the hash pinned in APPROVED.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    verify_pin()
    sess, trades, skips, hb = read("sessions.csv"), read("trades.csv"), read("skips.csv"), read("heartbeat.csv")
    if len(trades):
        trades = _num(trades[trades["label"] == "COUNTED"].copy(), ["net", "net_pct", "net_pct_fee065", "gross", "contracts", "ask_entry", "twin_net_pct"])
    cs = sess[sess["status"] == "COUNTED"] if len(sess) else sess
    ro, note = None, f"{len(cs)} counted sessions and {len(trades)} trades so far."
    if len(cs) >= GATE_SESSIONS and len(trades) >= GATE_TRADES:
        ro = readout(trades, cs)
    out = LAB / "results" / f"PAPER_WEEKLY_{a.date}.md"
    atomicio.atomic_write_text(str(out), public_md(a.date, sess, trades, skips, hb, ro, note))
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    atomicio.atomic_write_text(str(PRIVATE), private_md(a.date, sess, trades, ro))
    print(f"wrote {out} and {PRIVATE}: {note}" + (f" verdict {ro['verdict']}" if ro else " (not yet readable)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

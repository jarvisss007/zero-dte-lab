#!/opt/anaconda3/bin/python
"""naked_selling_study.py - what selling premium NAKED would have done, on this firm's own priced straddles.

Anupam, 2026-09-23: "why no naked options?" then "give me the best naked options trades". EV-3 blocks
naked premium ("quiet samples underwrite short-vol blowups") and only he can unblock it. This measures
the question instead of arguing it. DESCRIPTION ONLY - registers nothing, costs no trial.

Two books of REAL entry prices and SETTLED outcomes, none of them a backtest:
  A  stock-radar/agent/options_refusals.csv   straddles the options desk priced and REFUSED to buy,
                                              scored at expiry by options_refusal_shadow.py
  B  zero-dte-lab/results/straddle_test.csv   SPY 0DTE ATM straddles priced at the first snapshot
                                              of each trigger session, scored at the close

THE MIRROR. On each structure the naked SELLER's P&L is exactly minus the buyer's: collect the debit,
pay out the realized move. Priced at the buyer's ASK, which FLATTERS the seller (a seller collects the
bid). Every number below is therefore a ceiling on what naked selling earned.

PRE-DECLARED, before any number was seen:
  the tail  worst single structure, worst five, and the worst one as a share of everything ever
            collected - because a strategy that wins most days and loses one is judged by that one
  ruin      the account size at which ONE worst-case event, at N contracts per structure, exceeds it
  n         independent SESSION DATES, never rows
"""
from __future__ import annotations
import csv, json, math, os, statistics as st, sys, datetime as dt, collections
H = os.path.expanduser("~")
sys.path.insert(0, f"{H}/zero-dte-lab/src")
from atomicio import atomic_json
OUT = f"{H}/zero-dte-lab/results/naked_selling_study.json"

def f(x):
    try: return float(x)
    except: return None

def study(rows, label, key_date):
    """rows: list of (date, seller_pnl_per_share, premium_collected)."""
    if not rows: return {"n": 0, "reason": "no scored rows"}
    pnl = [p for _, p, _ in rows]; prem = [c for _, _, c in rows]
    days = collections.defaultdict(list)
    for d, p, _ in rows: days[d].append(p)
    dm = [st.mean(v) for v in days.values()]
    t = st.mean(dm) / (st.stdev(dm) / math.sqrt(len(dm))) if len(dm) > 2 and st.stdev(dm) > 0 else None
    worst = sorted(pnl)[:5]
    collected, paid = sum(prem), sum(max(0.0, -p) for p in pnl) + sum(max(0.0, c - p - c) for p, c in zip(pnl, prem))
    net = sum(pnl)
    return {"label": label, "n_structures": len(pnl), "n_days": len(days), "clustered_by": "session date",
            "seller_win_pct": round(100 * sum(1 for p in pnl if p > 0) / len(pnl), 1),
            "seller_mean_per_share": round(st.mean(pnl), 3), "seller_median_per_share": round(st.median(pnl), 3),
            "t_days": None if t is None else round(t, 2),
            "premium_collected_total": round(collected, 2), "net_after_payouts": round(net, 2),
            "keep_ratio_pct": round(100 * net / collected, 1) if collected else None,
            "worst_single": round(worst[0], 3), "worst_five": [round(x, 3) for x in worst],
            "worst_single_as_pct_of_all_premium_ever_collected": round(100 * -worst[0] / collected, 1) if collected and worst[0] < 0 else 0,
            "worst_single_vs_mean_win": round(-worst[0] / st.mean([p for p in pnl if p > 0]), 1) if any(p > 0 for p in pnl) and worst[0] < 0 else None,
            "note": "priced at the buyer's ASK - a ceiling for the seller"}

# ---- A: the desk's refused straddles. FOUND ON THE FIRST RUN: the 117 rows with an outcome are all
# `void` from the pre-OPT-020 format (no strike, no debit, no realized move); the 146 rows that ARE
# priced all expire 2026-10-09 -> 10-23. This dataset can answer nothing until October. Reported as
# a stated zero, not skipped.
A = []
A_rows = list(csv.DictReader(open(f"{H}/stock-radar/agent/options_refusals.csv")))
A_priced = [r for r in A_rows if (r.get("debit") or "").strip() and (r.get("strike") or "").strip()]
A_status = {"n": 0, "reason": (f"{sum(1 for r in A_rows if r.get('outcome'))} rows carry an outcome and every one is 'void' "
            f"(pre-OPT-020 rows with no price); the {len(A_priced)} PRICED refusals expire "
            f"{min(r['expiry'] for r in A_priced)} -> {max(r['expiry'] for r in A_priced)} and none has settled. "
            "Re-run after 2026-10-23.")}
# ---- B: SPY 0DTE straddles, and the DAY is the unit
B, Bday = [], collections.defaultdict(list)
for r in csv.DictReader(open(f"{H}/zero-dte-lab/results/straddle_test.csv")):
    cost, pay, rm, spot = f(r.get("cost_ask")), f(r.get("payoff")), f(r.get("realized_move_pct")), f(r.get("spot"))
    if cost is None or pay is None or cost <= 0: continue
    B.append((r["date"][:10], cost - pay, cost)); Bday[r["date"][:10]].append((cost - pay, cost, rm, spot))
resA = A_status
resB = study(B, "SPY 0DTE ATM straddles, first snapshot -> close", "date")
days = [(d, st.mean(x[0] for x in v), st.mean(x[1] for x in v),
         st.mean(x[2] for x in v if x[2] is not None) if any(x[2] is not None for x in v) else None,
         st.mean(x[3] for x in v if x[3]) if any(x[3] for x in v) else None) for d, v in sorted(Bday.items())]
dp = [x[1] for x in days]; wins = [x for x in dp if x > 0]
avg_prem = st.mean(x[2] for x in days); avg_spot = st.mean(x[4] for x in days if x[4]) if any(x[4] for x in days) else None
# ---- how quiet was the sample? against every SPY session on file
spy = [float(r.get("Close") or r.get("close")) for r in csv.DictReader(open(f"{H}/spy-trading/data/spy_daily.csv")) if (r.get("Close") or r.get("close"))]
mv = sorted(abs(spy[i] / spy[i - 1] - 1) * 100 for i in range(1, len(spy)))
q = lambda pct: mv[int(pct * len(mv))]
p2 = sum(1 for m in mv if m >= 2) / len(mv)
sample_max = max(x[3] for x in days if x[3] is not None)
# ---- the counterfactual: the SAME trade on a day the sample never saw, at the sample's own premium and price
def seller_on(move_pct):
    payout = move_pct / 100 * avg_spot          # an ATM straddle pays about the whole move
    pnl = avg_prem - payout
    return {"spy_move_pct": round(move_pct, 2), "payout_per_share": round(payout, 2), "seller_pnl_per_share": round(pnl, 2),
            "average_winning_days_erased": round(-pnl / st.mean(wins), 1)}
resB.update({
  "DAY_LEVEL_the_true_n": {"sessions": len(days), "days_seller_won": sum(1 for x in dp if x > 0), "mean_day": round(st.mean(dp), 3),
      "worst_day": round(min(dp), 3), "worst_day_vs_avg_winning_day": round(-min(dp) / st.mean(wins), 1),
      "avg_premium_collected_per_share": round(avg_prem, 2), "avg_spy_level": round(avg_spot, 1) if avg_spot else None},
  "HOW_QUIET_WAS_THE_SAMPLE": {"sample_mean_realized_move_pct": round(st.mean(x[3] for x in days if x[3] is not None), 2),
      "sample_MAX_realized_move_pct": round(sample_max, 2), "spy_history_sessions": len(mv),
      "spy_history_mean_move_pct": round(st.mean(mv), 2), "spy_95th_pct_move": round(q(0.95), 2), "spy_99th_pct_move": round(q(0.99), 2),
      "spy_max_move_pct": round(max(mv), 2), "share_of_history_days_moving_2pct_or_more": round(100 * p2, 1),
      "chance_of_drawing_17_days_with_no_2pct_move": round(100 * (1 - p2) ** 17, 1),
      "verdict": "the sample's LARGEST day was barely above SPY's AVERAGE day; not one of the 17 was a normal-sized down day"},
  "THE_TAIL_THE_SAMPLE_NEVER_SAW": {"a_95th_percentile_day (about once every 3 weeks)": seller_on(q(0.95)),
      "a_99th_percentile_day (about 2-3 a year)": seller_on(q(0.99)), "the_worst_day_on_file": seller_on(max(mv))}})
# ---- the ruin table: one worst event at N contracts vs the account
def ruin(res, sizes=(1, 5, 10, 25)):
    if not res.get("n_structures"): return {}
    w = -res["worst_single"] * 100          # per contract, dollars
    return {f"{n}_contracts": {"worst_event_usd": round(w * n), "mean_win_usd": round(res["seller_mean_per_share"] * 100 * n, 2),
                               "events_of_mean_income_erased": round(w / max(1e-9, res["seller_mean_per_share"] * 100), 1) if res["seller_mean_per_share"] > 0 else "income is negative"}
            for n in sizes}
rep = {"generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
       "status": "DESCRIPTION ONLY - EV-3 stays as Anupam ruled it; this registers nothing and takes no position",
       "A_refused_straddles": resA, "A_ruin": ruin(resA), "B_spy_0dte": resB, "B_ruin": ruin(resB)}
os.makedirs(os.path.dirname(OUT), exist_ok=True); atomic_json(OUT, rep, indent=1)
for k, r in (("A", resA), ("B", resB)):
    print(f"\n  {k}: {r.get('label', 'the desk refusal book')}")
    if not r.get("n_structures"): print("    ", r.get("reason")); continue
    print(f"    n {r['n_structures']} structures on {r['n_days']} days · seller wins {r['seller_win_pct']}% · mean {r['seller_mean_per_share']:+.3f}/sh · median {r['seller_median_per_share']:+.3f} · t {r['t_days']}")
    print(f"    collected {r['premium_collected_total']:,.2f} · kept after payouts {r['net_after_payouts']:+,.2f} ({r['keep_ratio_pct']}%)")
    print(f"    worst single {r['worst_single']:+.3f}/sh = {r['worst_single_as_pct_of_all_premium_ever_collected']}% of ALL premium ever collected · = {r['worst_single_vs_mean_win']}x the average win")
    print(f"    worst five: {r['worst_five']}")
D, Q, T = resB["DAY_LEVEL_the_true_n"], resB["HOW_QUIET_WAS_THE_SAMPLE"], resB["THE_TAIL_THE_SAMPLE_NEVER_SAW"]
print(f"\n  THE DAY IS THE UNIT: {D['sessions']} sessions · seller won {D['days_seller_won']} · mean day {D['mean_day']:+.3f}/sh · worst day {D['worst_day']:+.3f} ({D['worst_day_vs_avg_winning_day']}x an average winning day)")
print(f"  HOW QUIET: sample max move {Q['sample_MAX_realized_move_pct']}% vs SPY history mean {Q['spy_history_mean_move_pct']}% · 95th {Q['spy_95th_pct_move']}% · 99th {Q['spy_99th_pct_move']}% · {Q['share_of_history_days_moving_2pct_or_more']}% of days move >= 2% · chance of 17 days without one: {Q['chance_of_drawing_17_days_with_no_2pct_move']}%")
for k, v in T.items():
    print(f"  {k}: SPY {v['spy_move_pct']}% -> seller {v['seller_pnl_per_share']:+.2f}/sh = {v['average_winning_days_erased']} average winning days erased")
print("\n  wrote", OUT)

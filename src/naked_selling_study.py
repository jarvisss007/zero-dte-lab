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

2026-09-29 REFRESH (data range only). `--out` writes a NEW file. Block B read results/straddle_test.csv, which stopped at
2026-08-14 (17 sessions) because straddle_test.py takes its closes from a 60-day 5m cache that ends there.
`--build-straddle` re-runs straddle_test.run() UNCHANGED over every recorded session into a NEW CSV (`--straddle-csv`);
the Block A/B code below it is untouched. Two things in the quiet block were hard-coded to the old sample and now follow
the sample: the exponent/key "17 days" and the `verdict` sentence (an assertion about the 17 days, not a computation).
`--added` also computes the cells ADDED 2026-09-29 (bottom of this file); they are extra looks and feed nothing above.
"""
from __future__ import annotations
import argparse, csv, json, math, os, re, statistics as st, sys, datetime as dt, collections
H = os.path.expanduser("~")
sys.path.insert(0, f"{H}/zero-dte-lab/src")
from atomicio import atomic_json
OUT_REGISTERED = f"{H}/zero-dte-lab/results/naked_selling_study.json"
STRADDLE_REGISTERED = f"{H}/zero-dte-lab/results/straddle_test.csv"
_ap = argparse.ArgumentParser(description="What selling premium naked (and defined-risk) would have done on SPY 0DTE. Descriptive; paper only.")
_ap.add_argument("--out", default=OUT_REGISTERED,
                 help="output JSON. The default is the REGISTERED results/naked_selling_study.json - pass a NEW path to refresh without overwriting it")
_ap.add_argument("--straddle-csv", default=STRADDLE_REGISTERED, help="Block B's input rows (default: the registered results/straddle_test.csv)")
_ap.add_argument("--build-straddle", action="store_true",
                 help="rebuild --straddle-csv from EVERY recorded session first (straddle_test.run over signal_cost.load_books, closes extended)")
_ap.add_argument("--added", action="store_true", help="also compute the cells ADDED 2026-09-29 (defined-risk seller, quiet-block extras)")
ARGS = _ap.parse_args()
OUT, STRADDLE_CSV = ARGS.out, ARGS.straddle_csv
if ARGS.build_straddle and os.path.abspath(STRADDLE_CSV) == os.path.abspath(STRADDLE_REGISTERED):
    raise SystemExit("REFUSED: --build-straddle would overwrite the registered results/straddle_test.csv; pass a NEW --straddle-csv")
if (ARGS.added or ARGS.build_straddle or os.path.abspath(STRADDLE_CSV) != os.path.abspath(STRADDLE_REGISTERED)) \
        and os.path.abspath(OUT) == os.path.abspath(OUT_REGISTERED):
    raise SystemExit("REFUSED: this run would overwrite the registered results/naked_selling_study.json; pass a NEW --out")

# ======================================= ADDED 2026-09-29 - the DATA RANGE (rules unchanged) =======================
# `--build-straddle` re-runs straddle_test.run() over every recorded session. Nothing here changes a rule:
#   books   signal_cost.load_books() itself - laptop + CI legs, deduped on the CBOE book stamp, 0DTE only, a book stamped a
#           prior session dropped by its own date test, quotes must be two-sided - with ONLY the *.yfinance.csv fallback feed
#           (a different-quality feed sharing the date stem) filtered out of the two directories it globs;
#   closes  straddle_test's own: the actual RTH close from the 5m cache where the cache reaches (never the last recorded
#           book); for the sessions after it (cache ends 2026-08-14) the settled daily close in stock-radar/data/spy_daily.csv,
#           local and written after the bell. On the 60 overlapping sessions it differs from the 5m last-bar close by $0.09
#           on average. No network: a missing 5m cache stops the run rather than fetching.
SESSION_FILE = re.compile(r"^SPY_(\d{4}-\d{2}-\d{2})\.csv$")     # plain CBOE session files only
OFFICIAL_CLOSES = f"{H}/stock-radar/data/spy_daily.csv"
CLOSE_SRC, BUILD_NOTES = {}, {}


def _official_closes():
    """{YYYY-MM-DD: settled daily close}, read-only, from stock-radar's own SPY file."""
    with open(OFFICIAL_CLOSES) as fh:
        rd = csv.reader(fh)
        next(rd)
        return {r[0]: float(r[1]) for r in rd if len(r) > 1 and r[1]}


class _PlainSessionFiles:
    """Path-like whose .glob() drops *.yfinance.csv, so signal_cost.load_books() itself is used unchanged."""
    def __init__(self, p): self._p = p
    def glob(self, pat): return [x for x in self._p.glob(pat) if SESSION_FILE.match(x.name)]
    def __str__(self): return str(self._p)


def _closes_extended(dates):
    """{date: close}: straddle_test's own where the 5m cache reaches, the settled daily close for the sessions after it."""
    import signal_cost as sc, straddle_test as stt
    if not sc.CACHE.exists():
        raise SystemExit(f"REFUSED: {sc.CACHE} is missing - load_spy_5m() would go to the network, and this study fetches nothing")
    closes = dict(stt.session_closes(sc.load_spy_5m()))
    for d in closes:
        CLOSE_SRC[d.isoformat()] = "5m cache RTH close (straddle_test's own rule)"
    off = _official_closes()
    for d in sorted(dates):
        if d not in closes and d.isoformat() in off:
            closes[d] = off[d.isoformat()]
            CLOSE_SRC[d.isoformat()] = "stock-radar settled daily close (range extension)"
    return closes


def build_straddle_csv(path):
    """straddle_test.run() over every recorded session, into the NEW file `path`."""
    import signal_cost as sc, straddle_test as stt
    sc.CHAINS, sc.CHAINS_CI = _PlainSessionFiles(sc.CHAINS), _PlainSessionFiles(sc.CHAINS_CI)
    books = sc.load_books()
    closes = _closes_extended(set(books["date"].unique()))
    d = stt.run(books, closes)
    d.to_csv(path, index=False)
    used = set(d["date"].astype(str).unique())
    for date, day in books.groupby("date"):
        n, iso = int(day["quote_ts"].nunique()), date.isoformat()
        BUILD_NOTES[iso] = {"books": n, "in_sample": iso in used}
        if iso not in used:
            BUILD_NOTES[iso]["reason"] = (f"only {n} books (< MIN_BOOKS {sc.MIN_BOOKS})" if n < sc.MIN_BOOKS
                                          else "no settled close available")


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
if ARGS.build_straddle: build_straddle_csv(STRADDLE_CSV)
B, Bday = [], collections.defaultdict(list)
for r in csv.DictReader(open(STRADDLE_CSV)):
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
      f"chance_of_drawing_{len(days)}_days_with_no_2pct_move": round(100 * (1 - p2) ** len(days), 1),
      "verdict": (f"COMPUTED for this sample (2026-09-29; the 2026-09-23 sentence asserted facts about its 17 days): the sample's LARGEST "
                  f"realized move was {sample_max:.2f}% against SPY's AVERAGE day of {st.mean(mv):.2f}% and its 95th percentile of {q(0.95):.2f}%")},
  "THE_TAIL_THE_SAMPLE_NEVER_SAW": {"a_95th_percentile_day (about once every 3 weeks)": seller_on(q(0.95)),
      "a_99th_percentile_day (about 2-3 a year)": seller_on(q(0.99)), "the_worst_day_on_file": seller_on(max(mv))}})
# ---- the ruin table: one worst event at N contracts vs the account
def ruin(res, sizes=(1, 5, 10, 25)):
    if not res.get("n_structures"): return {}
    w = -res["worst_single"] * 100          # per contract, dollars
    return {f"{n}_contracts": {"worst_event_usd": round(w * n), "mean_win_usd": round(res["seller_mean_per_share"] * 100 * n, 2),
                               "events_of_mean_income_erased": round(w / max(1e-9, res["seller_mean_per_share"] * 100), 1) if res["seller_mean_per_share"] > 0 else "income is negative"}
            for n in sizes}
# =========================================================================================================
# ADDED 2026-09-29 - extra looks, each COUNTED as a look (multiplicity). None of it alters Block A or B.
# Definitions frozen here, before the first number was seen.
#
# A LABEL TO READ CAREFULLY. Block B's label says "first snapshot -> close", but its code averages EVERY recorded book of the
#   day (n_structures counts books; a day's value is the mean over ~75 entries). The first-snapshot design is measured below
#   on the same days as the iron butterfly, so the defined-risk cell has a like-for-like naked comparator.
# DEFINED-RISK SELLER. An iron butterfly at the first USABLE snapshot, held to the close: sell the ATM call and put at K, buy the
#   call at K+5 and the put at K-5. K = straddle_test's own pick (nearest strike to spot, call and put at the same strike).
#   Per share the seller keeps the net credit and pays min(|close - K|, 5): maximum loss = 5 - net credit, maximum gain = net credit.
#   FIRST USABLE SNAPSHOT (ZDTE-003 ii) = the earliest fetched_at_et in data/chains/SPY_<date>.csv at which the structure is
#   fittable: the book stamp is dated the session (load_books' staleness test), every leg row is two-sided (ask > 0, bid >= 0,
#   ask >= bid), the ATM call and put share a strike, both wings are listed. Every skipped snapshot is named.
#   CLOSE = Block B's closes (5m-cache RTH close where it reaches, else the settled daily close).
#   TWO FILLS, both shown. STUDY: shorts collected at the buyer's ASK (Block B's own open - it FLATTERS a seller, who really
#   collects the bid), wings paid at the ask. EXECUTABLE: shorts collected at the BID, wings paid at the ask - the seller's worst
#   case at the touch and the only column that could actually be traded (Firm Brain 5). "The buyer's side of the touch is the
#   seller's worst case" holds for the wings only, so both are reported and the reader picks.
#   Naked comparator: the same short ATM straddle with no wings, same days, same two fills.
# QUIET EXTRAS. Sample days that moved 1% or more (close to close from stock-radar's settled closes, and the study's own
#   realized-move measure), the largest down and up day, and how many 1% days history would predict for this many sessions.
# =========================================================================================================
WING = 5.0


def _valid_rows(df):
    """signal_cost.load_books' row rules applied to one recorded file: same tests, same order."""
    import pandas as pd
    df = df.copy()
    df["quote_ts"] = pd.to_datetime(df["quote_ts"], errors="coerce")
    df = df.dropna(subset=["quote_ts", "bid", "ask", "strike", "spot"])
    df["date"] = df["quote_ts"].dt.date
    df = df[pd.to_datetime(df["expiry"]).dt.date == df["date"]]
    return df[(df["ask"] > 0) & (df["bid"] >= 0) & (df["ask"] >= df["bid"])]


def _first_usable(fp):
    """ZDTE-003 (ii): the session's first snapshot, or the earliest FITTABLE one, naming each skipped snapshot."""
    import pandas as pd, signal_cost as sc
    day = os.path.basename(fp)[4:14]
    raw, skipped = pd.read_csv(fp), []
    for stamp, g in raw.groupby("fetched_at_et", sort=True):
        v = _valid_rows(g)
        if v.empty:
            skipped.append({"snapshot_fetched_et": stamp[11:],
                            "reason": f"no quote dated the session (book stamp {pd.to_datetime(g['quote_ts'], errors='coerce').iloc[0]})"})
            continue
        spot = float(v["spot"].iloc[0])
        c, p = sc._pick(v, "C", spot, 0), sc._pick(v, "P", spot, 0)
        if c is None or p is None or float(p["strike"]) != float(c["strike"]) or float(c["ask"]) + float(p["ask"]) <= 0:
            skipped.append({"snapshot_fetched_et": stamp[11:], "reason": "no ATM call/put pair at one strike with a positive ask"})
            continue
        K = float(c["strike"])
        wc, wp = v[(v["type"] == "C") & (v["strike"] == K + WING)], v[(v["type"] == "P") & (v["strike"] == K - WING)]
        if wc.empty or wp.empty:
            skipped.append({"snapshot_fetched_et": stamp[11:], "reason": f"a wing (K+{WING:g} call / K-{WING:g} put) is not listed with a valid quote"})
            continue
        return {"date": day, "snapshot_fetched_et": stamp[11:], "book_stamp_et": v["quote_ts"].iloc[0].strftime("%H:%M:%S"),
                "minutes_into_session": round((pd.Timestamp(stamp) - pd.Timestamp(f"{day} 09:30:00")).total_seconds() / 60, 1),
                "spot": spot, "K": K, "c_bid": float(c["bid"]), "c_ask": float(c["ask"]), "p_bid": float(p["bid"]), "p_ask": float(p["ask"]),
                "wc_ask": float(wc["ask"].iloc[0]), "wp_ask": float(wp["ask"].iloc[0])}, skipped
    return None, skipped


def _defined_risk_block():
    import glob
    files = sorted(x for x in glob.glob(f"{H}/zero-dte-lab/data/chains/SPY_*.csv") if SESSION_FILE.match(os.path.basename(x)))
    closes = _closes_extended({dt.date.fromisoformat(os.path.basename(x)[4:14]) for x in files})
    per_day, excluded = [], {}
    for fp in files:
        day = os.path.basename(fp)[4:14]
        rec, skipped = _first_usable(fp)
        if rec is None:
            excluded[day] = "no fittable snapshot: " + "; ".join(f"{s['snapshot_fetched_et']} {s['reason']}" for s in skipped[:2])
            continue
        if dt.date.fromisoformat(day) not in closes:
            excluded[day] = "no settled close available"
            continue
        S = closes[dt.date.fromisoformat(day)]
        move = abs(S - rec["K"])
        body_ask, body_bid, wings = rec["c_ask"] + rec["p_ask"], rec["c_bid"] + rec["p_bid"], rec["wc_ask"] + rec["wp_ask"]
        ib_pay = min(move, WING)
        per_day.append({**rec, "close": S, "close_source": CLOSE_SRC.get(day, "n/a"), "abs_close_minus_K": round(move, 4),
                        "skipped_before": skipped, "body_credit_at_ask": round(body_ask, 4), "body_credit_at_bid": round(body_bid, 4),
                        "wings_cost_at_ask": round(wings, 4),
                        "naked_pnl_study": round(body_ask - move, 4), "naked_pnl_executable": round(body_bid - move, 4),
                        "ib_net_credit_study": round(body_ask - wings, 4), "ib_net_credit_executable": round(body_bid - wings, 4),
                        "ib_pnl_study": round(body_ask - wings - ib_pay, 4), "ib_pnl_executable": round(body_bid - wings - ib_pay, 4)})

    def cell(label, pnl_key, prem_key):
        res = study([(r["date"], r[pnl_key], r[prem_key]) for r in per_day], label, "date")
        pnl = [r[pnl_key] for r in per_day]
        worst = min(per_day, key=lambda r: r[pnl_key])
        res.update({"days_won": sum(1 for x in pnl if x > 0), "days_lost": sum(1 for x in pnl if x < 0), "worst_day_date": worst["date"],
                    "worst_day_spy_abs_move_from_K": worst["abs_close_minus_K"]})
        return res

    def max_loss(net_key):
        m = [WING - r[net_key] for r in per_day]
        return {"per_share_average_over_days": round(st.mean(m), 3), "per_share_largest_day": round(max(m), 3),
                "per_share_smallest_day": round(min(m), 3), "per_contract_usd_average": round(100 * st.mean(m)),
                "per_contract_usd_largest": round(100 * max(m)),
                "note": f"the structure cannot lose more than {WING:g} - net credit per share, whatever SPY does"}

    cells = {"IRON_BUTTERFLY_executable_fill": cell("iron butterfly +-5, shorts at the BID, wings at the ask, first usable snapshot -> close", "ib_pnl_executable", "ib_net_credit_executable"),
             "IRON_BUTTERFLY_study_fill": cell("iron butterfly +-5, shorts at the ASK (flatters), wings at the ask, first usable snapshot -> close", "ib_pnl_study", "ib_net_credit_study"),
             "NAKED_STRADDLE_first_snapshot_executable_fill": cell("naked short ATM straddle, at the BID, first usable snapshot -> close", "naked_pnl_executable", "body_credit_at_bid"),
             "NAKED_STRADDLE_first_snapshot_study_fill": cell("naked short ATM straddle, at the ASK (flatters), first usable snapshot -> close", "naked_pnl_study", "body_credit_at_ask")}
    cells["IRON_BUTTERFLY_executable_fill"]["maximum_possible_loss"] = max_loss("ib_net_credit_executable")
    cells["IRON_BUTTERFLY_study_fill"]["maximum_possible_loss"] = max_loss("ib_net_credit_study")
    for k in ("NAKED_STRADDLE_first_snapshot_executable_fill", "NAKED_STRADDLE_first_snapshot_study_fill"):
        cells[k]["maximum_possible_loss"] = "unbounded: the loss is |close - K| minus the credit and grows with the move"
    nk = min(per_day, key=lambda r: r["naked_pnl_executable"])
    return {"definition": {"structure": f"sell ATM call+put at K, buy call K+{WING:g} and put K-{WING:g}; hold to the close; seller pays min(|close-K|, {WING:g})",
                           "entry": "first usable snapshot (ZDTE-003 ii): earliest fetched_at_et in data/chains/SPY_<date>.csv that is fittable",
                           "fills": {"study": "shorts at the buyer's ASK (Block B's own open, flatters the seller), wings at the ask",
                                     "executable": "shorts at the BID, wings at the ask - the seller's worst case at the touch"},
                           "close": "Block B's closes: 5m-cache RTH close where the cache reaches, else stock-radar's settled daily close"},
            "sessions": {"files_seen": len(files), "used": len(per_day), "excluded": excluded,
                         "started_late_gt_45min_into_session": [r["date"] for r in per_day if r["minutes_into_session"] > 45]},
            "cells": cells,
            "the_wings_on_the_naked_worst_day": {"date": nk["date"], "naked_pnl_executable": nk["naked_pnl_executable"],
                                                 "iron_butterfly_pnl_executable_same_day": nk["ib_pnl_executable"]},
            "average_cost_of_the_wings_per_share": round(st.mean(r["wings_cost_at_ask"] for r in per_day), 3),
            "per_day": per_day}


def _quiet_extras():
    off = _official_closes()
    ds = sorted(off)
    prev = {d: off[ds[i - 1]] for i, d in enumerate(ds) if i}
    meta = collections.defaultdict(lambda: {"n": 0, "first": None, "last": None})
    for r in csv.DictReader(open(STRADDLE_CSV)):
        m, t = meta[r["date"][:10]], r["quote_ts"][11:19]
        m["n"] += 1
        m["first"] = t if m["first"] is None or t < m["first"] else m["first"]
        m["last"] = t if m["last"] is None or t > m["last"] else m["last"]
    rows = []
    for d, pm, prm, rm, sp in days:
        c2c = round((off[d] / prev[d] - 1) * 100, 2) if d in off and d in prev else None
        rows.append({"date": d, "close_to_close_pct": c2c,
                     "blockB_realized_move_pct_study_measure": None if rm is None else round(rm, 3),
                     "blockB_seller_day_pnl_per_share": round(pm, 3), "blockB_avg_premium_per_share": round(prm, 3),
                     "n_books": meta[d]["n"], "first_book_stamp_et": meta[d]["first"], "last_book_stamp_et": meta[d]["last"],
                     "close_source": CLOSE_SRC.get(d, "read from the straddle CSV")})
    known = [r for r in rows if r["close_to_close_pct"] is not None]
    p1 = sum(1 for m in mv if m >= 1) / len(mv)
    big = [r for r in known if abs(r["close_to_close_pct"]) >= 1.0]
    return {"sample_days": len(days),
            "days_moving_1pct_or_more_close_to_close": big,
            "n_days_moving_1pct_or_more_close_to_close": len(big),
            "days_where_the_study_measure_is_1pct_or_more": [r["date"] for r in rows if (r["blockB_realized_move_pct_study_measure"] or 0) >= 1.0],
            "largest_down_day": min(known, key=lambda r: r["close_to_close_pct"]) if known else None,
            "largest_up_day": max(known, key=lambda r: r["close_to_close_pct"]) if known else None,
            "share_of_history_days_moving_1pct_or_more": round(100 * p1, 1),
            "days_1pct_or_more_history_predicts_for_this_many_sessions": round(len(days) * p1, 1),
            "sample_days_without_a_settled_close_to_close": [r["date"] for r in rows if r["close_to_close_pct"] is None],
            "blockB_days": rows}


def added_block():
    dr, qx = _defined_risk_block(), _quiet_extras()
    return {"label": "ADDED 2026-09-29 - extra looks, counted as looks; nothing here alters Block A or B",
            "status": "DESCRIPTION ONLY - nothing registered, no position follows from it",
            "blockB_label_caveat": ("Block B's label says 'first snapshot -> close' but its code averages EVERY recorded book of the day "
                                    f"(n_structures {resB['n_structures']} = books); the first-snapshot design is in defined_risk_seller "
                                    "as NAKED_STRADDLE_first_snapshot_*"),
            "data_range": {"straddle_csv": os.path.relpath(STRADDLE_CSV, f"{H}/zero-dte-lab"), "rebuilt_this_run": ARGS.build_straddle,
                           "session_files_read": "plain CBOE session files only; SPY_<date>.yfinance.csv (fallback feed, different quality) excluded",
                           "blockB_books_rule": "signal_cost.load_books unchanged: laptop + CI legs deduped on the CBOE book stamp, MIN_BOOKS 40",
                           "blockB_sessions_in_sample": len(days), "build_notes_per_session": BUILD_NOTES,
                           "closes": "5m-cache RTH close where the cache reaches (through 2026-08-14), else stock-radar's settled daily close",
                           "closes_used": {d: CLOSE_SRC[d] for d in sorted(CLOSE_SRC) if d in {r['date'] for r in qx['blockB_days']}}},
            "defined_risk_seller": dr, "how_quiet_extras": qx,
            "looks_added": {"iron_butterfly_two_fills": 2, "naked_first_snapshot_comparator_two_fills": 2,
                            "quiet_extras_1pct_days": 1, "total": 5}}


rep = {"generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
       "status": "DESCRIPTION ONLY - EV-3 stays as Anupam ruled it; this registers nothing and takes no position",
       "A_refused_straddles": resA, "A_ruin": ruin(resA), "B_spy_0dte": resB, "B_ruin": ruin(resB)}
if ARGS.added: rep["ADDED_2026-09-29"] = added_block()
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
print(f"  HOW QUIET: sample max move {Q['sample_MAX_realized_move_pct']}% vs SPY history mean {Q['spy_history_mean_move_pct']}% · 95th {Q['spy_95th_pct_move']}% · 99th {Q['spy_99th_pct_move']}% · {Q['share_of_history_days_moving_2pct_or_more']}% of days move >= 2% · chance of {len(days)} days without one: {Q[f'chance_of_drawing_{len(days)}_days_with_no_2pct_move']}%")
for k, v in T.items():
    print(f"  {k}: SPY {v['spy_move_pct']}% -> seller {v['seller_pnl_per_share']:+.2f}/sh = {v['average_winning_days_erased']} average winning days erased")
print("\n  wrote", OUT)
if ARGS.added:
    _ad = rep["ADDED_2026-09-29"]; _dr, _qx = _ad["defined_risk_seller"], _ad["how_quiet_extras"]
    print("\n  ADDED 2026-09-29 (extra looks) " + "-" * 60)
    print(f"   Block B sample: {_ad['data_range']['blockB_sessions_in_sample']} sessions; {_ad['looks_added']['total']} extra looks in this file")
    print(f"   defined-risk sample: {_dr['sessions']['used']} usable of {_dr['sessions']['files_seen']} files; excluded {_dr['sessions']['excluded']}; late starts {_dr['sessions']['started_late_gt_45min_into_session']}")
    for _k, _c in _dr["cells"].items():
        _ml = _c["maximum_possible_loss"]
        _ml = f"max loss avg {_ml['per_share_average_over_days']}/sh (largest {_ml['per_share_largest_day']})" if isinstance(_ml, dict) else "max loss unbounded"
        print(f"   {_k}\n      n {_c['n_days']} days · won {_c['days_won']} · mean {_c['seller_mean_per_share']:+.3f}/sh · median {_c['seller_median_per_share']:+.3f} · "
              f"t {_c['t_days']} · worst {_c['worst_single']:+.3f} on {_c['worst_day_date']} = {_c['worst_single_vs_mean_win']}x an average win · {_ml}")
    print(f"   quiet extras: {_qx['n_days_moving_1pct_or_more_close_to_close']} of {_qx['sample_days']} sample days moved >= 1% close to close "
          f"(history predicts {_qx['days_1pct_or_more_history_predicts_for_this_many_sessions']}); largest down {_qx['largest_down_day']}; largest up {_qx['largest_up_day']}")

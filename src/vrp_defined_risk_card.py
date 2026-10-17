"""vrp_defined_risk_card.py -- one-page PNG/PDF of results/vrp_defined_risk_study.json (conclusions first).

Run: /opt/anaconda3/bin/python src/vrp_defined_risk_card.py
Writes ~/Desktop/Trading/reviews/vrp_defined_risk_2026-10-17.{html,png,pdf}. No live account figures inside.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = json.loads((ROOT / "results" / "vrp_defined_risk_study.json").read_text())
WEEKS = pd.read_csv(ROOT / "results" / "vrp_defined_risk_weeks.csv", parse_dates=["entry"])
OUT = Path.home() / "Desktop" / "Trading" / "reviews"
STEM = "vrp_defined_risk_2026-10-17"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGE_W, PAGE_H = 1400, 1900
COL = {"IC": "#2a78d6", "PCS": "#eb6834", "CCS": "#1baf7a"}
NAME = {"IC": "iron condor", "PCS": "put spread", "CCS": "call spread"}


def cum_svg():
    W, H, L, R, T, B = 820, 380, 56, 120, 18, 40
    d = WEEKS.sort_values("entry")
    x0, x1 = d.entry.min(), d.entry.max()
    series = {s: d[s].fillna(0).cumsum().values for s in ("IC", "PCS", "CCS")}
    ymax = max(v.max() for v in series.values()) * 1.08
    ymin = min(0, min(v.min() for v in series.values()))

    def X(t):
        return L + (t - x0) / (x1 - x0) * (W - L - R)

    def Y(v):
        return T + (ymax - v) / (ymax - ymin) * (H - T - B)

    g = []
    for yr0, yr1 in ((2000, 2002), (2008, 2008), (2020, 2020), (2022, 2022)):
        a, b = X(pd.Timestamp(f"{yr0}-01-01")), X(pd.Timestamp(f"{yr1}-12-31"))
        g.append(f'<rect x="{a:.1f}" y="{T}" width="{b - a:.1f}" height="{H - T - B}" fill="#f1f0ec"/>')
    for v in range(0, int(ymax) + 1, 20):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"#9a9994" if v == 0 else "#e6e5e1"}"/>')
        g.append(f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" class="ax">{v}</text>')
    for yr in (1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025):
        g.append(f'<text x="{X(pd.Timestamp(f"{yr}-01-01")):.1f}" y="{H - B + 18}" text-anchor="middle" class="ax">{yr}</text>')
    for lab, yr in (("2000–02", 2001), ("2008", 2008), ("2020", 2020), ("2022", 2022)):
        g.append(f'<text x="{X(pd.Timestamp(f"{yr}-07-01")):.1f}" y="{T + 12}" text-anchor="middle" class="ax">{lab}</text>')
    step = max(1, len(d) // 600)
    ends = []
    for s, v in series.items():
        pts = " ".join(f"{X(t):.1f},{Y(y):.1f}" for t, y in zip(d.entry.values[::step], v[::step]))
        pts += f" {X(d.entry.values[-1]):.1f},{Y(v[-1]):.1f}"
        g.append(f'<polyline points="{pts}" fill="none" stroke="{COL[s]}" stroke-width="2" stroke-linejoin="round"/>')
        ends.append([Y(v[-1]), s, v[-1]])
    ends.sort()
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 32:
            ends[k][0] = ends[k - 1][0] + 32
    for y, s, v in ends:
        g.append(f'<rect x="{W - R + 8}" y="{y - 9:.1f}" width="10" height="3" fill="{COL[s]}"/>')
        g.append(f'<text x="{W - R + 24}" y="{y - 3:.1f}" class="lb">{NAME[s]}</text>'
                 f'<text x="{W - R + 24}" y="{y + 13:.1f}" class="ax">+{v:.0f} max risks</text>')
    g.append(f'<text x="{L}" y="{H - 4}" class="ax">Model-priced weekly trades on the S&amp;P 500, every week, no exceptions. Shaded: crash years.</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Cumulative P&amp;L in max-risk units">{"".join(g)}</svg>'


def r_(x, d=3):
    return f"{x:+.{d}f}"


def main():
    V0, P, G, A, CC = RES["V0"], RES["primary"], RES["grid"], RES["crash_audit"], RES["chain_check"]
    ic, pcs, ccs = P["IC"], P["PCS"], P["CCS"]
    bench = RES["benchmark_spx_price"]
    cal = RES["calibration"]
    losing_pcs = [y for y, v in A["PCS"]["by_year_sum_r"].items() if v < 0]
    ic_worst = A["IC"]["worst15"]
    pcs_worst = A["PCS"]["worst15"]
    big = WEEKS[WEEKS.IC <= -0.9]
    n_big, n_big_up, n_big_dn = len(big), int((big.move_pct > 0).sum()), int((big.move_pct < 0).sum())

    concl = [
        ("The premium is real.",
         f"In <b>{V0['pct_implied_gt_realized']:.0f}%</b> of the {V0['weeks']:,} weeks since 1990, options priced a bigger move than the S&amp;P "
         f"500 then made, on average {V0['mean_gap_vol_pts']:.1f} volatility points too much. Raw VIX gives "
         f"{V0['raw_vix9d_pct_implied_gt_realized']:.0f}%. This matches what your 0DTE lab found."),
        ("On the model, a capped-risk condor kept it, crash years included.",
         f"Selling the weekly ±1-move iron condor with ±2-move wings won {ic['primary']['win_pct']:.0f}% of weeks and averaged "
         f"{r_(ic['primary']['mean_r'])} of its max risk per week (t {ic['primary']['nw_t']}). It was positive in 1990–2007, 2008–2019 and 2020–2026. "
         f"Risking 2% a week: {ic['equity']['cagr_pct']:.1f}%/yr, worst drop {ic['equity']['max_dd_pct']:.0f}%, worst week "
         f"{ic['equity']['worst_week_pct']:.0f}% (the cap). The S&amp;P made {bench['cagr_pct']:.1f}%/yr with a {bench['max_dd_pct']:.0f}% drop."),
        ("But the whole answer hangs on one number the model can't pin down: how expensive the options really were.",
         f"Make them 10% cheaper than my estimate and the condor's profit falls about three-quarters, to "
         f"{r_(G['IC|cost1x|0.9k|skew_measured']['mean_r'])} (t {G['IC|cost1x|0.9k|skew_measured']['nw_t']}). Add a steeper skew and it loses "
         f"({r_(G['IC|cost1x|0.9k|skew_2x']['mean_r'])}). The extra is only ~{V0['mean_gap_vol_pts']:.1f} points, and the condor needs most of it."),
        ("Under the rules written beforehand, it is <u>not</u> supported.",
         f"All three trades failed the deflation test (deflated Sharpe {ic['dsr']['dsr']:.2f}; the bar was 0.95). The call spread also failed "
         f"the cost check, and it has been flat since 2020 (t {ccs['2020_2026']['nw_t']}). The deflation bar is harsh here because my grid of "
         f"price assumptions is wide. The price-level problem above is the real reason not to trust the number."),
        ("Crashes did most of the damage, and sharp rallies hurt too.",
         f"Of the condor's {n_big} near-max losses (−0.9 of max risk or worse), {n_big_dn} came in down weeks and {n_big_up} in up weeks, such as the "
         f"+12.1% rebound in the week of 2020-04-03, which ran over the call side. The put spread, where people think the money is, earned less "
         f"({r_(pcs['primary']['mean_r'])} per week). It took "
         f"{pcs['primary']['max_loss_weeks']} full-loss weeks, including −18.2% in October 2008, and lost money in {len(losing_pcs)} of 37 years "
         f"({', '.join(losing_pcs)})."),
        ("Your real quotes agree with the model on shape, but are far too few to judge.",
         f"On your {CC['sessions']} recorded days, the real executable credit was {CC['real_credit_over_width_median'] * 100:.1f}% of the wing width, "
         f"against {CC['model_credit_over_width_median'] * 100:.1f}% for the model. The same condor on real 0DTE quotes won "
         f"{CC['real_ic_win_pct']:.0f}% of days, averaging {r_(CC['real_ic_mean_r'])} of max risk (t {CC['real_ic_nw_t']}). It points the same way, "
         f"but 63 days can't settle it."),
    ]
    concl_html = "".join(f"<li><b>{h}</b> {b}</li>" for h, b in concl)

    def gcell(key):
        v = G[key]
        cls = "n neg" if v["mean_r"] <= 0 else "n"
        return f'<td class="{cls}">{r_(v["mean_r"])}<br><span class="m">t {v["nw_t"]}</span></td>'

    sens = ""
    for lab, kl in (("10% cheaper (0.9k)", "0.9k"), ("my estimate (k = 0.94)", "k"), ("raw VIX (k = 1)", "k=1")):
        sens += f"<tr><td>{lab}</td>{gcell(f'IC|cost1x|{kl}|skew_measured')}{gcell(f'IC|cost2x|{kl}|skew_measured')}{gcell(f'IC|cost1x|{kl}|skew_2x')}</tr>"

    def worst_rows(lst, n=6):
        return "".join(f'<tr><td>{w["entry"]}</td><td class="n">{w["spx_move_pct"]:+.1f}%</td><td class="n">{w["vol_pct"]:.0f}%</td>'
                       f'<td class="n">{w["loss_r"]:+.2f}</td><td class="n">{w["weeks_of_premium_eaten"]:.0f}</td></tr>' for w in lst[:n])
    pcs_big = sorted(pcs_worst, key=lambda w: w["spx_move_pct"])[:6]
    ic_big = sorted(ic_worst[:10], key=lambda w: -abs(w["spx_move_pct"]))[:6]

    era_rows = ""
    for s in ("IC", "PCS", "CCS"):
        era_rows += (f'<tr><td><span class="sw" style="background:{COL[s]}"></span>{NAME[s]}</td>'
                     + "".join(f'<td class="n">{r_(P[s][e]["mean_r"])}<br><span class="m">t {P[s][e]["nw_t"]}</span></td>'
                               for e in ("1990_2007", "2008_2019", "2020_2026"))
                     + f'<td class="n">{P[s]["primary"]["win_pct"]:.0f}%</td><td class="n">{P[s]["equity"]["cagr_pct"]:.1f}%</td>'
                       f'<td class="n">{P[s]["equity"]["max_dd_pct"]:.0f}%</td></tr>')

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Option Premium Test</title><style>
@page {{ size: {PAGE_W}px {PAGE_H}px; margin: 0 }}
body {{ margin: 0; width: {PAGE_W}px; background: #fcfcfb; color: #0b0b0b; font: 16px/1.45 -apple-system, Helvetica, Arial, sans-serif }}
.wrap {{ padding: 34px 44px }} h1 {{ font-size: 30px; margin: 0 0 4px }} .sub {{ color: #52514e; font-size: 15px }}
.verdict {{ margin: 18px 0 14px; padding: 14px 18px; border-left: 6px solid #d03b3b; background: #f6f5f2; font-size: 19px }}
ol {{ margin: 0; padding-left: 26px }} li {{ margin: 0 0 11px }}
.decide {{ margin: 14px 0 6px; padding: 14px 18px; background: #eef4fc; border-left: 6px solid #2a78d6 }}
.decide ul {{ margin: 6px 0 0; padding-left: 22px }} .decide li {{ margin: 0 0 4px }}
.grid {{ display: grid; grid-template-columns: 830px 1fr; gap: 24px; margin-top: 16px }}
h2 {{ font-size: 17px; margin: 16px 0 6px }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px }}
td, th {{ border-bottom: 1px solid #e6e5e1; padding: 5px 6px; text-align: left; vertical-align: top }}
th {{ color: #52514e; font-weight: 600 }} td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums }}
td.neg {{ background: #fdf0e9 }} .m {{ color: #52514e; font-size: 12.5px }}
.sw {{ display: inline-block; width: 10px; height: 3px; margin: 0 6px 4px 0 }}
svg text.ax {{ font-size: 12.5px; fill: #52514e }} svg text.lb {{ font-size: 13.5px; fill: #0b0b0b; font-weight: 600 }}
.foot {{ color: #52514e; font-size: 12.5px; margin-top: 14px; border-top: 1px solid #e6e5e1; padding-top: 10px }}
</style></head><body><div class="wrap">
<h1>Selling capped-risk options on the S&amp;P 500, 1990–2026: tested</h1>
<div class="sub">{V0['weeks']:,} weeks · weekly iron condor, put spread and call spread at ±1 move, wings at ±2 · priced from VIX, skew and spreads
measured on your {cal['sessions']} recorded chain days · rules written before the data (zero-dte-lab 421610b) · 2026-10-17</div>
<div class="verdict"><b>Verdict: NOT SUPPORTED as an edge, but this is the closest anything has come.</b> The premium is real, and on the
model a capped condor kept it through every crash. But it depends on a price level that only real weekly quotes can confirm.</div>
<ol>{concl_html}</ol>
<div class="decide"><b>What this means for you</b> (I'm not a licensed advisor; this is what the history shows)
<ul><li>No trade and no new desk (COUNCIL-021). Sim only (Rule 7). Naked selling stays blocked: here a single bad week can erase about
{abs(RES['naked_reference']['worst_pct_spot']) / RES['naked_reference']['mean_win_pct_spot']:.0f} average winning weeks.</li>
<li>The one way to settle it is real weekly quotes. Your chain recorder saves only same-day options. If it also saved the Friday expiry,
a real record would build up, and about 50 weeks could be judged.</li>
<li>If you ever trade premium, the cap is what saved the condor in 2008 and 2020: the worst week was −2% of the account, not −56%.</li></ul></div>

<div class="grid"><div>
<h2>Cumulative result, in units of max risk (model)</h2>
{cum_svg()}
<h2>By era: average per week (units of max risk), win rate, and 2%-risk equity</h2>
<table><tr><th></th><th class="n">1990–2007</th><th class="n">2008–2019</th><th class="n">2020–2026</th><th class="n">win</th><th class="n">per yr</th><th class="n">worst drop</th></tr>
{era_rows}</table>
</div><div>
<h2>How much the condor earns under different price assumptions</h2>
<table><tr><th>Option prices</th><th class="n">measured costs</th><th class="n">2× costs</th><th class="n">2× skew</th></tr>{sens}</table>
<div class="m" style="margin-top:6px">Average per week, in units of max risk. Shaded = loses money. A 10% error in the price level changes the answer.</div>
<h2>Put spread: the crash weeks</h2>
<table><tr><th>Week of</th><th class="n">S&amp;P</th><th class="n">vol</th><th class="n">result</th><th class="n">wins eaten</th></tr>{worst_rows(pcs_big)}</table>
<h2>Condor: rallies hurt too ({n_big_up} of its {n_big} near-max losses)</h2>
<table><tr><th>Week of</th><th class="n">S&amp;P</th><th class="n">vol</th><th class="n">result</th><th class="n">wins eaten</th></tr>{worst_rows(ic_big)}</table>
<div class="m" style="margin-top:6px">"Wins eaten" = how many average winning weeks one loss cancels.</div>
</div></div>

<div class="foot"><b>How it was tested.</b> Each week: sell at the Friday close, settle at the next Friday close (SPX weeklies are cash-settled, European).
Weekly vol = 0.94 × VIX9D. Before 2011, VIX9D is estimated from VIX (fit on 2011–2026). Strikes are at ±1 and ±2 expected moves. Black-Scholes is used with the
skew measured on your chains (puts at −2 moves priced 1.30× ATM vol, calls at +1 0.96×). Every leg fills at the bid or ask, never the mid, with
spreads measured on your chains (1–11% of price). <b>Correction disclosed:</b> the price-level step as first written gave a factor of 2.14. That came from a VIX1D
time-convention mismatch, not a premium, and it would have doubled every price. It was replaced before any P&amp;L was computed, with the
consistent VIX-to-ATM ratio (0.94). Weeklies did not exist before Oct 2005, so those years are a hypothetical contract. 1990s spreads were wider
than today's. 1987 predates VIX; a capped trade loses at most one max risk in any week. Luck count: 4 looks here, deflated at N = 150 for the family.
Files: ~/zero-dte-lab/src/vrp_defined_risk_study.py · results/vrp_defined_risk_study.json · src/vrp_defined_risk_card.py. Paper and sim only.</div>
</div></body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    h = OUT / f"{STEM}.html"
    h.write_text(html)
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", f"--user-data-dir={OUT / '.chrome-card'}"]
    subprocess.run(base + [f"--window-size={PAGE_W},{PAGE_H}", f"--screenshot={OUT / (STEM + '.png')}", h.as_uri()], check=True, capture_output=True, timeout=90)
    subprocess.run(base + ["--no-pdf-header-footer", f"--print-to-pdf={OUT / (STEM + '.pdf')}", h.as_uri()], check=True, capture_output=True, timeout=90)
    print("wrote", OUT / f"{STEM}.png")


if __name__ == "__main__":
    main()

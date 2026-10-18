"""option_premium_card.py -- the live "Option premium" tab, conclusions first: the VRP model study (421610b) checked
against CBOE's real-price strategy indexes (cboe_index_check.py, 56ff859).

Reads results/cboe_index_check.json, results/cboe_index_check_weekly.csv and results/vrp_defined_risk_study.json only.
build_html() is the seam ~/command-center/live_page.py uses. Run directly to write the local record:
~/Desktop/Trading/reviews/option_premium_2026-10-17.{png,pdf}. Paper research only; no live account figures inside.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "results" / "cboe_index_check.json").read_text())
M = json.loads((ROOT / "results" / "vrp_defined_risk_study.json").read_text())
W = pd.read_csv(ROOT / "results" / "cboe_index_check_weekly.csv", parse_dates=["week_end"]).set_index("week_end")
OUT = Path.home() / "Desktop" / "Trading" / "reviews"
STEM = "option_premium_2026-10-17"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGE_W, PAGE_H = 1200, 2300
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"

CSS = """
:root{color-scheme:light;--bg:#fcfcfb;--ink:#1d1c1a;--mut:#6b6a65;--line:#e3e1db;--card:#ffffff;--no:#b4441c}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:28px 16px} h1{font-size:28px;margin:0 0 4px;line-height:1.2} h2{font-size:17px;margin:22px 0 8px}
.sub,.m{color:var(--mut);font-size:13px} .banner{margin:16px 0;padding:14px 16px;border-left:6px solid var(--no);background:#f4f2ee;font-size:17px}
ol.concl{padding-left:22px;margin:0} ol.concl li{margin:0 0 10px}
.decide{margin:14px 0;padding:12px 16px;background:#eef4fc;border-left:6px solid #2a78d6} .decide ul{margin:6px 0 0;padding-left:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px} @media (max-width:820px){.grid{grid-template-columns:1fr}}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.scroll{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:13.5px}
td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left;vertical-align:top} th{color:var(--mut);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums} td.neg{background:#fdf0e9}
svg{width:100%;height:auto} svg .ax{font-size:12px;fill:var(--mut)} svg .lb{font-size:12.5px;fill:var(--ink);font-weight:600}
.key{display:inline-block;width:12px;height:3px;margin:0 6px 4px 0}
.foot{margin-top:20px;border-top:1px solid var(--line);padding-top:10px;color:var(--mut);font-size:12.5px}
"""


def pct(bp, d=2):
    return f"{bp / 100:+.{d}f}%".replace("-", "−")


def line_chart(df, cols, colors, labels, shade=None, W_=540, H_=300):
    L, Rr, T, B = 46, 110, 14, 30
    d = df[cols].dropna(how="all").fillna(0.0).cumsum() * 100
    x0, x1 = d.index.min(), d.index.max()
    ymin, ymax = min(0.0, float(d.min().min())), float(d.max().max()) * 1.08

    def X(t):
        return L + (t - x0) / (x1 - x0) * (W_ - L - Rr)

    def Y(v):
        return T + (ymax - v) / (ymax - ymin) * (H_ - T - B)
    g = []
    for a, b, lab in (shade or []):
        xa, xb = X(pd.Timestamp(a)), X(pd.Timestamp(b))
        g.append(f'<rect x="{xa:.1f}" y="{T}" width="{xb - xa:.1f}" height="{H_ - T - B}" fill="#f1f0ec"/>'
                 f'<text x="{(xa + xb) / 2:.1f}" y="{T + 12}" text-anchor="middle" class="ax">{lab}</text>')
    step = 50 if ymax - ymin > 120 else 25 if ymax - ymin > 60 else 10
    v = int(ymin // step) * step
    while v <= ymax:
        g.append(f'<line x1="{L}" x2="{W_ - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"#9a9994" if v == 0 else "#e6e5e1"}"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" class="ax">{v:+d}%</text>'.replace("+0%", "0%"))
        v += step
    yrs = range(x0.year + (5 - x0.year % 5) % 5, x1.year + 1, 5)
    for yr in yrs:
        g.append(f'<text x="{X(pd.Timestamp(f"{yr}-01-01")):.1f}" y="{H_ - 10}" text-anchor="middle" class="ax">{yr}</text>')
    ends = []
    for col, c, lab in zip(cols, colors, labels):
        s = d[col]
        pts = " ".join(f"{X(t):.1f},{Y(y):.1f}" for t, y in zip(s.index[::2], s.values[::2]))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>')
        ends.append([Y(s.values[-1]), c, lab, s.values[-1]])
    ends.sort()
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 30:
            ends[k][0] = ends[k - 1][0] + 30
    for y, c, lab, v in ends:
        g.append(f'<rect x="{W_ - Rr + 6}" y="{y - 8:.1f}" width="10" height="3" fill="{c}"/>'
                 f'<text x="{W_ - Rr + 20}" y="{y - 2:.1f}" class="lb">{lab}</text>'
                 f'<text x="{W_ - Rr + 20}" y="{y + 13:.1f}" class="ax">{v:+.0f}% summed</text>')
    return f'<svg viewBox="0 0 {W_} {H_}" role="img">{"".join(g)}</svg>'


def index_rows():
    names = {"WPUT": "Sell a 1-week put, every week", "PUT": "Sell a 1-month put", "BXM": "Own the S&amp;P, sell a 1-month call",
             "CNDR": "Monthly iron condor"}
    out = ""
    for x in ("WPUT", "CNDR", "PUT", "BXM"):
        b = R[x]
        cmp_ = b["vs_sp500tr_same_weeks"]
        cls = ' class="n neg"' if b["net"]["mean_bp"] <= 0 or b["net"]["nw_t"] < 2 else ' class="n"'
        out += (f'<tr><td><b>{x}</b><br><span class="m">{names[x]}</span></td><td>{R["meta"]["files"][x][0][:4] if x != "PUT" else "2007"}–2026</td>'
                f'<td class="n">{pct(b["gross"]["mean_bp"])}</td><td{cls}>{pct(b["net"]["mean_bp"])}<br><span class="m">t {b["net"]["nw_t"]}</span></td>'
                f'<td class="n">{cmp_["strategy_net"]["sharpe_annual"]:.2f}</td><td class="n">{cmp_["sp500tr"]["sharpe_annual"]:.2f}</td>'
                f'<td class="n">{b["net"]["max_dd_pct"]:.0f}%</td><td>{R["verdicts"][x].split(" (")[0].title()}</td></tr>')
    return out


def build_html(height_hint=None):
    r5 = R["R5"]
    ic5 = r5["IC_at_k_star"]
    wp, cn = R["WPUT"], R["CNDR"]
    mic = M["primary"]["IC"]["primary"]
    v0 = M["V0"]
    concl = [
        ("The premium exists, but at real prices it is tiny.",
         f"Options did price more movement than happened in {v0['pct_implied_gt_realized']:.0f}% of weeks since 1990. But selling the weekly put at "
         f"real prices (CBOE's WPUT index, 2006–2026) earned only <b>{pct(wp['gross']['mean_bp'])}</b> a week over T-bills before costs "
         f"(t {wp['gross']['nw_t']}), and {pct(wp['net']['mean_bp'])} after (t {wp['net']['nw_t']}). That is a Sharpe of "
         f"{wp['vs_sp500tr_same_weeks']['strategy_net']['sharpe_annual']:.2f}, against {wp['vs_sp500tr_same_weeks']['sp500tr']['sharpe_annual']:.2f} "
         f"for simply owning the S&amp;P. Since 2020 it is zero ({pct(wp['2020_2026']['mean_bp'])})."),
        ("My model priced weekly options about 13% too rich.",
         f"Real WPUT prices imply weekly options at <b>{r5['k_star']:.3f}× VIX9D</b>, not the {r5['k_frozen']}× the model used. Week to week the "
         f"model tracked the real index almost exactly (correlation {r5['weekly_corr_model_real_at_k_star']:.2f}). Only the level was off: the "
         f"model's put-selling earned {pct(r5['model_at_k_frozen_mean_excess_bp'])} a week, against {pct(r5['real_wput_mean_excess_bp'])} in reality."),
        ("At the real price level, the condor's edge is gone.",
         f"The same weekly iron condor that made {mic['mean_r']:+.3f} of max risk a week on the model makes "
         f"<b>{ic5['1990_2026']['mean_r']:+.3f}</b> at the real level (t {ic5['1990_2026']['nw_t']}), and {ic5['2006_2026']['mean_r']:+.3f} since 2006 "
         f"(t {ic5['2006_2026']['nw_t']}). The model's profit was the overpricing."),
        ("The real iron condor index agrees: it stopped working in 2008.",
         f"CBOE's CNDR, a monthly condor on real prices since 1986, made {pct(cn['1986_2007']['mean_bp'])} a week over T-bills in 1986–2007 "
         f"(t {cn['1986_2007']['nw_t']}). It then lost money in 2008–2019 ({pct(cn['2008_2019']['mean_bp'])}) and in 2020–2026 "
         f"({pct(cn['2020_2026']['mean_bp'])}). After costs the whole record is t {cn['net']['nw_t']}."),
        ("The monthly versions made money, but less per unit of risk than owning the S&amp;P.",
         f"Selling monthly puts (PUT) or monthly calls against stock (BXM) earned {pct(R['PUT']['net']['mean_bp'])} and "
         f"{pct(R['BXM']['net']['mean_bp'])} a week over T-bills. Their Sharpes are {R['PUT']['vs_sp500tr_same_weeks']['strategy_net']['sharpe_annual']:.2f} "
         f"and {R['BXM']['vs_sp500tr_same_weeks']['strategy_net']['sharpe_annual']:.2f}, against "
         f"{R['PUT']['vs_sp500tr_same_weeks']['sp500tr']['sharpe_annual']:.2f} and {R['BXM']['vs_sp500tr_same_weeks']['sp500tr']['sharpe_annual']:.2f} "
         f"for the S&amp;P over the same weeks. They are stock-market exposure with the upside capped, not a separate edge."),
    ]
    concl_html = "".join(f"<li><b>{h}</b> {b}</li>" for h, b in concl)
    chart1 = line_chart(W.loc["2006-02-01":], ["model_putwrite_k_frozen", "model_putwrite_k_star", "wput_real_excess"], [C2, C3, C1],
                        ["as priced", f"at {r5['k_star']:.3f}×", "real WPUT"])
    chart2 = line_chart(W.loc["1986-06-01":], ["cndr_real_excess"], [C1], ["real CNDR"],
                        shade=[("1987-09-01", "1987-12-31", "1987"), ("2008-01-01", "2008-12-31", "2008"), ("2020-01-01", "2020-12-31", "2020")])
    model_rows = ""
    for lab, key, src in (("Iron condor", "IC", None), ("Put spread", "PCS", "PCS_at_k_star_1990_2026"), ("Call spread", "CCS", "CCS_at_k_star_1990_2026")):
        frozen = M["primary"][key]["primary"]
        at = ic5["1990_2026"] if key == "IC" else r5[src]
        cls = ' class="n neg"' if at["mean_r"] <= 0 else ' class="n"'
        model_rows += (f'<tr><td>{lab}</td><td class="n">{frozen["mean_r"]:+.3f}<br><span class="m">t {frozen["nw_t"]}</span></td>'
                       f'<td{cls}>{at["mean_r"]:+.3f}<br><span class="m">t {at["nw_t"]}</span></td></tr>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Option Premium</title><style>{CSS}</style></head><body><div class="wrap">
<h1>Selling option premium: the model against real prices</h1>
<p class="sub">Two studies, both with rules written before the data. The model study priced weekly S&amp;P options from VIX for 1990–2026 (zero-dte-lab 421610b).
The check used CBOE's indexes, built from real S&amp;P 500 option prices: WPUT, PUT, BXM and CNDR, back to 1986 (56ff859). 5 looks.</p>
<div class="banner"><b>Verdict: the lead is closed.</b> Real option prices kept almost none of the premium my model found. The model was pricing
weekly options about 13% too rich, and at the real level the condor earns nothing. The real condor index has lost money since 2008.</div>
<h2>What this means</h2>
<ol class="concl">{concl_html}</ol>
<div class="decide"><b>What to do with it</b> (I'm not a licensed advisor; this is what the history shows)
<ul><li>No trade, and no desk (COUNCIL-021). Selling premium, capped or not, is not an edge at real prices in this data.</li>
<li>The weekly quote recorder (ZDTE-015) was meant to settle this. CBOE's 20 years of real prices settled it first. It is cheap to keep
running, or it can be switched off. That is your call.</li>
<li>In every comparison here, simply owning the S&amp;P had the best return per unit of risk (Sharpe 0.55–0.59).</li></ul></div>
<div class="grid">
<div class="box"><b>Weekly put-selling, 2006–2026: the model as priced vs real</b>{chart1}
<div class="m">Weekly return over T-bills, summed, before costs. Orange = the model at 0.939× VIX9D. Green = the model at the level real prices
imply. Blue = CBOE's real WPUT index. Green and blue end level by construction (that is how 0.815 was found); the check is that they
move together week to week (correlation {r5['weekly_corr_model_real_at_k_star']:.2f}). Orange ran away from both.</div></div>
<div class="box"><b>The real iron condor (CNDR), 1986–2026</b>{chart2}
<div class="m">Weekly return over T-bills, summed, before costs. It rose until 2007 and has drifted down since 2008.</div></div>
</div>
<h2>Real-price indexes against owning the S&amp;P</h2>
<div class="scroll"><table><tr><th>Index</th><th>Years</th><th class="n">Per week, before costs</th><th class="n">After costs</th>
<th class="n">Sharpe</th><th class="n">S&amp;P Sharpe</th><th class="n">Worst drop</th><th>Verdict</th></tr>{index_rows()}</table></div>
<p class="m">Return over T-bills per week. Costs: WPUT 3 bp a week, PUT and BXM 3 bp a month, CNDR 10 bp a month. To pass, an index needed t ≥ 2 after
costs AND a Sharpe at least as good as the S&amp;P's (for CNDR: t ≥ 2 and positive in every era). Shaded = fails.</p>
<h2>The model's spreads: as first priced vs at the real price level</h2>
<div class="scroll"><table><tr><th>Weekly trade, 1990–2026</th><th class="n">Model as priced (0.939×)</th><th class="n">At the real level ({r5['k_star']:.3f}×)</th></tr>{model_rows}</table></div>
<p class="m">Average per week, in units of max risk. Only the condor is a counted test here. The put-spread line is shown for completeness: one uncounted cell
at t 2.3, before any deflation. It is not an edge claim.</p>
<div class="foot">Data: CBOE daily index files (cdn.cboe.com, pulled 2026-10-17), Yahoo ^SP500TR and ^IRX, and the frozen VRP study's VIX9D series.
PUT is tested from 2007, because its file is sparse before then (disclosed before any result). CBOE indexes are priced without the bid-ask spread,
so the costs above are subtracted. The first and last values of each file were seen before the rules were written; this was disclosed in the source.
Files: ~/zero-dte-lab/src/cboe_index_check.py · results/cboe_index_check.json. Paper research only.</div>
</div></body></html>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / f"{STEM}.html"
        h.write_text(build_html())
        base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", f"--user-data-dir={Path(td) / 'chrome'}"]
        subprocess.run(base + [f"--window-size={PAGE_W},{PAGE_H}", f"--screenshot={OUT / (STEM + '.png')}", h.as_uri()],
                       check=True, capture_output=True, timeout=90)
        subprocess.run(base + ["--no-pdf-header-footer", f"--print-to-pdf={OUT / (STEM + '.pdf')}", h.as_uri()],
                       check=True, capture_output=True, timeout=90)
    print("wrote", OUT / f"{STEM}.png")


if __name__ == "__main__":
    main()

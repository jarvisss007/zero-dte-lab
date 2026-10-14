"""fib_hour45_report.py — the fib_hour45_study result on one page (PNG + PDF), with today's chart as the worked example.
Reads results/fib_hour45_study.json; writes results/FIB_HOUR45_STUDY.png and .pdf. Market data only.
"""
import base64
import datetime as dt
import io
import json
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fib_hour45_study as fs  # noqa: E402
import key_times_study as k  # noqa: E402

RES = ROOT / "results"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1400, 1420
GOOD, BAD, INK, INK2, GRID, BLUE, ORANGE = "#0ca30c", "#d03b3b", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6", "#eb6834"
PT = ZoneInfo("America/Los_Angeles")


def fig_png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode()


def charts(rep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 10, "axes.edgecolor": GRID, "xtick.color": INK2,
                         "ytick.color": INK2})
    out = {}
    # 1 — respected-rate at every level of the leg, Fib levels highlighted
    br = rep["fib"]["by_ratio"]
    rs = sorted(br, key=float)
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    for r in rs:
        v = br[r]
        ax.plot(float(r), 100 * v["respected"], "o", ms=10 if v["fib"] else 7, color=ORANGE if v["fib"] else "#9a9a96",
                mec="white", mew=1.5, zorder=3)
        if v["fib"]:
            ax.text(float(r), 100 * v["respected"] + 0.9, f"{float(r):g}", ha="center", fontsize=9, color=INK, fontweight="bold")
    ax.axhline(100 * rep["fib"]["respected_control"], color="#9a9a96", lw=1, ls="--")
    ax.text(0.17, 100 * rep["fib"]["respected_control"] + 0.4, "average of the non-Fib levels", fontsize=8.5, color=INK2)
    ax.set_xlabel("level, as a share of the leg (0 = the leg's end, 1 = its start)", color=INK2)
    ax.set_ylabel("% of touches that held", color=INK2)
    ax.set_title("Did price hold at the level? Orange = Fibonacci, grey = ordinary levels of the same leg", loc="left",
                 fontsize=11, color=INK)
    ax.grid(axis="y", color=GRID)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    out["fib"] = fig_png(fig)
    plt.close(fig)
    # 2 — where in the hour the swings happen
    z = rep["hour45"]["0.0020"]
    prof = z["minute_profile"]
    keys = list(prof)
    tot = sum(prof.values())
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    vals = [100 * prof[c] / tot for c in keys]
    ax.bar(range(12), vals, color=[ORANGE if c == ":45" else "#b8c9e8" for c in keys], width=0.72)
    ax.axhline(100 / 12, color=INK2, lw=1, ls="--")
    ax.text(11.4, 100 / 12 + 0.15, "if every 5-min slot\nwere equally likely", fontsize=8, color=INK2, ha="right", va="bottom")
    ax.set_xticks(range(12))
    ax.set_xticklabels(keys)
    ax.set_ylabel("% of all swing highs/lows", color=INK2)
    ax.set_title(f"Where in the hour SPY's swings turned ({z['pivots']:,} swings of 0.20%+, 5-min bars)", loc="left",
                 fontsize=11, color=INK)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color=GRID)
    out["hour"] = fig_png(fig)
    plt.close(fig)
    # 3 — today's chart: every :45 marked, every real swing marked
    k.LAST_SETTLED = dt.date.today()
    y5, _, _ = k.yahoo("5d", "5m")
    y5, _ = k.rth(y5, 5)
    day = max(y5["date"])
    g = y5[y5["date"] == day].reset_index(drop=True)
    hh, ll = g["high"].to_numpy(float), g["low"].to_numpy(float)
    piv = fs.zigzag(hh, ll, 0.0010)
    piv = [i for i in piv if 0 < i < len(g) - 1]
    ts = [t.tz_convert(PT) for t in g["ts"]]
    fig, ax = plt.subplots(figsize=(17.5, 4.6))
    for i, (o, h_, l_, c_) in enumerate(zip(g["open"], hh, ll, g["close"])):
        col = "#1baf7a" if c_ >= o else "#e34948"
        ax.vlines(i, l_, h_, color=col, lw=1)
        ax.add_patch(matplotlib.patches.Rectangle((i - 0.3, min(o, c_)), 0.6, max(abs(c_ - o), 1e-4),
                                                   facecolor="white" if c_ >= o else col, edgecolor=col, lw=1, zorder=3))
    on45 = 0
    for i, t in enumerate(ts):
        if t.minute == 45:
            ax.axvline(i, color=ORANGE, lw=1, ls=":", zorder=1)
            ax.text(i, hh.max() + 0.25, t.strftime("%H:%M"), ha="center", fontsize=8.5, color=ORANGE)
    for i in piv:
        is_hi = hh[i] >= max(hh[max(0, i - 1)], hh[min(len(hh) - 1, i + 1)])
        y = hh[i] + 0.12 if is_hi else ll[i] - 0.12
        hit = ts[i].minute in (40, 45, 50)
        on45 += hit
        ax.plot(i, y, "v" if is_hi else "^", color=GOOD if hit else BAD, ms=10, zorder=4)
        ax.text(i, y + (0.18 if is_hi else -0.18), ts[i].strftime("%H:%M"), ha="center", va="bottom" if is_hi else "top",
                fontsize=8.5, color=INK, fontweight="bold")
    ax.set_xticks([i for i, t in enumerate(ts) if t.minute == 0])
    ax.set_xticklabels([t.strftime("%H:%M") for t in ts if t.minute == 0])
    ax.set_xlim(-1, len(g))
    ax.set_ylim(ll.min() - 0.6, hh.max() + 0.6)
    ax.set_title(f"{day:%a %b %d} — every :45 (orange dotted) and every swing turn of 0.10%+ "
                 f"(green = within 5 min of :45, red = not): {on45} of {len(piv)} on a :45", loc="left", fontsize=11, color=INK)
    ax.grid(axis="y", color=GRID)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    out["today"] = fig_png(fig)
    out["today_counts"] = (on45, len(piv), day)
    plt.close(fig)
    return out


def added_look():
    k.LAST_SETTLED = dt.date.today()
    days, src, info = k.load_bars()
    ds, H_, L_, C_, D_, M_ = fs.stack(days)
    piv = fs.pivots(H_, L_, M_, D_, 0.0010)
    return fs.hour45(piv, len(ds)), fs.hour45(piv, len(ds), (40, 45, 50))


def page(rep, ch) -> str:
    f = rep["fib"]
    p = f["primary_diff"]
    z = rep["hour45"]["0.0020"]["at_45"]
    z3 = rep["hour45"]["0.0030"]["at_45"]
    zw = rep["hour45"]["0.0020"]["window_40_50"]
    on45, npiv, day = ch["today_counts"]
    a1, a3 = ch["added"]
    fib_verdict = "YES" if p["lo"] > 0.02 else "NO"
    h_verdict = "YES" if z["lo"] > 1.10 else "NO"
    rows = "".join(f"<tr><td><b>{r}</b></td><td>{100 * v['respected']:.1f}%</td><td>{100 * v['neighbours']:.1f}%</td>"
                   f"<td>{100 * v['diff']['est']:+.1f} pts</td><td>{v['n']:,}</td></tr>" for r, v in f["per_level"].items())
    d = rep["data"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: {W}px {H}px; margin: 0 }} * {{ box-sizing: border-box }}
body {{ margin: 0; width: {W}px; background: #fcfcfb; color: {INK}; font: 15px/1.45 -apple-system, Helvetica, Arial, sans-serif }}
.wrap {{ padding: 26px 32px }} h1 {{ margin: 0; font-size: 27px }} .sub {{ color: {INK2} }}
.verdicts {{ display: flex; gap: 14px; margin: 16px 0 }} .v {{ flex: 1; border-radius: 12px; padding: 14px 18px; color: #fff }}
.v h3 {{ margin: 0 0 4px; font-size: 13px; letter-spacing: .05em; opacity: .9 }} .v .big {{ font-size: 21px; font-weight: 700 }}
.no {{ background: #3b3b38 }} .yes {{ background: #0f7d2f }}
.row {{ display: flex; gap: 16px; align-items: flex-start }} .card {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 12px 14px }}
.card img {{ display: block; width: 100% }} .half {{ flex: 1 }}
table {{ border-collapse: collapse; width: 100% }} td, th {{ padding: 4px 8px; border-bottom: 1px solid #f0efec; font-size: 13.5px; text-align: left }}
th {{ color: {INK2}; font-weight: 500; font-size: 12px }} h2 {{ font-size: 18px; margin: 18px 0 8px }} ul {{ margin: 6px 0 0 18px; padding: 0 }} li {{ margin: 4px 0 }}
.foot {{ color: {INK2}; font-size: 12.5px; margin-top: 14px }}
</style></head><body><div class="wrap">
<h1>Does SPY follow the Fibonacci levels — and turn at :45?</h1>
<div class="sub">SPY 5-minute bars, {d['from']} to {d['to']} ({d['sessions']:,} sessions) · IE Pro ONE v2's own auto-Fib ("Latest leg", 156 bars) · rules written and committed before the data was read</div>
<div class="verdicts">
<div class="v {'yes' if fib_verdict == 'YES' else 'no'}"><h3>FIBONACCI LEVELS</h3><div class="big">{'Respected more than other levels' if fib_verdict == 'YES' else 'No more respected than any other level'}</div>
Fib levels held {100 * f['respected_fib']:.1f}% of {f['n_fib']:,} touches; ordinary levels of the same legs held {100 * f['respected_control']:.1f}% — difference {100 * p['est']:+.1f} pts (95% range {100 * p['lo']:+.1f} to {100 * p['hi']:+.1f})</div>
<div class="v {'yes' if h_verdict == 'YES' else 'no'}"><h3>TURNS AT :45</h3><div class="big">{'More turns at :45' if h_verdict == 'YES' else 'No more turns at :45 than at any other minute'}</div>
{z['observed']:,} of {z['pivots']:,} swings turned on a :45 bar vs {z['expected']:,.0f} expected by chance — {z['ratio']:.2f}× (95% range {z['lo']:.2f}–{z['hi']:.2f}); bigger swings (0.30%): {z3['ratio']:.2f}×</div>
</div>
<div class="row"><div class="card half"><img src="data:image/png;base64,{ch['fib']}"></div>
<div class="card half"><img src="data:image/png;base64,{ch['hour']}"></div></div>
<h2>Your chart today, the way you read it</h2>
<div class="card"><img src="data:image/png;base64,{ch['today']}"></div>
<div class="row" style="margin-top:14px">
<div class="card half"><b>Each Fibonacci level against its two neighbours (±0.05 of the leg)</b>
<table><tr><th>level</th><th>held</th><th>neighbours held</th><th>difference</th><th>touches</th></tr>{rows}</table></div>
<div class="card half"><b>Why it feels true</b><ul>
<li>A leg has 7 drawn lines. Price is almost always near one of them, so every bounce lands "on a Fib".</li>
<li>Price holds at <i>any</i> level about {100 * f['respected_control']:.0f}% of the time — Fib or not. Holding at 0.618 looks special only when the misses aren't counted.</li>
<li>:40–:50 covers a quarter of every hour. Today {on45} of {npiv} turns fell there — the rest didn't, and those don't stick in memory.</li>
<li>Smaller swings (0.10%, the size you saw today — added after looking at today's chart): {a1['observed']:,} of {a1['pivots']:,} turned on :45 vs {a1['expected']:,.0f} expected — {a1['ratio']:.2f}× (95% {a1['lo']:.2f}–{a1['hi']:.2f}).</li>
<li>The earlier study of your 14 key times (1,549 days) found the same: turns 50.4% at your times vs 49.8% beside them.</li></ul></div></div>
<div class="foot">fib_hour45_study.py (pre-registered, commit 634568b) · results/fib_hour45_study.json · {f['events']:,} level touches; dropped: {f['dropped']} · :40–:50 window {zw['ratio']:.2f}× · RTH bars only (your chart also draws extended hours). A description of SPY, not a signal. Sim-only until Rule 7.</div>
</div></body></html>"""


def main():
    rep = json.loads((RES / "fib_hour45_study.json").read_text())
    ch = charts(rep)
    ch["added"] = added_look()
    hp = RES / "FIB_HOUR45_STUDY.html"
    hp.write_text(page(rep, ch))
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", f"--user-data-dir={RES / '.chrome'}"]
    subprocess.run(base + [f"--window-size={W},{H}", f"--screenshot={RES / 'FIB_HOUR45_STUDY.png'}", hp.as_uri()],
                   check=True, capture_output=True, timeout=90)
    subprocess.run(base + ["--no-pdf-header-footer", f"--print-to-pdf={RES / 'FIB_HOUR45_STUDY.pdf'}", hp.as_uri()],
                   check=True, capture_output=True, timeout=90)
    print("wrote", RES / "FIB_HOUR45_STUDY.png")


if __name__ == "__main__":
    main()

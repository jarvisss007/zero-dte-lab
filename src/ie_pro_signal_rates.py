"""Reproduces every signal-rate number quoted in PREREG_IE_PRO_PAPER.md from the committed seed bars.
Run: /opt/anaconda3/bin/python src/ie_pro_signal_rates.py > results/IE_PRO_SIGNAL_RATES_2026-10-09.txt
Reads only data/paper/bars_seed_2026-10-09.csv. Places nothing. Counts signals; computes no option P&L.
Warm-up: the first 5 sessions of the seed are excluded from the rates (EMA/RSI/ATR settling); they stay in the series.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ie_pro_one_trigger as T  # noqa: E402
import ie_pro_trigger as P  # noqa: E402
import paper_bars as B  # noqa: E402

SEED = HERE.parent / "data" / "paper" / "bars_seed_2026-10-09.csv"
WARMUP_SESSIONS = 5


def main() -> None:
    raw = B.load(SEED)
    df = B.clean(raw)
    days = sorted(df["ts"].dt.date.unique())
    counted = set(days[WARMUP_SESSIONS:])
    print(f"seed bars {len(raw)} -> clean {len(df)}; sessions {len(days)} ({days[0]} .. {days[-1]}); "
          f"rates over the {len(counted)} sessions after a {WARMUP_SESSIONS}-session warm-up")
    for name, run in (("v1 IE Pro (ie_pro_trigger, htf=developing)", lambda x: P.run(x, htf_mode="developing")),
                      ("IE Pro ONE sweep (ie_pro_one_trigger, htf=developing)", lambda x: T.run(x, htf_mode="developing"))):
        r = run(df)
        sig = r[(r.sig != 0) & r["ts"].dt.date.isin(counted)]
        trad = sig[[B.tradable_bar(t) for t in sig["ts"]]]
        per = trad.groupby(trad["ts"].dt.date).size().reindex(sorted(counted), fill_value=0)
        n = len(counted)
        print(f"\n{name}\n  all signals in the sessions: {len(sig)} (incl. premarket/untradable)"
              f"\n  tradable signals: {len(trad)} over {n} sessions = {len(trad) / n:.2f} per session"
              f"\n  sessions with 0 / 1 / 2 / 3 / 4+ tradable signals: "
              f"{(per == 0).sum()} / {(per == 1).sum()} / {(per == 2).sum()} / {(per == 3).sum()} / {(per >= 4).sum()}; max per session {per.max()}"
              f"\n  long {(trad.sig > 0).sum()}, short {(trad.sig < 0).sum()}")
        if name.startswith("v1"):
            gaps = trad.groupby(trad["ts"].dt.date)["ts"].apply(lambda s: s.diff().dropna().min() if len(s) > 1 else pd.NaT).dropna()
            print(f"  smallest gap between two tradable signals in one session: {gaps.min() if len(gaps) else 'n/a'} "
                  f"(spacing rule = 20 bars = 100 min)")


if __name__ == "__main__":
    main()

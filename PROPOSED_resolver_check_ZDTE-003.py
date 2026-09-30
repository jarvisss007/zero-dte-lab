# PROPOSED for ~/command-center/council/resolver.py (NOT applied here - the resolver's owner integrates it).
# Replaces check_zdte_recorder_starts_by_0950 as ZDTE-003's check: that one tests a 09:50 clock the ratified
# rule no longer names, so it would read red forever. Prefix everything _zdte003_ so nothing shadows resolver names.
# Register: attach as ZDTE-003's `check` ("zdte_first_snapshot_rule_holds").
import csv as _zdte003_csv, json as _zdte003_json, os as _zdte003_os

_ZDTE003_RATIFIED = "2026-09-30"   # agent-ledger rows from this date must carry snapshot_et + minutes_into_session

def _zdte003_first_fetch(lab, session):
    p = f"{lab}/data/chains/SPY_{session}.csv"
    if not _zdte003_os.path.exists(p):
        return None
    with open(p) as f:
        r = _zdte003_csv.DictReader(f)
        ts = [row["fetched_at_et"] for row in r if row.get("fetched_at_et")]
    return min(ts) if ts else None

def check_zdte_first_snapshot_rule_holds():
    """ZDTE-003 (ii), ratified 2026-09-29 under Anupam's delegation: Tracks C and D enter at the FIRST snapshot of
    the session (earliest fetched_at_et in data/chains/SPY_<date>.csv) or refuse; the agent ledger stamps at the
    first snapshot, or at the earliest fittable one naming the skipped snapshot, and from 2026-09-30 every row
    carries snapshot_et and minutes_into_session. Fails loud when a chain file needed to judge an entry is missing."""
    lab = _zdte003_os.path.expanduser("~/zero-dte-lab")
    bad, n = [], 0
    for book in ("track_c", "track_d"):
        try:
            rows = _zdte003_json.load(open(f"{lab}/data/{book}.json"))
        except Exception as e:
            return False, f"{book}.json unreadable ({type(e).__name__}) - cannot judge the entry rule"
        for r in rows:
            if str(r.get("outcome", "")).upper().startswith("VOID") or not r.get("entered_at_snapshot"):
                continue
            first = _zdte003_first_fetch(lab, r["session"])
            if first is None:
                bad.append(f"{r.get('structure_id')}: no chain file to judge its entry"); continue
            n += 1
            if r["entered_at_snapshot"] != first:
                bad.append(f"{r.get('structure_id')} entered {r['entered_at_snapshot'][11:]} but first snapshot was {first[11:]}")
    try:
        led = list(_zdte003_csv.DictReader(open(f"{lab}/agent/ledger.csv")))
    except Exception as e:
        return False, f"agent ledger unreadable ({type(e).__name__})"
    newrows = [r for r in led if (r.get("date") or "") >= _ZDTE003_RATIFIED]
    missing = [r["date"] for r in newrows if not (r.get("snapshot_et") or "").strip() or not (r.get("minutes_into_session") or "").strip()]
    if missing:
        bad.append(f"{len(missing)} agent-ledger row(s) since {_ZDTE003_RATIFIED} without snapshot_et/minutes_into_session: {missing[:4]}")
    if bad:
        return False, f"{len(bad)} breach(es) of the first-snapshot rule (ZDTE-003): " + "; ".join(bad[:4])
    return True, (f"{n} Track C/D entries all at the session's first snapshot; "
                  f"{len(newrows)} agent-ledger row(s) since {_ZDTE003_RATIFIED}, all carry snapshot_et + minutes_into_session")

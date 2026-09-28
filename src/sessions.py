"""NYSE SESSION CALENDAR — the estate's one source of truth for "is this date a session".

SESSION-001 (2026-09-05). Found while tracing a Saturday row on the equity curve: nothing
in the estate knew that Monday 2026-09-07 is Labor Day. Every writer keyed rows by the
wall clock or by `weekday() < 5`, so a holiday would have produced rows dated a day the
market never traded — the clock≠data family (THE_FIRM_BRAIN.md), rows≠days edition.

Rules:
  * a row's date is a SESSION date, never a calendar date;
  * a decision on a non-session day queues for the NEXT session (REG-PP-002);
  * the close pass keys its row to the last SETTLED session, never to "today".

Holidays are listed explicitly (NYSE published calendar); early closes are informational.
MIRROR: zero-dte-lab/src/sessions.py is a byte-identical copy (CI runs that repo alone);
the resolver check sessions_calendar fails if the two ever differ.

HORIZON GUARD — SESSION-006 (Anupam, ruled 2026-09-27, option (a) "refuse outside the range,
staged"). The calendar only KNOWS [CALENDAR_BEGINS, CALENDAR_ENDS]; outside it, "weekday and not a
listed holiday" is a guess presented as an answer (Christmas 2019 read as a session until
SESSION-005). The guard is symmetric in both directions, like sessions_nse.py after SESSION-004:
  * stage 1 (now, until REFUSE_FROM): an out-of-range date still gets the old weekday answer, but
    every such call WARNS on stderr, naming the date, and is recorded in OUT_OF_RANGE_SEEN — loud,
    never silent, so any caller that crosses the range is found before the flip;
  * stage 2 (from REFUSE_FROM, a Saturday before the ruled 2027-06-30 deadline, so the flip never
    lands mid-session): an out-of-range date RAISES CalendarExhausted. No opt-out exists; set
    SESSIONS_STRICT=1 to get stage 2 today (the self-test does).
Caller audit 2026-09-27: every tape starts on/after 2011-09-19, no book or ledger holds a date
past 2027-12-31, and no code probes a literal out-of-range date — so stage 1 should print nothing.
Before REFUSE_FROM: extend HOLIDAYS through 2028 (NYSE publishes it) and move CALENDAR_ENDS.

CLI:   python sessions.py            -> status line; exit 0 = session today, 1 = not
       python sessions.py --settled  -> ISO date of the last settled session
       python sessions.py 2026-09-07 -> status for that date
       python sessions.py --selftest -> asserts the SESSION-006 guard both ways; exit 0 = pass
"""
import atexit, datetime as dt, os, sys

HOLIDAYS = {
    # SESSION-005 EXTENDED 2026-09-18: coverage pushed back to the price panel's own
    # start (2011-09-12) so the horizon guard, when ruled, raises on nothing the estate
    # actually reads. Same two-source rule: no SPY bar on the tape AND reproduced by the
    # standard holiday rules computed without it. 45 of 47 matched both; the 2 that
    # matched only the tape are Hurricane Sandy, named below.
    # 2011
    "2011-11-24": "Thanksgiving Day", "2011-12-26": "Christmas Day (observed)",
    # 2012
    "2012-01-02": "New Year's Day (observed)", "2012-01-16": "Martin Luther King Jr. Day",
    "2012-02-20": "Presidents' Day", "2012-04-06": "Good Friday",
    "2012-05-28": "Memorial Day", "2012-07-04": "Independence Day",
    "2012-09-03": "Labor Day", "2012-10-29": "Hurricane Sandy (NYSE closed 2 days)",
    "2012-10-30": "Hurricane Sandy (NYSE closed 2 days)", "2012-11-22": "Thanksgiving Day",
    "2012-12-25": "Christmas Day",
    # 2013
    "2013-01-01": "New Year's Day", "2013-01-21": "Martin Luther King Jr. Day",
    "2013-02-18": "Presidents' Day", "2013-03-29": "Good Friday",
    "2013-05-27": "Memorial Day", "2013-07-04": "Independence Day",
    "2013-09-02": "Labor Day", "2013-11-28": "Thanksgiving Day",
    "2013-12-25": "Christmas Day",
    # 2014
    "2014-01-01": "New Year's Day", "2014-01-20": "Martin Luther King Jr. Day",
    "2014-02-17": "Presidents' Day", "2014-04-18": "Good Friday",
    "2014-05-26": "Memorial Day", "2014-07-04": "Independence Day",
    "2014-09-01": "Labor Day", "2014-11-27": "Thanksgiving Day",
    "2014-12-25": "Christmas Day",
    # 2015
    "2015-01-01": "New Year's Day", "2015-01-19": "Martin Luther King Jr. Day",
    "2015-02-16": "Presidents' Day", "2015-04-03": "Good Friday",
    "2015-05-25": "Memorial Day", "2015-07-03": "Independence Day (observed)",
    "2015-09-07": "Labor Day", "2015-11-26": "Thanksgiving Day",
    "2015-12-25": "Christmas Day",
    # 2016
    "2016-01-01": "New Year's Day", "2016-01-18": "Martin Luther King Jr. Day",
    "2016-02-15": "Presidents' Day", "2016-03-25": "Good Friday",
    "2016-05-30": "Memorial Day", "2016-07-04": "Independence Day",
    "2016-09-05": "Labor Day",
    # SESSION-005 (2026-09-16): this dict held 2026-27 only, and is_session() has NO
    # horizon guard — so every NYSE holiday before 2026 answered is_session=True.
    # Christmas 2019, July 4 2017 and 95 others read as trading sessions. Verified two
    # independent ways before being added, the standard this estate already demands:
    # (1) the SPX tape has no bar on the date, (2) the date is reproduced by the standard
    # US market holiday rules computed WITHOUT reference to the tape. 95 of 97 matched
    # both; the 2 that matched only the tape are the presidential days of mourning below,
    # named explicitly rather than smuggled in.
    # SESSION-005, second pass (Resolver, 2026-09-16): the first pass verified against an
    # SPX tape that begins 2016-09-02 and reported "0 disagreements" — true of THAT tape,
    # while the estate's own longer tape (strategy-lab/data/close.csv, from 2011-09-12)
    # still had 46 weekdays where this calendar called a closed day a session. Same two
    # sources as above: 44 matched both the tape's missing bar and the computed rules, and
    # the 2 that matched the tape alone are Hurricane Sandy, named here rather than
    # smuggled in. The tape also corrected the RULES once: NYSE traded 2021-12-31, so a
    # Saturday New Year's Day is NOT observed on the Friday before — that date is absent
    # here by construction, since only dates the tape shows as closed were ever added.
    # 2011
    "2011-11-24": "Thanksgiving Day", "2011-12-26": "Christmas Day (observed)",
    # 2012
    "2012-01-02": "New Year's Day (observed)", "2012-01-16": "Martin Luther King Jr. Day",
    "2012-02-20": "Presidents' Day", "2012-04-06": "Good Friday",
    "2012-05-28": "Memorial Day", "2012-07-04": "Independence Day",
    "2012-09-03": "Labor Day", "2012-10-29": "Hurricane Sandy",
    "2012-10-30": "Hurricane Sandy", "2012-11-22": "Thanksgiving Day",
    "2012-12-25": "Christmas Day",
    # 2013
    "2013-01-01": "New Year's Day", "2013-01-21": "Martin Luther King Jr. Day",
    "2013-02-18": "Presidents' Day", "2013-03-29": "Good Friday",
    "2013-05-27": "Memorial Day", "2013-07-04": "Independence Day",
    "2013-09-02": "Labor Day", "2013-11-28": "Thanksgiving Day",
    "2013-12-25": "Christmas Day",
    # 2014
    "2014-01-01": "New Year's Day", "2014-01-20": "Martin Luther King Jr. Day",
    "2014-02-17": "Presidents' Day", "2014-04-18": "Good Friday",
    "2014-05-26": "Memorial Day", "2014-07-04": "Independence Day",
    "2014-09-01": "Labor Day", "2014-11-27": "Thanksgiving Day",
    "2014-12-25": "Christmas Day",
    # 2015
    "2015-01-01": "New Year's Day", "2015-01-19": "Martin Luther King Jr. Day",
    "2015-02-16": "Presidents' Day", "2015-04-03": "Good Friday",
    "2015-05-25": "Memorial Day", "2015-07-03": "Independence Day (observed)",
    "2015-09-07": "Labor Day", "2015-11-26": "Thanksgiving Day",
    "2015-12-25": "Christmas Day",
    # 2016
    "2016-01-01": "New Year's Day", "2016-01-18": "Martin Luther King Jr. Day",
    "2016-02-15": "Presidents' Day", "2016-03-25": "Good Friday",
    "2016-05-30": "Memorial Day", "2016-07-04": "Independence Day",
    # 2016  — tape-verified from 2016-09-02 (SPX history begins here)
    "2016-09-05": "Labor Day", "2016-11-24": "Thanksgiving Day",
    "2016-12-26": "Christmas Day (observed)",
    # 2017
    "2017-01-02": "New Year's Day (observed)", "2017-01-16": "Martin Luther King Jr. Day",
    "2017-02-20": "Presidents' Day", "2017-04-14": "Good Friday",
    "2017-05-29": "Memorial Day", "2017-07-04": "Independence Day",
    "2017-09-04": "Labor Day", "2017-11-23": "Thanksgiving Day",
    "2017-12-25": "Christmas Day",
    # 2018
    "2018-01-01": "New Year's Day", "2018-01-15": "Martin Luther King Jr. Day",
    "2018-02-19": "Presidents' Day", "2018-03-30": "Good Friday",
    "2018-05-28": "Memorial Day", "2018-07-04": "Independence Day",
    "2018-09-03": "Labor Day", "2018-11-22": "Thanksgiving Day",
    "2018-12-05": "National Day of Mourning (George H. W. Bush)", "2018-12-25": "Christmas Day",
    # 2019
    "2019-01-01": "New Year's Day", "2019-01-21": "Martin Luther King Jr. Day",
    "2019-02-18": "Presidents' Day", "2019-04-19": "Good Friday",
    "2019-05-27": "Memorial Day", "2019-07-04": "Independence Day",
    "2019-09-02": "Labor Day", "2019-11-28": "Thanksgiving Day",
    "2019-12-25": "Christmas Day",
    # 2020
    "2020-01-01": "New Year's Day", "2020-01-20": "Martin Luther King Jr. Day",
    "2020-02-17": "Presidents' Day", "2020-04-10": "Good Friday",
    "2020-05-25": "Memorial Day", "2020-07-03": "Independence Day (observed)",
    "2020-09-07": "Labor Day", "2020-11-26": "Thanksgiving Day",
    "2020-12-25": "Christmas Day",
    # 2021
    "2021-01-01": "New Year's Day", "2021-01-18": "Martin Luther King Jr. Day",
    "2021-02-15": "Presidents' Day", "2021-04-02": "Good Friday",
    "2021-05-31": "Memorial Day", "2021-07-05": "Independence Day (observed)",
    "2021-09-06": "Labor Day", "2021-11-25": "Thanksgiving Day",
    "2021-12-24": "Christmas Day (observed)",
    # 2022
    "2022-01-17": "Martin Luther King Jr. Day", "2022-02-21": "Presidents' Day",
    "2022-04-15": "Good Friday", "2022-05-30": "Memorial Day",
    "2022-06-20": "Juneteenth (observed)", "2022-07-04": "Independence Day",
    "2022-09-05": "Labor Day", "2022-11-24": "Thanksgiving Day",
    "2022-12-26": "Christmas Day (observed)",
    # 2023
    "2023-01-02": "New Year's Day (observed)", "2023-01-16": "Martin Luther King Jr. Day",
    "2023-02-20": "Presidents' Day", "2023-04-07": "Good Friday",
    "2023-05-29": "Memorial Day", "2023-06-19": "Juneteenth",
    "2023-07-04": "Independence Day", "2023-09-04": "Labor Day",
    "2023-11-23": "Thanksgiving Day", "2023-12-25": "Christmas Day",
    # 2024
    "2024-01-01": "New Year's Day", "2024-01-15": "Martin Luther King Jr. Day",
    "2024-02-19": "Presidents' Day", "2024-03-29": "Good Friday",
    "2024-05-27": "Memorial Day", "2024-06-19": "Juneteenth",
    "2024-07-04": "Independence Day", "2024-09-02": "Labor Day",
    "2024-11-28": "Thanksgiving Day", "2024-12-25": "Christmas Day",
    # 2025
    "2025-01-01": "New Year's Day", "2025-01-09": "National Day of Mourning (Jimmy Carter)",
    "2025-01-20": "Martin Luther King Jr. Day", "2025-02-17": "Presidents' Day",
    "2025-04-18": "Good Friday", "2025-05-26": "Memorial Day",
    "2025-06-19": "Juneteenth", "2025-07-04": "Independence Day",
    "2025-09-01": "Labor Day", "2025-11-27": "Thanksgiving Day",
    "2025-12-25": "Christmas Day",
    # 2026
    "2026-01-01": "New Year's Day", "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Presidents' Day", "2026-04-03": "Good Friday", "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth", "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day", "2026-11-26": "Thanksgiving Day", "2026-12-25": "Christmas Day",
    # 2027
    "2027-01-01": "New Year's Day", "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Presidents' Day", "2027-03-26": "Good Friday", "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth (observed)", "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day", "2027-11-25": "Thanksgiving Day", "2027-12-24": "Christmas Day (observed)",
}
EARLY_CLOSES = {"2026-11-27": "13:00 ET", "2026-12-24": "13:00 ET", "2027-11-26": "13:00 ET"}
CALENDAR_BEGINS = "2011-09-12"   # SESSION-006: the first day of the estate's longest tape (strategy-lab/data/close.csv); SESSION-005 verified holidays from here, not from 2011-01-01
CALENDAR_ENDS = "2027-12-31"
REFUSE_FROM = "2027-06-26"       # SESSION-006 stage 2: from this (PT) date an out-of-range date raises instead of warning
CLOSE_PT = (13, 0)          # 16:00 ET on a full session
SETTLED_PT = (13, 5)        # the close is settled a few minutes after the bell


class CalendarExhausted(ValueError):
    """SESSION-006: asked about a date this calendar has no evidence for."""


OUT_OF_RANGE_SEEN = set()   # SESSION-006 stage 1: every out-of-range date asked this process (the audit trail)
_WARN_LINES = 5


def _now_pt():
    """The PT wall clock regardless of the machine's zone (SETTLE-002: GitHub runners are UTC, and the
    settled cutoff is written in PT). Falls back to the local clock only if no tz database exists."""
    try:
        import zoneinfo
        return dt.datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles")).replace(tzinfo=None)
    except Exception:
        return dt.datetime.now()


def _strict():
    return os.environ.get("SESSIONS_STRICT") == "1" or _now_pt().date().isoformat() >= REFUSE_FROM


def _check_horizon(d):
    """SESSION-006: symmetric — the floor and the ceiling are treated identically (no one-sided guard)."""
    iso = d.isoformat()[:10]
    if CALENDAR_BEGINS <= iso <= CALENDAR_ENDS:
        return
    side = "before the floor" if iso < CALENDAR_BEGINS else "past the end"
    msg = (f"sessions.py has no calendar for {iso} ({side}; it knows {CALENDAR_BEGINS}..{CALENDAR_ENDS}). "
           f"A weekday outside that range is NOT evidence of a session.")
    if _strict():
        raise CalendarExhausted(msg + " Refused (SESSION-006).")
    if iso not in OUT_OF_RANGE_SEEN:
        OUT_OF_RANGE_SEEN.add(iso)
        if len(OUT_OF_RANGE_SEEN) <= _WARN_LINES:
            print(f"SESSION-006 WARNING: {msg} Answering weekdays-only as a GUESS; from {REFUSE_FROM} this raises "
                  f"CalendarExhausted. Caller: fix it or extend HOLIDAYS.", file=sys.stderr)


@atexit.register
def _report_out_of_range():
    if len(OUT_OF_RANGE_SEEN) > _WARN_LINES:
        print(f"SESSION-006 WARNING: {len(OUT_OF_RANGE_SEEN)} out-of-range dates were answered as guesses this run "
              f"({min(OUT_OF_RANGE_SEEN)}..{max(OUT_OF_RANGE_SEEN)}); from {REFUSE_FROM} each one raises.", file=sys.stderr)


def _d(x):
    if isinstance(x, dt.datetime):   # SESSION-006 audit: a datetime's isoformat() never matched a HOLIDAYS key, so a holiday datetime read as a session
        return x.date()
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x)[:10])


def is_session(d):
    d = _d(d)
    _check_horizon(d)   # SESSION-006
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def why_closed(d):
    d = _d(d)
    _check_horizon(d)   # SESSION-006
    if d.weekday() >= 5:
        return "weekend"
    return HOLIDAYS.get(d.isoformat(), "")


def last_session(d, inclusive=True):
    d = _d(d)
    if not inclusive:
        d -= dt.timedelta(days=1)
    while not is_session(d):
        d -= dt.timedelta(days=1)
    return d


def next_session(d, inclusive=False):
    d = _d(d)
    if not inclusive:
        d += dt.timedelta(days=1)
    while not is_session(d):
        d += dt.timedelta(days=1)
    return d


def roll_to_session(d):
    """A check/exit date that lands on a non-session rolls FORWARD to the next session."""
    return next_session(d, inclusive=True)


def settled_session(now=None, cutoff=SETTLED_PT):
    """The most recent session whose close is settled (PT clock): today if today is a
    session and the clock is past `cutoff`, else the previous session."""
    now = now or _now_pt()   # SETTLE-002: the cutoff is PT, so read the PT clock even on a UTC runner (identical on the Mac)
    d = now.date()
    if is_session(d) and (now.hour, now.minute) >= cutoff:
        return d
    return last_session(d, inclusive=False)


def sessions_between(a, b):
    """Sessions strictly after a and up to and including b."""
    a, b = _d(a), _d(b); out = []
    d = a + dt.timedelta(days=1)
    while d <= b:
        if is_session(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def status_line(d=None):
    d = _d(d or dt.date.today())
    if is_session(d):
        s = f"MARKET: {d} is a session" + (f" (EARLY CLOSE {EARLY_CLOSES[d.isoformat()]})" if d.isoformat() in EARLY_CLOSES else "")
    else:
        s = f"MARKET: CLOSED {d} ({why_closed(d)}) — no session; write no rows dated today; next session {next_session(d)}"
    if d.isoformat() > CALENDAR_ENDS:
        s += " · WARNING: holiday calendar ends " + CALENDAR_ENDS + " — extend sessions.py"
    return s


def _selftest():
    """SESSION-006: the guard refuses BOTH ends under stage 2 and warns (never silently answers) under stage 1."""
    global _strict
    real = _strict
    try:
        _strict = lambda: True
        for w in ("2011-09-09", "2008-12-25", "2028-01-17", "2030-07-04"):
            for fn in (is_session, why_closed):
                try:
                    fn(w)
                except CalendarExhausted:
                    continue
                raise AssertionError(f"{fn.__name__}({w}) answered instead of refusing")
        assert is_session(CALENDAR_BEGINS) and is_session("2027-12-31") and not is_session("2019-12-25")
        _strict = lambda: False
        OUT_OF_RANGE_SEEN.clear()
        assert is_session("2030-07-04") is True and "2030-07-04" in OUT_OF_RANGE_SEEN   # stage 1: answers, but on the record
        assert not is_session(dt.datetime(2026, 9, 7, 10, 0))   # Labor Day as a datetime is not a session
        OUT_OF_RANGE_SEEN.clear()
    finally:
        _strict = real
    print(f"sessions selftest: PASS — {CALENDAR_BEGINS}..{CALENDAR_ENDS}; both ends refuse under stage 2 "
          f"(from {REFUSE_FROM}); stage 1 warns and records")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest(); sys.exit(0)
    if "--settled" in sys.argv:
        print(settled_session().isoformat()); sys.exit(0)
    arg = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = _d(arg) if arg else dt.date.today()
    print(status_line(d)); sys.exit(0 if is_session(d) else 1)

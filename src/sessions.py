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

When the list runs out the calendar degrades to weekdays-only and SAYS so on the CLI.

CLI:   python sessions.py            -> status line; exit 0 = session today, 1 = not
       python sessions.py --settled  -> ISO date of the last settled session
       python sessions.py 2026-09-07 -> status for that date
"""
import datetime as dt, sys

HOLIDAYS = {
    # SESSION-005 (2026-09-16): this dict held 2026-27 only, and is_session() has NO
    # horizon guard — so every NYSE holiday before 2026 answered is_session=True.
    # Christmas 2019, July 4 2017 and 95 others read as trading sessions. Verified two
    # independent ways before being added, the standard this estate already demands:
    # (1) the SPX tape has no bar on the date, (2) the date is reproduced by the standard
    # US market holiday rules computed WITHOUT reference to the tape. 95 of 97 matched
    # both; the 2 that matched only the tape are the presidential days of mourning below,
    # named explicitly rather than smuggled in.
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
CALENDAR_ENDS = "2027-12-31"
CLOSE_PT = (13, 0)          # 16:00 ET on a full session
SETTLED_PT = (13, 5)        # the close is settled a few minutes after the bell


def _d(x):
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x)[:10])


def is_session(d):
    d = _d(d)
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def why_closed(d):
    d = _d(d)
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
    now = now or dt.datetime.now()
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


if __name__ == "__main__":
    if "--settled" in sys.argv:
        print(settled_session().isoformat()); sys.exit(0)
    arg = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = _d(arg) if arg else dt.date.today()
    print(status_line(d)); sys.exit(0 if is_session(d) else 1)

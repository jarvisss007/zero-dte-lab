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

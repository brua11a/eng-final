"""The university's time zone.

Class and registration-turn hours are wall-clock times (LOCAL TIME / `time`): a class at 13:15
is at 13:15 in both winter and summer. They get an offset only when combined with a date,
in this zone (Cypher: `datetime({date, time, timezone: 'Europe/Warsaw'})`,
SQL: `(date + time) AT TIME ZONE 'Europe/Warsaw'`). Moments (joined, submit, ...) stay zoned.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Warsaw"
ZONE = ZoneInfo(TIMEZONE)


def local_time(value: time) -> str:
    """Wall-clock time to store; an offset sent by the client is dropped, as it has no date."""
    return value.replace(tzinfo=None).isoformat()


def zoned_datetime(value: datetime) -> str:
    """A moment; a value without an offset is taken as university time on that date."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZONE)
    return value.isoformat()

# conversion/noaa-requests/noaa-py/noaapy/dates/dates.py
from dataclasses import dataclass
from datetime import datetime
from typing import List


class TimeSegment:

@dataclass
class TimeSegments:
    starts: List[str]
    ends: List[str]


@dataclass
class DateRange:
    observed: TimeSegments
    prediction: TimeSegments


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d %H:%M")

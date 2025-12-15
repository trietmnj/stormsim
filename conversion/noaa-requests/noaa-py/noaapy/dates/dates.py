# conversion/noaa-requests/noaa-py/noaapy/dates/dates.py
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd


@dataclass
class DateRanges:
    observed: List[pd.Interval]
    prediction: List[pd.Interval]


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d %H:%M")

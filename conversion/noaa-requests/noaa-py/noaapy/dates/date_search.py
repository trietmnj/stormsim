# conversion/noaa-requests/noaa-py/noaapy/dates/date_search.py
import datetime as dt
from typing import List, Tuple

import pandas as pd

from .dates import DateRanges


def get_valid_station_interval(
    dates: DateRanges,
    request: pd.Interval,
    indices: List[int],
) -> Tuple[List[int], dt.datetime, dt.datetime, bool]:
    """
    Given a requested datetime interval and a subset of availability ranges,
    determine the valid requested range for a station.

    Returns:
        (valid_indices, valid_start, valid_end, invalid)

    Notes:
    - dates["start_date"][i] / dates["end_date"][i] are strings; only the first 19
      characters are used ("YYYY-mm-dd HH:MM:SS").
    - If the request does not overlap any availability range -> invalid=True.
    - If the request is fully contained by one or more availability ranges -> return those indices.
    - If the request partially overlaps -> clamp start/end to availability boundaries.
    """
    req_start = request.left.to_pydatetime()
    req_end = request.right.to_pydatetime()

    def parse(s: str) -> dt.datetime:
        return dt.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")

    windows = [(parse(dates["start_date"][i]), parse(dates["end_date"][i])) for i in indices]

    # Any overlap at all? (inclusive endpoints)
    def overlaps(a_start: dt.datetime, a_end: dt.datetime) -> bool:
        return not (req_end < a_start or req_start > a_end)

    overlapping = [(i, w) for i, w in zip(indices, windows) if overlaps(*w)]
    if not overlapping:
        return indices, req_start, req_end, True

    # Fully contained in a window?
    def contains(w_start: dt.datetime, w_end: dt.datetime) -> bool:
        return w_start <= req_start and req_end <= w_end

    containing = [i for i, (w_start, w_end) in overlapping if contains(w_start, w_end)]
    if containing:
        return containing, req_start, req_end, False

    # Partial overlap: clamp the request to the union of overlapping windows.
    starts = [w_start for _, (w_start, _) in overlapping]
    ends = [w_end for _, (_, w_end) in overlapping]

    clamped_start = max(req_start, min(starts))
    clamped_end = min(req_end, max(ends))

    # Safety: clamping should preserve overlap, but guard anyway.
    invalid = clamped_start > clamped_end
    return indices, clamped_start, clamped_end, invalid

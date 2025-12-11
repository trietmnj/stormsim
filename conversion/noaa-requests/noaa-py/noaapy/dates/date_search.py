# conversion/noaa-requests/noaa-py/noaapy/dates/date_search.py
import datetime
from typing import Dict, List, Tuple

from .dates import DateRange


def get_valid_station_interval(
    dates: DateRange,
    d_beg: datetime.datetime,
    d_end: datetime.datetime,
    idx: List[int],
) -> Tuple[List[int], datetime.datetime, datetime.datetime, bool]:
    """
    Get valid date range for station within the data request date range
    d_struct["start_date"], d_struct["end_date"]:
        lists of 'yyyy-mm-dd HH:MM:SS' strings
    indx:
        list of indices into those lists (0-based)
    """
    invalid_flag = False

    # Parse only the ranges we care about (those in indx)
    starts = [
        datetime.datetime.strptime(dates["start_date"][i][:19], "%Y-%m-%d %H:%M:%S")
        for i in idx
    ]
    ends = [
        datetime.datetime.strptime(dates["end_date"][i][:19], "%Y-%m-%d %H:%M:%S")
        for i in idx
    ]

    # Flags for whether d_beg / d_end fall inside each interval
    beg_inside = [start <= d_beg <= end for start, end in zip(starts, ends)]
    end_inside = [start <= d_end <= end for start, end in zip(starts, ends)]

    # 0 = neither inside, 1 = one inside, 2 = both inside
    overlap_score = [int(b) + int(e) for b, e in zip(beg_inside, end_inside)]

    # Case 1: no overlap at all
    if all(score == 0 for score in overlap_score):
        invalid_flag = True

    # Case 2: some interval fully contains [d_beg, d_end]
    elif any(score == 2 for score in overlap_score):
        # choose all such indices, mapped back to original d_struct indices
        idx = [idx[i] for i, score in enumerate(overlap_score) if score == 2]

    # Case 3: partial overlap – adjust d_beg or d_end to nearest boundary
    elif any(score == 1 for score in overlap_score):
        # if start is outside all intervals, snap d_beg to nearest start
        if not any(beg_inside):
            d_beg = min(starts, key=lambda t: abs(t - d_beg))
        # if end is outside all intervals, snap d_end to nearest end
        elif not any(end_inside):
            d_end = min(ends, key=lambda t: abs(t - d_end))

    return idx, d_end, d_beg, invalid_flag

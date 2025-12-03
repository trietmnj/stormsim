from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any


def date_range_segmentation(
    d_struct: Dict[str, List[str]],
    flag1: str,
    indx: List[int],
) -> Tuple[List[List[str]], List[List[str]]]:
    """
    Python translation of date_range_segmentation.m

    Parameters
    ----------
    d_struct : dict
        Dictionary with:
            d_struct["startDate"] : list of 'yyyy-mm-dd HH:MM:SS' strings
            d_struct["endDate"]   : list of 'yyyy-mm-dd HH:MM:SS' strings
    flag1 : str
        '6', '6p' for 6-minute data; anything else is treated as hourly/HiLo.
    indx : list of int
        Indices of station records to segment (0-based in Python).

    Returns
    -------
    st_dates, end_dates : list of list of str
        For each index in `indx`, you get:
            st_dates[j] : list of 'yyyymmdd HH:MM' start times for each segment
            end_dates[j]: list of 'yyyymmdd HH:MM' end times for each segment
    """

    # 6-min products: 30 days per download, else: 364 days per download
    if flag1 in ("6", "6p"):
        dt_s = timedelta(days=30)
    else:
        dt_s = timedelta(days=364)

    start_date_list = d_struct["startDate"]
    end_date_list = d_struct["endDate"]

    st_dates: List[List[str]] = []
    end_dates: List[List[str]] = []

    def parse_dt(s: str) -> datetime:
        # MATLAB uses s(1:end-4) to drop fractional seconds / TZ if present
        # assume first 19 chars are 'yyyy-mm-dd HH:MM:SS'
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")

    def fmt_dt(dt: datetime) -> str:
        # MATLAB: 'yyyymmdd HH:MM'
        return dt.strftime("%Y%m%d %H:%M")

    for idx in indx:
        start_str = start_date_list[idx]
        end_str = end_date_list[idx]

        start_dt = parse_dt(start_str)
        end_dt = parse_dt(end_str)

        # Build the dummy time vector with suggested dt_s
        dummy: List[datetime] = [start_dt]
        while dummy[-1] + dt_s < end_dt:
            dummy.append(dummy[-1] + dt_s)

        # If final date doesn't coincide with station end date, fix it
        if dummy[-1] != end_dt:
            dummy.append(end_dt)

        # Segment start/end lists:
        # dummy[0]→dummy[1], dummy[1]→dummy[2], ..., dummy[-2]→dummy[-1]
        starts = [fmt_dt(t) for t in dummy[:-1]]
        ends = [fmt_dt(t) for t in dummy[1:]]

        st_dates.append(starts)
        end_dates.append(ends)

    return st_dates, end_dates

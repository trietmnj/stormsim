# conversion/noaa-requests/noaa-py/noaapy/download_segmentation.py
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd

import noaapy
from .dates import DateRanges


def parse_dates(station, interval_param: str, idx: int) -> DateRanges:
    """
    Parse the segmentation date ranges for a given station based on the specified flag.
    Args:
        station (dict): The station data containing segmentation information.
        intervalParam: A flag indicating the type of segmentation to retrieve.
        idx (list): A list of indices to specify which segments to retrieve.
    Returns:
        Tuple[list, list, list, list]: Four lists containing start and end dates for segments
                                        and predictions.
    """
    if interval_param not in noaapy.globals.PRODUCT_LABELS:
        raise ValueError(
            f"intervalParam={interval_param} must be in {list(noaapy.globals.PRODUCT_LABELS.keys())}"
        )

    if interval_param != "m":
        start_dates, end_dates = _date_range_segmentation(station, interval_param, idx)
    else:
        start_dates = station["start_date"][idx]
        end_dates = station["end_date"][idx]
        start_dates = [date[:19] for date in start_dates]
        end_dates = [date[:19] for date in end_dates]
        start_dates = [
            datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d %H:%M")
            for date in start_dates
        ]
        end_dates = [
            datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d %H:%M")
            for date in end_dates
        ]

    prediction_start_dates, prediction_end_dates = _segment_prediction_date_range(
        station, idx
    )

    return DateRange(
        observed=pd.Interval( start_dates, end_dates,),
        prediction=TimeSegments(
            starts=prediction_start_dates,
            ends=prediction_end_dates,
        ),
    )


def _segment_prediction_date_range(
    d_struct: Dict[str, List[str]],
    indx: List[int],
) -> Tuple[List[List[str]], List[List[str]]]:
    """
    Python translation of date_range_segmentation_predictions_V2.m

    Parameters
    ----------
    d_struct : dict
        Must contain:
            d_struct["startDate"] : list of 'yyyy-mm-dd HH:MM:SS' strings
            d_struct["endDate"]   : list of 'yyyy-mm-dd HH:MM:SS' strings
    indx : list of int
        Indices into the above arrays (0-based in Python).

    Returns
    -------
    st_dates, end_dates : list of list of str
        Each is a list with a single inner list:
            st_dates[0][k] : 'yyyymmdd HH:MM' start for segment k
            end_dates[0][k]: 'yyyymmdd HH:MM' end   for segment k
    """

    # Suggested dt: 30 days (predictions limited to 31 days per request)
    dt_s = timedelta(days=30)

    # Get station-wide start & end using first and last indices
    start_str = d_struct["startDate"][indx[0]]
    end_str = d_struct["endDate"][indx[-1]]

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)

    # Build dummy time vector with 30-day spacing
    dummy: List[datetime] = [start_dt]
    while dummy[-1] + dt_s < end_dt:
        dummy.append(dummy[-1] + dt_s)

    # Ensure the last element equals the station end date
    if dummy[-1] != end_dt:
        dummy.append(end_dt)

    # Segment pairs: dummy[0]→dummy[1], dummy[1]→dummy[2], ..., dummy[-2]→dummy[-1]
    starts = [fmt_dt(t) for t in dummy[:-1]]
    ends = [fmt_dt(t) for t in dummy[1:]]

    start_dates = [starts]
    end_dates = [ends]

    return start_dates, end_dates


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d %H:%M")


def _date_range_segmentation(
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

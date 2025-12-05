# noaa-requests/noaa-py/noaapy/download_segmentation.py
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass


import noaapy


@dataclass
class DateRange:
    start_dates: List[str]
    end_dates: List[str]
    prediction_start_dates: List[str]
    prediction_end_dates: List[str]


def parse_dates(station, interval_param: str, idx: int) -> DateRange:
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
        start_dates, end_dates = noaapy.date.date_range_segmentation(
            station, interval_param, idx
        )
    else:
        start_dates = station["start_date"][idx]
        end_dates = station["end_date"][idx]
        start_dates = [date[:19] for date in start_dates]
        end_dates = [date[:19] for date in end_dates]
        start_dates = [
            datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
                "%Y%m%d %H:%M"
            )
            for date in start_dates
        ]
        end_dates = [
            datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
                "%Y%m%d %H:%M"
            )
            for date in end_dates
        ]

    prediction_start_dates, prediction_end_dates = _segment_prediction_date_range(
        station, idx
    )

    return DateRange(
        start_dates=start_dates,
        end_dates=end_dates,
        prediction_start_dates=prediction_start_dates,
        prediction_end_dates=prediction_end_dates,
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

    # MATLAB uses s(1:end-4) → first 19 chars: 'yyyy-mm-dd HH:MM:SS'
    def parse_dt(s: str) -> datetime:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")

    def fmt_dt(dt: datetime) -> str:
        # MATLAB: 'yyyymmdd HH:MM'
        return dt.strftime("%Y%m%d %H:%M")

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

    # Match MATLAB structure: 1x1 cell with a vector inside
    start_dates = [starts]
    end_dates = [ends]

    return start_dates, end_dates

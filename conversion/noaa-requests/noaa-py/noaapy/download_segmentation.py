# noaa-requests/noaa-py/noaapy/download_segmentation.py
import datetime
from typing import Tuple

import noaapy


def download_segmentation(
    station, flag1: bool, idx: int
) -> Tuple[list, list, list, list]:
    """
    Downloads the segmentation date ranges for a given station based on the specified flag.
    Args:
        station (dict): The station data containing segmentation information.
        flag1 (bool): A flag indicating the type of segmentation to retrieve.
        indx (list): A list of indices to specify which segments to retrieve.
    Returns:
        Tuple[list, list, list, list]: Four lists containing start and end dates for segments
                                        and predictions.
    """
    if flag1 != "m":
        st_dates, end_dates = noaapy.date.date_range_segmentation(station, flag1, idx)
    else:
        print(type(idx))
        print(type(idx[0]))
        print(station)
        st_dates = station["start_date"][idx]
        end_dates = station["end_date"][idx]
        st_dates = [date[:19] for date in st_dates]
        end_dates = [date[:19] for date in end_dates]
        st_dates = [
            datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
                "%Y%m%d %H:%M"
            )
            for date in st_dates
        ]
        end_dates = [
            datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
                "%Y%m%d %H:%M"
            )
            for date in end_dates
        ]

    st_dates_p, end_dates_p = noaapy.date.date_range_segmentation_predictions_v2(
        station, idx
    )

    return st_dates, end_dates, st_dates_p, end_dates_p

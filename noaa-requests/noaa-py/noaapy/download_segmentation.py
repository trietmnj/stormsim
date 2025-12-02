# noaa-requests/noaa-py/noaapy/download_segmentation.py
import datetime

import noaapy


def download_segmentation(d_struct, flag1, indx):
    if flag1 != "m":
        st_dates, end_dates = noaapy.date.date_range_segmentation(d_struct, flag1, indx)
    else:
        st_dates = d_struct["start_date"][indx]
        end_dates = d_struct["end_date"][indx]
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
        d_struct, indx
    )

    return st_dates, end_dates, st_dates_p, end_dates_p

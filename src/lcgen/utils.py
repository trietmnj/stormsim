import datetime as dt
import numpy as np


def doy_to_month_day(year: int, doy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorized DOY → (month, day) converter.
    """
    base = dt.datetime(year, 1, 1)

    # Convert DOY → datetime
    dt_arr = np.array([base + dt.timedelta(days=int(d) - 1) for d in doy])

    month = np.array([x.month for x in dt_arr], dtype=int)
    day = np.array([x.day for x in dt_arr], dtype=int)

    return month, day

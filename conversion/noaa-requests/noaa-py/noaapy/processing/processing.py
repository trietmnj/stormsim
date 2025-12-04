import numpy as np
import pandas as pd


def synthesize_nan_series(
    begin_str: str,
    end_str: str,
    flag1: str,
) -> pd.DataFrame:
    """
    Create a synthetic DateTime / NaN WaterLevel series when the
    downloaded table is empty or malformed.
    """
    u_bound = pd.to_datetime(begin_str, format="%Y%m%d %H:%M")
    l_bound = pd.to_datetime(end_str, format="%Y%m%d %H:%M")

    # timestep: use 6-minute where appropriate, else hourly
    freq = "6min" if "6" in flag1 else "1H"

    # datetime vector from u_bound to l_bound, then drop the first
    datetimes = pd.date_range(start=u_bound, end=l_bound, freq=freq)[1:]
    water_level = np.full(shape=len(datetimes), fill_value=np.nan)

    return pd.DataFrame({"DateTime": datetimes, "WaterLevel": water_level})


def normalize_non_monthly_wl_table(wltable: pd.DataFrame) -> pd.DataFrame:
    """
    Take the first two columns from the NOAA non-monthly table
    and rename them to DateTime / WaterLevel.
    """
    subset = wltable.iloc[:, :2].copy()
    subset.columns = ["DateTime", "WaterLevel"]
    subset["DateTime"] = pd.to_datetime(subset["DateTime"])
    return subset


def process_monthly_table(wltable: pd.DataFrame) -> pd.DataFrame:
    """
    Map NOAA monthly_mean response into DateTime / WaterLevel with
    a regular monthly (MS) index and NaN-filled gaps.
    """
    if "Date" not in wltable.columns:
        raise ValueError(
            "Expected a 'Date' column in monthly_mean response; "
            f"got columns: {list(wltable.columns)}"
        )
    if "MSL" not in wltable.columns:
        raise ValueError(
            "Expected an 'MSL' column in monthly_mean response; "
            f"got columns: {list(wltable.columns)}"
        )

    wltable = wltable.copy()
    wltable["DateTime"] = pd.to_datetime(wltable["Date"])
    wltable["WaterLevel"] = wltable["MSL"]

    monthly = (
        wltable[["DateTime", "WaterLevel"]]
        .set_index("DateTime")
        .asfreq("MS")  # Month-start frequency
    )
    monthly = monthly.reset_index()
    monthly.columns = ["DateTime", "WaterLevel"]
    return monthly

# noaa-requests/noaa-py/noaapy/wl_download.py
import time
from io import StringIO
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import requests


def _download_csv_as_dataframe(
    url: str, options: Dict[str, Any] | None = None
) -> pd.DataFrame:
    """
    Helper to download a CSV from NOAA CO-OPS and return as a pandas DataFrame.
    """
    opts = options.copy() if options else {}
    timeout = opts.pop("timeout", 30)  # pull out timeout if provided

    resp = requests.get(url, timeout=timeout, **opts)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


def wl_download(
    ii: int,
    Sdata: List[dict],
    datum: str,
    station: str,
    timezone: str,
    units: str,
    fmt: str,  # 'format' is a Python builtin, so use fmt instead
    stDates,
    endDates,
    gen_url: str,
    options: Dict[str, Any] | None,
    flag1: str,
) -> List[dict]:
    """
    Python translation of MATLAB WL_download.m

    Parameters
    ----------
    ii : int
        Index into Sdata (0-based in Python: Sdata[ii]).
    Sdata : list of dict
        Sdata[ii]['WL'] will be set to the resulting DataFrame.
    datum, station, timezone, units, fmt, gen_url, flag1 :
        Same semantics as in the MATLAB function.
    stDates, endDates :
        For non-monthly:
            - list of list of strings, e.g. stDates[jj][kk] == 'yyyymmdd HH:MM'
        For monthly:
            - list (or 1-D array) of strings 'yyyymmdd HH:MM' or 'yyyymmdd'.
    options : dict or None
        Extra options for requests.get (e.g. {'timeout': 30}).

    Returns
    -------
    Sdata : list of dict
        Same object as input, with Sdata[ii]['WL'] set to a DataFrame
        with columns ['DateTime', 'WaterLevel'].
    """
    data = pd.DataFrame(columns=["DateTime", "WaterLevel"])

    # Determine length of outer loop
    if flag1 != "m":
        Lend = len(stDates)
    else:
        # MATLAB used length(stDates(:,1)); here we assume stDates is 1-D
        Lend = len(stDates)

    for jj in range(Lend):
        # GAP FILLER (placeholder)
        data = gap_filler(data, stDates, endDates, flag1, jj)

        # ------------------------------------------------------------------
        # NON-MONTHLY PRODUCTS (6-min, hourly, high/low)
        # ------------------------------------------------------------------
        if flag1 != "m":
            # stDates[jj] and endDates[jj] should be lists of 'yyyymmdd HH:MM' strings
            segments = stDates[jj]
            end_segments = endDates[jj]

            for kk in range(len(segments)):
                begin_str = segments[kk]  # 'yyyymmdd HH:MM'
                end_str = end_segments[kk]

                if flag1 in ("6", "6p"):
                    # 6-minute WL measurements
                    wl_api = (
                        "/api/prod/datagetter?product=water_level"
                        "&application=NOS.COOPS.TAC.WL"
                        f"&begin_date={begin_str}"
                        f"&end_date={end_str}"
                        f"&datum={datum}"
                        f"&station={station}"
                        f"&time_zone={timezone}"
                        f"&units={units}"
                        f"&format={fmt}"
                    )

                    url = gen_url + wl_api

                    # Retry loop (as in MATLAB try/catch + while)
                    wltable = None
                    while wltable is None:
                        try:
                            wltable = _download_csv_as_dataframe(url, options)
                        except Exception:
                            time.sleep(3)

                elif flag1 == "1":
                    # 1-hour WL measurements
                    wl_api = (
                        "/api/prod/datagetter?product=hourly_height"
                        "&application=NOS.COOPS.TAC.WL"
                        f"&begin_date={begin_str}"
                        f"&end_date={end_str}"
                        f"&datum={datum}"
                        f"&station={station}"
                        f"&time_zone={timezone}"
                        f"&units={units}"
                        f"&format={fmt}"
                    )
                    url = gen_url + wl_api
                    wltable = _download_csv_as_dataframe(url, options)

                elif flag1 == "hilo":
                    # High/low WL measurements
                    wl_api = (
                        "/api/prod/datagetter?product=high_low"
                        "&application=NOS.COOPS.TAC.WL"
                        f"&begin_date={begin_str}"
                        f"&end_date={end_str}"
                        f"&datum={datum}"
                        f"&station={station}"
                        f"&time_zone={timezone}"
                        f"&units={units}"
                        f"&format={fmt}"
                    )
                    url = gen_url + wl_api
                    wltable = _download_csv_as_dataframe(url, options)

                else:
                    raise ValueError(f"Unsupported flag1 for non-monthly data: {flag1}")

                # ------------------------------------------------------------------
                # FAILSAFE: if empty or "too many" columns, synthesize NaN series
                # ------------------------------------------------------------------
                if wltable.empty or wltable.shape[1] > 5:
                    # MATLAB:
                    # uBound = datenum(stDates{jj}{kk},'yyyymmdd HH:MM');
                    # lBound = datenum(endDates{jj}{kk},'yyyymmdd HH:MM');
                    u_bound = pd.to_datetime(begin_str, format="%Y%m%d %H:%M")
                    l_bound = pd.to_datetime(end_str, format="%Y%m%d %H:%M")

                    # timestep
                    if "6" in flag1:
                        freq = "6min"
                    else:
                        freq = "1H"

                    # datetime vector from uBound to lBound, then drop the first
                    datetimes = pd.date_range(start=u_bound, end=l_bound, freq=freq)[1:]

                    # Create NaN vector
                    water_level = np.full(shape=len(datetimes), fill_value=np.nan)

                    # Synthetic table
                    wltable = pd.DataFrame(
                        {"DateTime": datetimes, "WaterLevel": water_level}
                    )
                else:
                    # Take first two columns (datetime, water level) like wltable(:,1:2)
                    # We rename them to ['DateTime','WaterLevel'] for consistency.
                    # NOAA CSV typically has 'Date Time' and 'Water Level' etc.
                    subset = wltable.iloc[:, :2].copy()
                    subset.columns = ["DateTime", "WaterLevel"]

                    # Convert DateTime to pandas datetime if it's not already
                    subset["DateTime"] = pd.to_datetime(subset["DateTime"])
                    wltable = subset

                print(
                    f"Station: {station} WL Measurements: {jj + 1}/{Lend} "
                    f"Segmentation: {kk + 1}/{len(segments)}"
                )

                # Concatenate chunk
                data = pd.concat([data, wltable], ignore_index=True)

        # ------------------------------------------------------------------
        # MONTHLY PRODUCT
        # ------------------------------------------------------------------
        else:
            # Monthly WL measurements
            begin_str = stDates[jj]  # assume 'yyyymmdd' or 'yyyymmdd HH:MM'
            end_str = endDates[jj]

            wl_api = (
                "/api/prod/datagetter?product=monthly_mean"
                "&application=NOS.COOPS.TAC.WL"
                f"&begin_date={begin_str}"
                f"&end_date={end_str}"
                f"&datum={datum}"
                f"&station={station}"
                f"&time_zone={timezone}"
                f"&units={units}"
                f"&format={fmt}"
            )

            url = gen_url + wl_api
            wltable = _download_csv_as_dataframe(url, options)

            # NOAA monthly CSV typically has a 'Date' column like 'YYYY-MM', and 'MSL'.
            # We map this into the same DateTime/WaterLevel structure and fill gaps.
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

            wltable["DateTime"] = pd.to_datetime(wltable["Date"])
            wltable["WaterLevel"] = wltable["MSL"]

            # Set monthly frequency and fill gaps with NaNs (like the MATLAB loop)
            monthly = (
                wltable[["DateTime", "WaterLevel"]]
                .set_index("DateTime")
                .asfreq("MS")  # Month-start frequency
            )

            monthly = monthly.reset_index()  # back to columns
            monthly.columns = ["DateTime", "WaterLevel"]

            # Concatenate chunk
            data = pd.concat([data, monthly], ignore_index=True)

    # ----------------------------------------------------------------------
    # REMOVE DUPLICATE POINTS (MEASUREMENTS)
    # ----------------------------------------------------------------------
    # Sort by DateTime, then drop duplicates keeping the last (as MATLAB unique(...,'last'))
    data = data.sort_values("DateTime").drop_duplicates(subset="DateTime", keep="last")

    # Attach to Sdata and return
    if ii >= len(Sdata):
        # extend Sdata if needed
        Sdata.extend({} for _ in range(ii - len(Sdata) + 1))

    Sdata[ii]["WL"] = data.reset_index(drop=True)
    return Sdata

# noaa-requests/noaa-py/download.py
import datetime
import time
from io import StringIO
from typing import Any, Dict, List
import requests

import pandas as pd
import numpy as np

import noaapy

# https://api.tidesandcurrents.noaa.gov/api/prod/


def download(
    id_list, station_list, requested_datum, prod, operation, begin_date, end_date
):
    """Entry point to the download"""
    if operation not in ["full_record", "specific_date"]:
        raise ValueError(
            "Please use a valid operational mode: full_record or specific_date)"
        )

    # Start Timer
    start_time = datetime.datetime.now()

    # Define Initial Variables
    datum = noaapy.globals.DEFAULT_DATUM
    timezone = noaapy.globals.DEFAULT_TIMEZONE
    units = noaapy.globals.DEFAULT_UNITS
    data_format = noaapy.globals.DEFAULT_DATA_FORMAT
    gen_url = noaapy.globals.BASE_API_URL
    timeout = noaapy.globals.DEFAULT_TIMEOUT

    # Check if stations are in inventory
    logical_matrix = np.array([[s["id"] == id for id in id_list] for s in station_list])
    max_logical = np.max(logical_matrix, axis=0)
    valid_indices = np.argmax(logical_matrix, axis=0)

    # Single out stations that were not found in StationList
    not_found = [id_list[i] for i, val in enumerate(max_logical) if not val]

    # Create valid station id list
    id_list = [
        station_list[valid_indices[i]]["id"] for i, val in enumerate(max_logical) if val
    ]

    # Initialize Counter
    ctr = 0

    # Initialize Results
    s_data = []

    # Download Data for Each Station
    for i, station_id in enumerate(id_list):
        print(f"------------------ {i + 1} / {len(id_list)} ---------------------")
        for product in prod:
            # Extract Station from Data Structure
            station: dict = next(s for s in station_list if s["id"] == station_id)
            s_data_entry = {
                "id": station_id,
                "name": station["name"],
                "lon": station["lon"],
                "lat": station["lat"],
                "state": station["state"],
            }

            # Check WL Measurements Products Available
            flag4, flag1, indx = noaapy.measurements_product_flags(station, product)

            if flag4 == 1:
                s_data_entry.update(
                    {
                        "WL_datum": "Not found",
                        "TP_datum": "Not found",
                        "WL_downloaded_product": "Not found",
                        "TP_downloaded_product": "Not found",
                        "record_length": "Not found",
                        "WL": "Not found",
                        "TP": "Not found",
                    }
                )
                s_data.append(s_data_entry)
                ctr += 1
                continue

            # Check if Date Range of Interest is Available
            if operation == "specific_date":
                indx, end_date, begin_date, dummy3 = noaapy.date_search(
                    station, begin_date, end_date, indx
                )
                if not dummy3:
                    station["start_date"][indx] = (
                        f"{begin_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                    )
                    station["end_date"][indx] = (
                        f"{end_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                    )
                else:
                    s_data_entry.update(
                        {
                            "WL_datum": "Not found",
                            "TP_datum": "Not found",
                            "WL_downloaded_product": "Not found",
                            "TP_downloaded_product": "Not found",
                            "record_length": "Not found",
                            "WL": "Not found",
                            "TP": "Not found",
                        }
                    )
                    s_data.append(s_data_entry)
                    ctr += 1
                    continue

            # Divide Date Range in Allowed Segments
            st_dates, end_dates, st_dates_p, end_dates_p = noaapy.download_segmentation(
                station, flag1, indx
            )

            # Check Datum Availability
            datum, datum_p = noaapy.datum_selector(station, requested_datum)

            # Check Tidal Predictions Intervals
            interval, _ = noaapy.prediction_interval_selector(
                station, flag1, station["greatlakes"]
            )

            # Assign Info to Sdata
            s_data_entry.update(
                {
                    "WL_datum": datum,
                    "TP_datum": datum_p,
                    "WL_downloaded_product": noaapy.globals.PRODUCT_LABELS[flag1],
                    "TP_downloaded_product": interval,
                    "record_length": station["record_length"][indx],
                }
            )

            # NAVD88 Adjustment
            if datum == "NAVD88":
                datum = "NAVD"
            if datum_p == "NAVD88":
                datum_p = "NAVD"

            # Build URL & Download Measured Data
            s_data = _wl_download(
                ctr,
                s_data,
                datum,
                station_id,
                timezone,
                units,
                data_format,
                st_dates,
                end_dates,
                gen_url,
                timeout,
                flag1,
            )

            # Download Tidal Predictions
            s_data = tidal_predictions_downloader(
                ctr,
                s_data,
                datum_p,
                station_id,
                timezone,
                units,
                data_format,
                interval,
                st_dates_p,
                end_dates_p,
                gen_url,
                timeout,
                station["greatlakes"],
                flag1,
                station,
            )

            # Make Sure Time Vectors Are the Same Length
            if station["greatlakes"] == 0:
                s_data = vector_length_check(ctr, s_data, flag1, station["greatlakes"])

            # Compute Total Record Length (Non NaN Data)
            s_data = record_length_calc(ctr, s_data, flag1)

            # Add DateRange
            s_data_entry.update(
                {
                    "Beg": s_data[ctr]["WL"]["DateTime"][0].strftime("%Y-%m-%d %H:%M"),
                    "End": s_data[ctr]["WL"]["DateTime"][-1].strftime("%Y-%m-%d %H:%M"),
                }
            )

            # Increment Counter for Product Loop
            ctr += 1

    # End Timer
    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print(f"Total Run Time: {run_time}")

    return s_data, not_found


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
    fmt: str,
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

                product_param = noaapy.globals.PRODUCT_PARAM[flag1]

                wl_api = (
                    f"/datagetter?product={product_param}"
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
                if flag1 not in noaapy.globals.PRODUCT_PARAMS:
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
                "/datagetter?product=monthly_mean"
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

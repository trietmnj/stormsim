# noaa-requests/noaa-py/download.py
import datetime
from io import StringIO
from typing import Any, Dict, List, Sequence, Tuple, Iterable, Optional
from dataclasses import dataclass

import requests
import pandas as pd

import noaapy


class DownloadDataConfig(dataclass):
    station_ids: List[str]
    datum: str
    prod: List[str]
    op_mode: str
    d_beg: Optional[str] = None
    d_end: Optional[str] = None


def download(
    download_data_cfg: DownloadDataConfig,
    station_list,
):
    """Entry point to the download."""
    station_ids = download_data_cfg.station_ids
    requested_datum = download_data_cfg.datum
    prod = download_data_cfg.prod
    operation = download_data_cfg.op_mode
    begin_date = download_data_cfg.d_beg
    end_date = download_data_cfg.d_end

    _validate_operation(operation)
    start_time = datetime.datetime.now()

    # Defaults from globals
    datum = noaapy.globals.DEFAULT_DATUM
    timezone = noaapy.globals.DEFAULT_TIMEZONE
    units = noaapy.globals.DEFAULT_UNITS
    data_format = noaapy.globals.DEFAULT_DATA_FORMAT
    gen_url = noaapy.globals.BASE_API_URL
    timeout = noaapy.globals.DEFAULT_TIMEOUT
    request_options = {"timeout": timeout}

    # Station lookup and validity check
    station_lookup = _build_station_lookup(station_list)
    station_ids, not_found = _filter_station_ids(station_ids, station_lookup)

    # Results container
    data: List[Dict[str, Any]] = []

    # Loop over stations and products
    for _, station_id in enumerate(station_ids):
        station = station_lookup[station_id]
        for product in prod:
            # Create base entry and append immediately so all helpers
            # can rely on its index.
            s_data_entry = _base_sdata_entry(station_id, station)
            data.append(s_data_entry)
            entry_idx = len(data) - 1

            # Check WL measurements products available
            is_product_available, interval_param, indx = (
                noaapy.params.measurements_product_flags(product)
            )
            if not is_product_available:
                continue

            # For "specific_date", ensure requested date range is available
            if operation == "specific_date":
                indx, end_date, begin_date, date_ok = noaapy.date_search(
                    station, begin_date, end_date, indx
                )
                if not date_ok:
                    # Leave base "Not found" values and skip
                    continue

                # Update station record dates if needed
                station["start_date"][indx] = (
                    f"{begin_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )
                station["end_date"][indx] = (
                    f"{end_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )

            # Divide date range into allowed segments
            (
                st_dates,
                end_dates,
                st_dates_p,
                end_dates_p,
            ) = noaapy.parse_dates(station, interval_param, indx)

            # Datum selection
            datum, datum_p = noaapy.datum_selector(station, requested_datum)

            # Tidal prediction interval
            interval, _ = noaapy.prediction_interval_selector(
                station, interval_param, station["greatlakes"]
            )

            # Update metadata on the entry
            s_data_entry.update(
                {
                    "WL_datum": datum,
                    "TP_datum": datum_p,
                    "WL_downloaded_product": noaapy.globals.PRODUCT_LABELS[
                        interval_param
                    ],
                    "TP_downloaded_product": interval,
                    "record_length": station["record_length"][indx],
                }
            )

            # NAVD88 adjustment for NOAA endpoints
            wl_datum_for_api = datum.replace("NAVD88", "NAVD")
            tp_datum_for_api = datum_p.replace("NAVD88", "NAVD")

            # Download measured data
            data = _wl_download(
                entry_idx,
                data,
                wl_datum_for_api,
                station_id,
                timezone,
                units,
                data_format,
                st_dates,
                end_dates,
                gen_url,
                request_options,  # dict expected by _wl_download
                interval_param,
            )

            # Download tidal predictions
            data = tidal_predictions_downloader(
                entry_idx,
                data,
                tp_datum_for_api,
                station_id,
                timezone,
                units,
                data_format,
                interval,
                st_dates_p,
                end_dates_p,
                gen_url,
                timeout,  # keep as-is if tidal_predictions_downloader expects a scalar
                station["greatlakes"],
                interval_param,
                station,
            )

            # Great Lakes special handling
            if station["greatlakes"] == 0:
                data = vector_length_check(
                    entry_idx,
                    data,
                    interval_param,
                    station["greatlakes"],
                )

            # Compute total record length (non-NaN data)
            data = record_length_calc(entry_idx, data, interval_param)

            # Add Begin / End timestamps to this entry
            _set_beg_end_from_wl_entry(s_data_entry)

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print(f"Total Run Time: {run_time}")

    return data, not_found


def _validate_operation(operation: str) -> None:
    if operation not in ("full_record", "specific_date"):
        raise ValueError(
            "Please use a valid operational mode: full_record or specific_date"
        )


def _build_station_lookup(
    station_list: Iterable[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Map station id -> station dict."""
    return {s["id"]: s for s in station_list}


def _filter_station_ids(
    id_list: Iterable[str], station_lookup: Dict[str, Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """
    Split requested ids into valid ones (present in station_lookup)
    and not_found ones.
    """
    valid_ids: List[str] = []
    not_found: List[str] = []

    for station_id in id_list:
        if station_id in station_lookup:
            valid_ids.append(station_id)
        else:
            not_found.append(station_id)

    return valid_ids, not_found


def _base_sdata_entry(station_id: str, station: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize a result entry with common fields + 'Not found' defaults."""
    return {
        "id": station_id,
        "name": station["name"],
        "lon": station["lng"],
        "lat": station["lat"],
        "state": station["state"],
        "WL_datum": "Not found",
        "TP_datum": "Not found",
        "WL_downloaded_product": "Not found",
        "TP_downloaded_product": "Not found",
        "record_length": "Not found",
        "WL": "Not found",
        "TP": "Not found",
    }


def _set_beg_end_from_wl_entry(entry: Dict[str, Any]) -> None:
    """Set 'Beg' and 'End' keys on an s_data entry based on its WL DataFrame."""
    wl = entry.get("WL")
    if isinstance(wl, pd.DataFrame) and not wl.empty:
        entry["Beg"] = wl["DateTime"].iloc[0].strftime("%Y-%m-%d %H:%M")
        entry["End"] = wl["DateTime"].iloc[-1].strftime("%Y-%m-%d %H:%M")


def _wl_download(
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
    query_params = {
        "datum": datum,
        "station": station,
        "timezone": timezone,
        "units": units,
        "fmt": fmt,
    }

    if flag1 != "m":
        data = _handle_non_monthly(
            data=data,
            flag1=flag1,
            datum=datum,
            station=station,
            timezone=timezone,
            units=units,
            fmt=fmt,
            gen_url=gen_url,
            stDates=stDates,
            endDates=endDates,
            options=options,
        )
    else:
        data = _handle_monthly(
            data=data,
            query_params=query_params,
            stDates=stDates,
            endDates=endDates,
            options=options,
        )

    # Remove duplicate measurements
    data = (
        data.sort_values("DateTime")
        .drop_duplicates(subset="DateTime", keep="last")
        .reset_index(drop=True)
    )

    # Ensure Sdata is large enough
    if ii >= len(Sdata):
        Sdata.extend({} for _ in range(ii - len(Sdata) + 1))

    Sdata[ii]["WL"] = data
    return Sdata


def _validate_non_monthly_flag(flag1: str) -> None:
    """Ensure flag1 is a supported non-monthly product."""
    if flag1 not in noaapy.globals.INTERVAL_TO_PRODUCT_PARAM:
        raise ValueError(f"Unsupported flag1 for non-monthly data: {flag1}")


def _handle_monthly(
    data: pd.DataFrame,
    stDates: Sequence[str],
    endDates: Sequence[str],
    options: Dict[str, Any] | None,
    query_params: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Handle monthly_mean product.
    stDates[jj], endDates[jj] are 'yyyymmdd' or 'yyyymmdd HH:MM'.
    """
    Lend = len(stDates)
    for idx in range(Lend):
        query_params["product"] = "monthly_mean"
        query_params["begin_str"] = stDates[idx]
        query_params["end_str"] = endDates[idx]
        url = _build_url(query_param=query_params)
        wltable = _download_wl_table(url, options)
        monthly = noaapy.processing.process_monthly_table(wltable)
        data = pd.concat([data, monthly], ignore_index=True)
    return data


def _build_url(
    query_param: Dict[str, str],
) -> str:
    """Build NOAA CO-OPS non-monthly WL URL."""
    wl_api = (
        f"/datagetter?product={query_param.product}"
        "&application=NOS.COOPS.TAC.WL"
        f"&begin_date={query_param.begin_str}"
        f"&end_date={query_param.end_str}"
        f"&datum={query_param.datum}"
        f"&station={query_param.station}"
        f"&time_zone={query_param.timezone}"
        f"&units={query_param.units}"
        f"&format={query_param.fmt}"
    )
    return noaapy.globals.BASE_API_URL + wl_api


def _download_wl_table(url: str, options: Dict[str, Any] | None) -> pd.DataFrame:
    """
    Download a CSV from NOAA CO-OPS and return as a pandas DataFrame.
    """
    opts = options.copy() if options else {}
    timeout = opts.pop("timeout", 30)
    resp = requests.get(url, timeout=timeout, **opts)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


# ----------------------------------------------------------------------
# Helpers: per-branch logic
# ----------------------------------------------------------------------
def _handle_non_monthly(
    data: pd.DataFrame,
    flag1: str,
    datum: str,
    station: str,
    timezone: str,
    units: str,
    fmt: str,
    gen_url: str,
    stDates: Sequence[Sequence[str]],
    endDates: Sequence[Sequence[str]],
    options: Dict[str, Any] | None,
) -> pd.DataFrame:
    """
    Handle non-monthly products (6-min, hourly, high/low).
    stDates[jj], endDates[jj] are lists of 'yyyymmdd HH:MM' strings.
    """
    _validate_non_monthly_flag(flag1)
    product = noaapy.globals.PRODUCT_PARAM[flag1]

    Lend = len(stDates)
    for jj in range(Lend):
        data = noaapy.processing.fill_gaps(data, stDates, endDates, flag1, jj)
        segments = stDates[jj]
        end_segments = endDates[jj]
        for kk, (begin_str, end_str) in enumerate(zip(segments, end_segments)):
            query_param = {
                "product": product,
                "datum": datum,
                "station": station,
                "timezone": timezone,
                "units": units,
                "fmt": fmt,
                "gen_url": gen_url,
                "begin_str": begin_str,
                "end_str": end_str,
            }
            url = _build_url(
                query_param=query_param,
            )
            wltable = _download_wl_table(url, options)
            # Failsafe path
            if wltable.empty or wltable.shape[1] > 5:
                wltable = noaapy.processing.synthesize_nan_series(
                    begin_str, end_str, flag1
                )
            else:
                wltable = noaapy.processing.normalize_non_monthly_wl_table(wltable)
            print(
                f"Station: {station} WL Measurements: {jj + 1}/{Lend} "
                f"Segmentation: {kk + 1}/{len(segments)}"
            )
            data = pd.concat([data, wltable], ignore_index=True)

    return data

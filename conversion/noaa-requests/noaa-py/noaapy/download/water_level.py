from typing import Any, Dict, List, Sequence
import pandas as pd
import noaapy
import requests
from io import StringIO


def download_wl(
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


def _download_wl_table(url: str, options: Dict[str, Any] | None) -> pd.DataFrame:
    """
    Download a CSV from NOAA CO-OPS and return as a pandas DataFrame.
    """
    opts = options.copy() if options else {}
    timeout = opts.pop("timeout", 30)
    resp = requests.get(url, timeout=timeout, **opts)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


def _build_url(
    query_param: Dict[str, str],
) -> str:
    """Build NOAA CO-OPS non-monthly WL URL."""
    wl_api = (
        f"/datagetter?product={query_param['product']}"
        "&application=NOS.COOPS.TAC.WL"
        f"&begin_date={query_param['begin_str']}"
        f"&end_date={query_param['end_str']}"
        f"&datum={query_param['datum']}"
        f"&station={query_param['station']}"
        f"&time_zone={query_param['timezone']}"
        f"&units={query_param['units']}"
        f"&format={query_param['fmt']}"
    )
    return noaapy.globals.BASE_API_URL + wl_api


def _validate_non_monthly_flag(flag1: str) -> None:
    """Ensure flag1 is a supported non-monthly product."""
    if flag1 not in noaapy.globals.INTERVAL_TO_PRODUCT_PARAM:
        raise ValueError(f"Unsupported flag1 for non-monthly data: {flag1}")

# conversion/noaa-requests/noaa-py/noaapy/download/water_level.py
from typing import Any, Dict, List, Tuple
import pandas as pd
import requests
from io import StringIO

import noaapy


def download_wl(
    datum: str,
    station: str,
    timezone: str,
    units: str,
    fmt: str,
    dates: noaapy.dates.DateRanges,
    gen_url: str,
    interval: str,
    options: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    base_params = {
        "datum": datum,
        "station": station,
        "timezone": timezone,
        "units": units,
        "fmt": fmt,
    }

    stDates = dates.starts
    endDates = dates.ends

    # --- configure by flag1 ---
    if interval == "m":
        product = "monthly_mean"
        postprocess = noaapy.processing.process_monthly_table
        # make monthly look like “one block with many segments”
        blocks = [list(zip(stDates, endDates))]
    if interval not in noaapy.globals.INTERVAL_TO_PRODUCT_PARAM:
        raise ValueError(f"Unsupported flag1: {interval}")
    else:
        product = noaapy.globals.PRODUCT_PARAM[interval]
        postprocess = noaapy.processing.normalize_non_monthly_wl_table
        blocks = [
            list(zip(seg_st, seg_end)) for seg_st, seg_end in zip(stDates, endDates)
        ]

    data = pd.DataFrame(columns=["DateTime", "WaterLevel"])
    params = base_params.copy()
    params["product"] = product
    params["gen_url"] = gen_url

    for jj, segments in enumerate(blocks):
        # only non-monthly uses fill_gaps
        if interval != "m":
            data = noaapy.processing.fill_gaps(data, stDates, endDates, interval, jj)

        for kk, (begin_str, end_str) in enumerate(segments):
            params["begin_str"] = begin_str
            params["end_str"] = end_str

            url = _build_url(params)
            wltable = _download_wl_table(url, options)

            if interval != "m" and (wltable.empty or wltable.shape[1] > 5):
                wltable = noaapy.processing.synthesize_nan_series(
                    begin_str, end_str, interval
                )
            else:
                wltable = postprocess(wltable)

            print(
                f"Station: {station} Block: {jj + 1}/{len(blocks)} "
                f"Seg: {kk + 1}/{len(segments)}"
            )

            data = pd.concat([data, wltable], ignore_index=True)

    data = (
        data.sort_values("DateTime")
        .drop_duplicates(subset="DateTime", keep="last")
        .reset_index(drop=True)
    )
    return data


def _download_wl_table(url: str, options: Dict[str, Any] | None) -> pd.DataFrame:
    """Download CSV from NOAA and return as DataFrame."""
    opts = options.copy() if options else {}
    timeout = opts.pop("timeout", 30)
    resp = requests.get(url, timeout=timeout, **opts)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


def _build_url(params: Dict[str, Any]) -> str:
    """Build NOAA CO-OPS WL URL."""
    wl_api = (
        f"/datagetter?product={params['product']}"
        "&application=NOS.COOPS.TAC.WL"
        f"&begin_date={params['begin_str']}"
        f"&end_date={params['end_str']}"
        f"&datum={params['datum']}"
        f"&station={params['station']}"
        f"&time_zone={params['timezone']}"
        f"&units={params['units']}"
        f"&format={params['fmt']}"
    )
    return noaapy.globals.BASE_API_URL + wl_api

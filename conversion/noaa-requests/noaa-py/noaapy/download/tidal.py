from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _should_download_predictions(
    flag2: int, d_struct: Dict[str, Any], sdata_entry: Dict[str, Any]
) -> bool:
    """
    Replicates the MATLAB condition:

        if flag2 == 0 && (~iscell(dStruct.datums_predictions) && ~iscell(Sdata(ii).TP_datum))

    In the MATLAB code, 'cell' is used as a sentinel-type for "no predictions".
    Here we treat 'list/tuple' as the Python analogue of "cell array".
    """
    if flag2 != 0:
        return False

    datums_pred = d_struct.get("datums_predictions")
    tp_datum = sdata_entry.get("TP_datum")

    datums_is_cell = isinstance(datums_pred, (list, tuple))
    tp_datum_is_cell = isinstance(tp_datum, (list, tuple))

    return (not datums_is_cell) and (not tp_datum_is_cell)


def _build_predictions_url(
    station: str,
    datum_p: str,
    timezone: str,
    units: str,
    fmt: str,
    gen_url: str,
    begin_str: str,
    end_str: str,
    interval: str,
    flag1: str,
) -> str:
    """
    Build the tidal predictions URL.

    The MATLAB code always uses the /api/prod/datagetter default 6-min path,
    ignoring interval and flag1 in practice.
    """
    # Direct translation of the active branch in MATLAB:
    # pred_api = ['/api/prod/datagetter?begin_date=',stDatesp{jj}{kk},'&end_date=',endDatesp{jj}{kk},...
    #             '&station=',station,'&product=predictions&datum=',datum_p,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
    pred_api = (
        f"/api/prod/datagetter?"
        f"begin_date={begin_str}"
        f"&end_date={end_str}"
        f"&station={station}"
        f"&product=predictions"
        f"&datum={datum_p}"
        f"&time_zone={timezone}"
        f"&units={units}"
        f"&format={fmt}"
    )

    return gen_url + pred_api


def _download_predictions_table(
    url: str, options: Dict[str, Any] | None
) -> pd.DataFrame:
    """
    Download tidal predictions as a DataFrame with columns:

        DateTime, Prediction

    Assumes `_download_csv_as_dataframe` is available and that NOAA's CSV
    contains something like 'Date Time' and 'Prediction'.
    """
    df = _download_csv_as_dataframe(url, options)

    if df.empty:
        return pd.DataFrame(columns=["DateTime", "Prediction"])

    # Try to normalize column names
    df = df.copy()
    # Common NOAA column names: 'Date Time' or 'DateTime', 'Prediction' or 'Predictions'
    rename_map = {}
    if "Date Time" in df.columns:
        rename_map["Date Time"] = "DateTime"
    if "DateTime" in df.columns:
        rename_map["DateTime"] = "DateTime"
    if "Prediction" in df.columns:
        rename_map["Prediction"] = "Prediction"
    if "Predictions" in df.columns:
        rename_map["Predictions"] = "Prediction"

    df.rename(columns=rename_map, inplace=True)

    # Keep only the two main columns if present
    if "DateTime" not in df.columns or "Prediction" not in df.columns:
        # Fallback: just take first 2 columns and assume they are DateTime & Prediction
        subset = df.iloc[:, :2].copy()
        subset.columns = ["DateTime", "Prediction"]
        df = subset

    df["DateTime"] = pd.to_datetime(df["DateTime"])
    return df[["DateTime", "Prediction"]]


def _retry_download_predictions(
    url: str,
    options: Dict[str, Any] | None,
    max_retries: int = 5,
    wait_seconds: int = 5,
) -> pd.DataFrame:
    """
    Try downloading predictions up to max_retries times.
    On failure, return a 1-row NaN DataFrame (like MATLAB's fallback).
    """
    for attempt in range(1, max_retries + 1):
        try:
            return _download_predictions_table(url, options)
        except Exception:
            if attempt == max_retries:
                # Final failure: return NaN row
                return pd.DataFrame({"DateTime": [pd.NaT], "Prediction": [np.nan]})
            # Sleep before retry (like pause(5) in MATLAB)
            import time

            time.sleep(wait_seconds)


def _append_if_valid(datap: pd.DataFrame, predtable: pd.DataFrame) -> pd.DataFrame:
    """
    MATLAB:

        if iscell(predtable.DateTime(1))==0
            datap = [datap;predtable(:,1:2)];
        end

    Here we approximate "not a cell" as "not a list/tuple".
    """
    if predtable.empty:
        return datap

    first_dt = predtable["DateTime"].iloc[0]
    if isinstance(first_dt, (list, tuple)):
        return datap

    return pd.concat([datap, predtable[["DateTime", "Prediction"]]], ignore_index=True)


def _finalize_tp_from_chunks(
    datap: pd.DataFrame,
    last_predtable: pd.DataFrame | None,
) -> pd.DataFrame | str:
    """
    Decide final Sdata[ii]['TP'] based on the collected datap and the last predtable.
    """
    if last_predtable is not None:
        # If "empty" sentinel: single-row NaN
        if len(last_predtable) == 1 and last_predtable["DateTime"].isna().all():
            return "Great Lakes Station"

    if datap.empty:
        return "Not Found"

    # Deduplicate by DateTime, keeping last (as MATLAB unique(...,'last'))
    datap = datap.sort_values("DateTime").drop_duplicates(
        subset="DateTime", keep="last"
    )
    return datap.reset_index(drop=True)


def _align_predictions_to_measurements(
    wl_df: pd.DataFrame,
    tp_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a monthly (or generally aligned) signal from predictions.

    MATLAB logic:

        tWL = Sdata(ii).WL(:,1);
        tTP = Sdata(ii).TP(:,1);
        found  = find(ismember(tTP,tWL)==1);
        DateTime = tTP.DateTime(found);
        Prediction = table2array(Sdata(ii).TP(:,2));
        Prediction = Prediction(found);
        Sdata(ii).TP = table(DateTime,Prediction);

    In pandas: merge predictions onto WL by DateTime and keep matches.
    """
    # Ensure expected columns
    if wl_df.empty or tp_df.empty:
        raise ValueError("Empty WL or TP DataFrame")

    if "DateTime" not in wl_df.columns or "DateTime" not in tp_df.columns:
        raise ValueError("WL or TP missing 'DateTime' column")

    if "Prediction" not in tp_df.columns:
        raise ValueError("TP missing 'Prediction' column")

    # Merge using WL's DateTime as the reference (to align with WL samples)
    merged = wl_df[["DateTime"]].merge(
        tp_df[["DateTime", "Prediction"]],
        on="DateTime",
        how="inner",
    )

    if merged.empty:
        raise ValueError("No overlapping DateTime values between WL and TP")

    return merged[["DateTime", "Prediction"]].reset_index(drop=True)


# ---------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------
def tidal_predictions_downloader(
    ii: int,
    Sdata: List[Dict[str, Any]],
    datum_p: str,
    station: str,
    timezone: str,
    units: str,
    fmt: str,
    interval: str,
    stDatesp,
    endDatesp,
    gen_url: str,
    timeout: int,
    flag2: int,
    flag1: str,
    dStruct: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Python translation of MATLAB tidal_predictions_downloader.m

    Parameters
    ----------
    ii : int
        Index into Sdata (0-based).
    Sdata : list of dict
        Sdata[ii]['TP'] will be set/updated by this function.
    datum_p, station, timezone, units, fmt, interval, gen_url, timeout :
        Same semantics as in MATLAB version (NOAA CO-OPS predictions API).
    stDatesp, endDatesp :
        Nested lists: stDatesp[jj][kk] and endDatesp[jj][kk] are 'yyyymmdd HH:MM'.
    flag2 : int
        Typically station["greatlakes"] (0 or 1).
    flag1 : str
        Interval parameter / product flag (not heavily used here).
    dStruct : dict
        Station metadata structure (must contain 'datums_predictions').

    Returns
    -------
    Sdata : list of dict
        Updated in-place, but also returned for convenience.
    """
    s_entry = Sdata[ii]
    options = {"timeout": timeout}

    datap = pd.DataFrame(columns=["DateTime", "Prediction"])
    last_predtable: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # DOWNLOAD TIDAL PREDICTIONS
    # ------------------------------------------------------------------
    if _should_download_predictions(flag2, dStruct, s_entry):
        # stDatesp[jj], endDatesp[jj] are lists of strings
        for jj, (st_row, end_row) in enumerate(zip(stDatesp, endDatesp), start=1):
            for kk, (begin_str, end_str) in enumerate(zip(st_row, end_row), start=1):
                url = _build_predictions_url(
                    station=station,
                    datum_p=datum_p,
                    timezone=timezone,
                    units=units,
                    fmt=fmt,
                    gen_url=gen_url,
                    begin_str=begin_str,
                    end_str=end_str,
                    interval=interval,
                    flag1=flag1,
                )

                predtable = _retry_download_predictions(url, options)
                last_predtable = predtable

                datap = _append_if_valid(datap, predtable)

                print(
                    f"Station: {station} WL Preds: {jj}/{len(stDatesp)} "
                    f"Segmentation: {kk}/{len(st_row)}"
                )

        Sdata[ii]["TP"] = _finalize_tp_from_chunks(datap, last_predtable)
    else:
        # No tidal prediction
        Sdata[ii]["TP"] = "Not Found"

    # ------------------------------------------------------------------
    # CREATE A MONTHLY SIGNAL FROM PREDICTIONS (ALIGN TO WL)
    # ------------------------------------------------------------------
    if flag2 == 0:
        try:
            wl_df = Sdata[ii]["WL"]
            tp_val = Sdata[ii]["TP"]

            if not isinstance(wl_df, pd.DataFrame) or not isinstance(
                tp_val, pd.DataFrame
            ):
                raise ValueError("WL or TP is not a DataFrame")

            Sdata[ii]["TP"] = _align_predictions_to_measurements(wl_df, tp_val)

        except Exception:
            Sdata[ii]["TP"] = "Not Found"

    return Sdata

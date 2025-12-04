from typing import Any, Dict, List

import numpy as np
import pandas as pd


def vector_length_check(
    ii: int,
    Sdata: List[Dict[str, Any]],
    flag1: str,
    flag2: int,
) -> List[Dict[str, Any]]:
    """
    Python translation of MATLAB vector_length_check.m

    Ensures WL and TP time vectors are consistent, and if TP has extra
    DateTime values, pads WL with NaNs at those times.

    Parameters
    ----------
    ii : int
        Index into Sdata (0-based).
    Sdata : list of dict
        Sdata[ii]['WL'] : DataFrame with ['DateTime', 'WaterLevel']
        Sdata[ii]['TP'] : DataFrame with ['DateTime', 'Prediction'] or a string.
    flag1 : str
        Interval/product flag; only non-monthly ('m' != flag1) are adjusted.
    flag2 : int
        Great Lakes flag (0 = ocean/coastal, non-zero = Great Lakes).

    Returns
    -------
    Sdata : list of dict
        Updated in place, but also returned for convenience.
    """
    try:
        wl_df = Sdata[ii].get("WL")
        tp_df = Sdata[ii].get("TP")

        # We only operate when both are DataFrames
        if not isinstance(wl_df, pd.DataFrame) or not isinstance(tp_df, pd.DataFrame):
            raise ValueError("WL or TP is not a DataFrame")

        tWL = wl_df["DateTime"]
        tTP = tp_df["DateTime"]

        # If more WL than TP (and not Great Lakes), raise like MATLAB
        if len(tWL) > len(tTP) and flag2 == 0:
            raise RuntimeError(
                "CHECK THIS SECTION CAREFULLY. It is unusual to have more "
                "measurements than predictions."
            )

        # If lengths differ, non-monthly (flag1 != 'm') and not Great Lakes
        if len(tWL) != len(tTP) and flag1 != "m" and flag2 == 0:
            Sdata[ii]["WL"] = _extend_wl_with_missing_predictions(wl_df, tp_df)

    except Exception:
        # On any failure, mirror MATLAB's catch behavior:
        Sdata[ii]["TP"] = "No Tidal Predictions"

    return Sdata


def _extend_wl_with_missing_predictions(
    wl_df: pd.DataFrame,
    tp_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add NaN WaterLevel rows to WL for any DateTime present in TP but not in WL,
    then sort by DateTime.

    This mirrors the MATLAB logic:

        DateTime = tTP.DateTime(ismember(tTP,tWL)==0);
        WaterLevel = NaN(size(DateTime));
        gap_mat = table(DateTime,WaterLevel);
        gap_mat = [Sdata(ii).WL;gap_mat];
        gap_mat = sortrows(gap_mat,1);
        Sdata(ii).WL = gap_mat;
    """
    if wl_df.empty or tp_df.empty:
        return wl_df

    if "DateTime" not in wl_df.columns or "DateTime" not in tp_df.columns:
        return wl_df

    # Time vectors
    tWL = wl_df["DateTime"]
    tTP = tp_df["DateTime"]

    # Mask of DateTimes in TP that are NOT in WL
    missing_mask = ~tTP.isin(tWL)
    missing_dates = tTP[missing_mask]

    if missing_dates.empty:
        return wl_df

    gap_mat = pd.DataFrame(
        {
            "DateTime": missing_dates,
            "WaterLevel": np.nan,
        }
    )

    wl_extended = pd.concat([wl_df, gap_mat], ignore_index=True)
    wl_extended = wl_extended.sort_values("DateTime").reset_index(drop=True)
    return wl_extended

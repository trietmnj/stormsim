from typing import Any, Dict, List

import pandas as pd


def _compute_record_length_years(wl_df: pd.DataFrame) -> float:
    """
    Compute record length in decimal years based on the first and last
    non-NaN WaterLevel entries.
    """
    if wl_df.empty:
        return 0.0

    if "DateTime" not in wl_df.columns or "WaterLevel" not in wl_df.columns:
        return 0.0

    # Keep only valid measurements
    valid = wl_df.dropna(subset=["WaterLevel"])
    if valid.empty:
        return 0.0

    t1 = valid["DateTime"].min()
    t2 = valid["DateTime"].max()

    # Convert to Timedelta and then to years
    delta = t2 - t1
    years = delta.total_seconds() / (365.25 * 24 * 3600.0)
    return float(years)


def record_length_calc(
    ii: int,
    Sdata: List[Dict[str, Any]],
    flag1: str,  # kept for API compatibility; not used in this simplified version
) -> List[Dict[str, Any]]:
    """
    Python translation / simplification of record_length_calc.m.

    This function computes the record length of downloaded WL data by:
    - removing NaN values from the WaterLevel time series
    - computing the time span between first and last valid measurements
    - expressing that span in decimal years

    Parameters
    ----------
    ii : int
        Index into Sdata (0-based).
    Sdata : list of dict
        Sdata[ii]['WL'] must be a DataFrame with ['DateTime', 'WaterLevel'].
    flag1 : str
        Product flag (e.g. '1', '6', 'm'); kept for compatibility but not used.

    Returns
    -------
    Sdata : list of dict
        Updated in-place (Sdata[ii]['record_length'] set to float years),
        and also returned for convenience.
    """
    wl_df = Sdata[ii].get("WL")
    if isinstance(wl_df, pd.DataFrame):
        Sdata[ii]["record_length"] = _compute_record_length_years(wl_df)
    else:
        Sdata[ii]["record_length"] = 0.0
    return Sdata

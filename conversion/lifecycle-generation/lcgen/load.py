import pandas as pd
import numpy as np


def load_relative_probabilities(filepath: str):
    """
    Load daily cumulative storm probabilities by (Month, Day).
    Expects columns: 'Month', 'Day', 'Cumulative trop prob'.
    """
    df = pd.read_csv(
        filepath,
        usecols=["Month", "Day", "Cumulative trop prob"],
        dtype={"Month": int, "Day": int, "Cumulative trop prob": float},
    ).rename(
        columns={
            "Month": "month",
            "Day": "day",
            "Cumulative trop prob": "trop_day_cdf",
        }
    )
    df["day_of_year"] = pd.to_datetime(
        df[["month", "day"]].assign(Year=2025), errors="coerce"
    ).dt.dayofyear
    return df


def load_storm_id_cdf(filepath: str):
    """
    Load storm IDs and their probabilities from CHS master track.
    Expects columns: 'storm_ID', 'DSW' (or similar).
    """
    df = pd.read_csv(
        filepath, usecols=["storm_ID", "DSW"], dtype={"storm_ID": int, "DSW": float}
    ).rename(
        columns={
            "storm_ID": "storm_id",
            "DSW": "dsw",
        }
    )
    df = df.sort_values(by="dsw").reset_index(drop=True)

    total_weight = df["dsw"].sum()
    df["prob"] = df["dsw"] / total_weight
    df["cdf"] = np.cumsum(df["prob"])
    return df

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
    )
    return df


def load_storm_id_cdf(filepath: str):
    """
    Load storm IDs and their probabilities from CHS master track.
    Expects columns: 'storm_ID', 'DSW' (or similar).
    """
    df = pd.read_csv(filepath, usecols=["storm_ID", "DSW"])
    df = df.sort_values(by="DSW").reset_index(drop=True)

    total_weight = df["DSW"].sum()
    df["probability"] = df["DSW"] / total_weight
    df["cdf"] = np.cumsum(df["probability"])
    return df

import numpy as np
import pandas as pd
from stormsim.hazard_curves.pst.mrl import fit_mrl


def test_mrl_statistics_with_reference_data():
    # Load input data
    input_df = pd.read_parquet("data/hazard_curves/pst/02_pst_input_cleaned.parquet")

    # Column 1 (index 1) contains the surge peaks as confirmed by inspection
    peaks = input_df[1].values

    n_years = 75

    summary, selection = fit_mrl(2, peaks, n_years)

    # Load reference stats
    target_summary = pd.read_parquet(
        "data/hazard_curves/pst/03_pst_mrl_summary.parquet"
    )

    # The summary dataframes have integer columns [0, 1, ..., 7]
    # Corresponding to: ["Threshold", "MeanExcess", "Weight", "WMSE", "GPD_Shape", "GPD_Scale", "Events", "Rate"]

    # GPD_Shape/GPD_Scale tolerances are loose due to Matlab vs scipy fitdist difference
    tolerances = [1e-8, 1e-12, 1e-9, 1e-7, 0.5, 0.2, 1e-8, 1e-8]
    col_names = [
        "Threshold",
        "MeanExcess",
        "Weight",
        "WMSE",
        "GPD_Shape",
        "GPD_Scale",
        "Events",
        "Rate",
    ]

    # Per-column validation
    for i, col in enumerate(col_names):
        assert np.allclose(
            summary.iloc[:, i].values,
            target_summary.iloc[:, i].values,
            atol=tolerances[i],
            equal_nan=True,
        ), f"Column {col} (idx {i}) mismatch"


def test_mrl_crit_si():
    input_df = pd.read_parquet("data/hazard_curves/pst/02_pst_input_cleaned.parquet")
    peaks = input_df[1].values
    summary, selection = fit_mrl(1, peaks, 75)
    assert selection is not None
    assert selection["Criterion"] == "CritSI"

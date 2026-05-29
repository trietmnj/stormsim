import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch
from stormsim.hazard_curves.pst.cleaner import clean_pot_data
from stormsim.hazard_curves.pst.utils import add_noise_to_duplicates
from stormsim.hazard_curves.pst.core import PSTOptions
from stormsim.hazard_curves.pst.fit import (
    fit_hazard_curve,
    bootstrap_ecdf,
    monotonic_adjustment,
)
from stormsim.hazard_curves.pst.mrl import kern_reg_local_mean, fit_mrl


def test_clean_pot_data():
    data = np.array(
        [
            [1.0, 0.5],
            [2.0, 1.0],
            [3.0, 1.5],
            [4.0, 2.0],
            [5.0, 999.0],
            [6.0, np.nan],
            [7.0, -1.0],
        ]
    )
    cleaned = clean_pot_data(data, flag_value=[999.0])
    assert len(cleaned) == 4
    assert np.all(cleaned[:, 1] > 0)
    assert 999.0 not in cleaned[:, 1]
    assert np.all(~np.isnan(cleaned[:, 1]))


def test_add_noise_to_duplicates():
    data = np.array(
        [
            [1.0, 1.0],
            [2.0, 2.0],
            [3.0, 1.0],
        ]
    )
    noisy_data = add_noise_to_duplicates(data.copy(), col_idx=1)
    assert noisy_data[0, 1] == 1.0
    assert noisy_data[1, 1] == 2.0
    assert noisy_data[2, 1] == 1.0 + 1e-6


def test_fitting_smoke():
    POT_no_tides = np.linspace(1, 10, 25)
    pst_options = PSTOptions(gpd_criterion=2, bootstrap_sims=5, percentiles=[16, 84])
    SST_output, MRL_output = fit_hazard_curve(
        POT_no_tides, None, _slc=0, n_years=30, _gpr_mdl=None, pst_options=pst_options
    )
    assert SST_output is not None
    assert MRL_output is not None


def test_ecdf_boot_against_matlab():
    empHC = pd.read_parquet(
        "data/hazard_curves/pst/02_pst_ecdf_emphc.parquet"
    ).values.flatten()
    boot_ref = pd.read_parquet("data/hazard_curves/pst/02_pst_ecdf_boot.parquet").values
    test_data = {
        "random": pd.read_parquet(
            "data/hazard_curves/pst/02_pst_ecdf_random.parquet"
        ).values.flatten(),
        "indices": pd.read_parquet("data/hazard_curves/pst/02_pst_ecdf_indices.parquet")
        .values.flatten()
        .astype(int)
        - 1,
    }
    boot = bootstrap_ecdf(empHC, boot_ref.shape[0], test_data=test_data)
    assert np.max(np.abs(boot - boot_ref)) < 1e-10


def test_kern_reg_local_mean():
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 4.0, 9.0])
    H = 1.0
    _, y_smooth = kern_reg_local_mean(x, y, H)
    expected = np.array([2.666187, 4.548137, 6.637398])
    np.testing.assert_allclose(y_smooth, expected, atol=1e-6)


def test_monotonic_adjustment():
    # Single positive slope between indices 1 and 2: y goes 5->3->4
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([5.0, 3.0, 4.0])
    result = monotonic_adjustment(x, y).flatten()
    # The bump at index 2 should be corrected downward
    assert result[2] < y[2]
    assert result[2] <= result[1]


def test_fitting_empirical_only():
    # N < 20 and apply_gpd=0 forces empirical-only path (no GPD)
    POT_no_tides = np.linspace(1, 10, 15)
    pst_options = PSTOptions(
        gpd_criterion=2, bootstrap_sims=10, percentiles=[16, 84], apply_gpd=0
    )
    SST_output, MRL_output = fit_hazard_curve(
        POT_no_tides, None, _slc=0, n_years=5, _gpr_mdl=None, pst_options=pst_options
    )
    assert MRL_output["summary"] is None
    assert MRL_output["selection"] is None
    assert not np.all(np.isnan(SST_output["hc_plot"]))


def test_fitting_use_aep():
    POT_no_tides = np.linspace(1, 10, 25)
    pst_options = PSTOptions(
        gpd_criterion=2, bootstrap_sims=5, percentiles=[16, 84], use_aep=1
    )
    SST_output, _ = fit_hazard_curve(
        POT_no_tides, None, _slc=0, n_years=30, _gpr_mdl=None, pst_options=pst_options
    )
    # hc_plot_x in AEP space: values in (0, 1]
    assert np.all(SST_output["hc_plot_x"] > 0)
    assert np.all(SST_output["hc_plot_x"] <= 1)


def test_mrl_raises_on_small_sample():
    with pytest.raises(ValueError, match="Insufficient sample size"):
        fit_mrl(2, np.linspace(1, 10, 15), 30)


def test_mrl_no_local_minima_returns_none_selection():
    peaks = np.linspace(0.1, 5.0, 30)
    with patch(
        "stormsim.hazard_curves.pst.mrl.find_peaks", return_value=(np.array([]), {})
    ):
        summary, selection = fit_mrl(2, peaks, 30)
    assert selection is None
    assert summary is not None and len(summary) > 0

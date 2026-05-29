import numpy as np
import pandas as pd

from stormsim.hazard_curves.jpm.compute import compute
from stormsim.hazard_curves.jpm.core import Options
from stormsim.hazard_curves.jpm.engine import integrate, interpolate_results, preprocess

_DATA_DIR = "data/hazard_curves/jpm"


def _opts(**overrides):
    """Options matching jpm_call_example.m: ITCS, combined uncertainty, no tides."""
    base = dict(
        flag_value=[],
        ua=0.3738,
        ur=0.5840,
        integration_mode="ITCS",
        uncertainty_mode="combined",
        tide_mode="none",
        percentiles=[16, 84],
        use_aep=False,
        return_table=True,
    )
    base.update(overrides)
    return Options(**base)


def test_preprocess_against_matlab():
    data = pd.read_parquet(f"{_DATA_DIR}/01_jpm_input.parquet").values
    resp, prob_mass = preprocess(data, _opts())

    ref = pd.read_parquet(f"{_DATA_DIR}/02_jpm_preprocessed.parquet").values
    assert np.allclose(resp, ref[:, 0], atol=1e-6, equal_nan=True)
    assert np.allclose(prob_mass, ref[:, 1], atol=1e-6, equal_nan=True)


def test_integrate_against_matlab():
    ref_pre = pd.read_parquet(f"{_DATA_DIR}/02_jpm_preprocessed.parquet").values
    x, y = integrate(ref_pre[:, 0], ref_pre[:, 1], _opts())

    ref = pd.read_parquet(f"{_DATA_DIR}/03_jpm_integration.parquet").values
    assert np.allclose(x, ref[:, 0], atol=1e-8, equal_nan=True)
    assert np.allclose(y, ref[:, 1:], atol=1e-8, equal_nan=True)


def test_interpolate_results_plot_against_matlab():
    ref_int = pd.read_parquet(f"{_DATA_DIR}/03_jpm_integration.parquet").values
    results = interpolate_results(ref_int[:, 0], ref_int[:, 1:], _opts())
    plot_arr = dict(results)["plot"]

    ref_plt = pd.read_parquet(f"{_DATA_DIR}/04_jpm_hc_plt.parquet").values
    assert np.allclose(plot_arr, ref_plt, atol=1e-6, equal_nan=True)


def test_interpolate_results_table_against_matlab():
    ref_int = pd.read_parquet(f"{_DATA_DIR}/03_jpm_integration.parquet").values
    results = interpolate_results(ref_int[:, 0], ref_int[:, 1:], _opts())
    tbl_arr = dict(results)["table"]

    ref_tbl = pd.read_parquet(f"{_DATA_DIR}/04_jpm_hc_tbl.parquet").values
    assert np.allclose(tbl_arr, ref_tbl, atol=1e-4, equal_nan=True)


def test_compute_pipeline_against_matlab():
    data = pd.read_parquet(f"{_DATA_DIR}/01_jpm_input.parquet").values
    results = compute(data, _opts())

    out = dict(results)
    ref_plt = pd.read_parquet(f"{_DATA_DIR}/04_jpm_hc_plt.parquet").values
    ref_tbl = pd.read_parquet(f"{_DATA_DIR}/04_jpm_hc_tbl.parquet").values

    assert np.allclose(out["plot"], ref_plt, atol=1e-6, equal_nan=True)
    assert np.allclose(out["table"], ref_tbl, atol=1e-4, equal_nan=True)

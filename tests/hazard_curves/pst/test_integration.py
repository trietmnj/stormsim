import numpy as np
import pandas as pd
import pytest

from stormsim.hazard_curves.pst.compute import compute
from stormsim.hazard_curves.pst.simulation import run_pst
from stormsim.hazard_curves.pst.core import PSTOptions, ResponseData


def test_pst():
    input_df = pd.read_parquet("data/hazard_curves/pst/01_pst_input_raw.parquet")
    surge_pot = input_df.iloc[:, 1].values

    data = np.zeros((surge_pot.size, 3))
    data[:, 1] = surge_pot.flatten()

    test_data = {
        "random": pd.read_parquet(
            "data/hazard_curves/pst/02_pst_ecdf_random.parquet"
        ).values.flatten(),
        "indices": pd.read_parquet("data/hazard_curves/pst/02_pst_ecdf_indices.parquet")
        .values.flatten()
        .astype(int)
        - 1,
    }

    response_data = ResponseData(
        data=data,
        flag_value=[],
        slc=0,
        n_years=75,
        gpr_mdl=None,
        data_type="POT",
    )

    pst_options = PSTOptions(
        apply_skew=0,
        use_aep=0,
        percentiles=[16, 84],
        t_lag=0,
        gpd_criterion=2,
        apply_gpd=1,
        bootstrap_sims=100,
    )

    hc_output, mrl_output = compute(
        response_data, pst_options, test_ecdf_data=test_data
    )

    # Validate against MATLAB golden data
    assert np.allclose(
        pd.read_parquet("data/hazard_curves/pst/05_pst_hc_plt_x.parquet").values[:, 0],
        hc_output["hc_plot_x"],
        atol=1e-10,
        equal_nan=True,
    )
    # atol=2e-3: scipy genpareto vs MATLAB fitdist difference propagates into hc_plot
    assert np.allclose(
        pd.read_parquet("data/hazard_curves/pst/05_pst_hc_plt.parquet").values,
        hc_output["hc_plot"],
        atol=2e-3,
        equal_nan=True,
    )
    assert np.allclose(
        pd.read_parquet("data/hazard_curves/pst/05_pst_hc_emp.parquet").values,
        hc_output["hc_emp"].values,
        atol=1e-10,
        equal_nan=True,
    )
    assert np.allclose(
        pd.read_parquet(
            "data/hazard_curves/pst/04_pst_gpd_params_unadjusted.parquet"
        ).values,
        mrl_output["gpd_shapes"],
        atol=1e-4,
        equal_nan=True,
    )
    assert np.allclose(
        pd.read_parquet(
            "data/hazard_curves/pst/04_pst_gpd_params_adjusted.parquet"
        ).values,
        mrl_output["gpd_shapes_clipped"],
        atol=1e-4,
        equal_nan=True,
    )


def test_run_pst_writes_outputs(tmp_path):
    config = {
        "inputs": {
            "data_file": "data/hazard_curves/pst/01_pst_input_raw.parquet",
        },
        "outputs": {
            "local_directory": str(tmp_path),
            "filename": "pst",
        },
        "pst_params": {
            "data_type": "POT",
            "n_years": 75,
            "slc": 0,
            "flag_value": [],
        },
        "pst_options": {
            "gpd_criterion": 2,
            "apply_gpd": 1,
            "bootstrap_sims": 10,
            "percentiles": [16, 84],
            "use_aep": 0,
            "apply_skew": 0,
        },
    }
    result = run_pst(config)
    assert result["status"] == "success"
    out_dir = tmp_path / "pst"
    assert (out_dir / "hc_plot.parquet").exists()
    assert (out_dir / "hc_emp.parquet").exists()
    assert (out_dir / "gpd_params.parquet").exists()
    assert (out_dir / "mrl_selection.json").exists()


def test_stormsim_pst_timeseries_not_implemented():
    import datetime

    base = datetime.datetime(2000, 1, 1).toordinal()
    data = np.zeros((100, 2))
    data[:, 0] = np.arange(base, base + 100, dtype=float)
    data[:, 1] = np.abs(np.random.default_rng(0).normal(size=100)) + 0.1
    response_data = ResponseData(data=data, data_type="Timeseries", annual_rate=2.0)
    pst_options = PSTOptions(t_lag=1.0)
    with pytest.raises(NotImplementedError):
        compute(response_data, pst_options)

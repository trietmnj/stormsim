import pytest
import numpy as np
from stormsim.hazard_curves import jpm
from stormsim.hazard_curves.common import read_parquet


def test_jpm_compute(hazard_curves_input, test_output_dir):
    fpath = hazard_curves_input / "jpm_input.parquet"
    key = "response"

    opts = jpm.Options(
        flag_value=[],
        ua=0.3738,
        ur=0.5840,
        integration_mode="ITCS",
        uncertainty_mode="combined",
        tide_mode="none",
        skewed=False,
        percentiles=[16, 84],
        output_path=test_output_dir,
        return_table=True,
        use_aep=False,
    )
    plt_opts = jpm.PlotOptions(file_name="jpm_output.png", ylabel="Surge (m)")

    jpm.compute(fpath, key, opts, plt_opts=plt_opts)

    # Validate output
    data_plt = read_parquet(test_output_dir / "plot.parquet")
    target_plt = read_parquet(hazard_curves_input / "jpm_output_plt.parquet")
    assert np.allclose(data_plt, target_plt, atol=1e-3, equal_nan=True), (
        "Plot output mismatch"
    )

    if opts.return_table:
        data_tbl = read_parquet(test_output_dir / "table.parquet")
        target_tbl = read_parquet(hazard_curves_input / "jpm_output_tbl.parquet")
        assert np.allclose(data_tbl, target_tbl, atol=1e-3, equal_nan=True), (
            "Table output mismatch"
        )

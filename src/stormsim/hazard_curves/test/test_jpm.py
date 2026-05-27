from pathlib import Path

from tools import compare1d

from stormsim.hazard_curves import jpm

# Test data lives in the canonical tests/ directory
_tests_root = Path(__file__).parents[5] / "tests" / "hazard_curves"
input_path = _tests_root / "input_data"
output_path = Path(__file__).parent / "test_output"

input_path.mkdir(exist_ok=True)
output_path.mkdir(exist_ok=True)

fpath = input_path / "jpm_input.parquet"
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
    output_path=output_path,
    return_table=True,
    use_aep=False,
)

plt_opts = jpm.PlotOptions(file_name="jpm_output.png", ylabel="Surge (m)")

jpm.compute(fpath, key, opts, plt_opts=plt_opts)

fpath_test = output_path / "plot.parquet"
fpath_target = input_path / "jpm_output_plt.parquet"

compare1d("Plot", fpath_test, fpath_target)

if opts.return_table:
    fpath_test = output_path / "table.parquet"
    fpath_target = input_path / "jpm_output_tbl.parquet"
    compare1d("Table", fpath_test, fpath_target)

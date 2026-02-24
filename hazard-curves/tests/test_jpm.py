from pathlib import Path

from tools import compare1d

from hazard_curves import jpm

# Options, compute from hazard_curves import StormSim_JPM

# Input directory for test data
input_path = Path("./input_data")
# Directory to store output files
output_path = Path("./test_output")
output_path = Path("/Users/rdchlmyl/Desktop/test_output")

# Path to parquet file contain data
fpath = input_path / "jpm_input.parquet"
# Column key value to select quantity to compute hazard curve from
key = "response"

# Configuring and executing JPM code
# Note: 1) Can use dict or Options dataclass
#       2) integration_mode, uncertainty_mode, & tide_mode can be initialize
#          with integer, case-insensitive string, or enum
opts = jpm.Options(
    flag_value=[],
    ua=0.3738,
    ur=0.5840,
    #    tide_std=0.1,
    integration_mode="ITCS",
    uncertainty_mode="combined",
    tide_mode="none",
    skewed=False,
    percentiles=[16, 84],
    output_path=output_path,
    return_table=True,
    use_aep=False,
)

# Optional argument
# Set to None to skip plotting
plt_opts = jpm.PlotOptions(file_name="jpm_output.png", ylabel="Surge (m)")

jpm.compute(fpath, key, opts, plt_opts=plt_opts)


# Comparing output with MATLAB output
fpath_test = output_path / "plot.parquet"
fpath_target = input_path / "jpm_output_plt.parquet"

compare1d("Plot", fpath_test, fpath_target)

if opts.return_table:
    fpath_test = output_path / "table.parquet"
    fpath_target = input_path / "jpm_output_tbl.parquet"
    compare1d("Table", fpath_test, fpath_target)

from pathlib import Path

import pyarrow as pa
from tools import *

matlab_dpath = Path("./matlab_data")
parquet_dpath = Path("./input_data")

in_fpath = matlab_dpath / "jpm_input.mat"
out_fpath = parquet_dpath / "jpm_input.parquet"

dtype = pa.float32()
schema = [
    ("datetime", dtype),
    ("response_wo_tides", dtype),
    ("response_skew_tides", dtype),
    ("discrete_storm_weights", dtype),
]

matlab2parquet1d(in_fpath, "data", schema, out_fpath)

schema = [("aep", dtype), ("response", dtype), ("16.00", dtype), ("84.00", dtype)]

in_fpath = matlab_dpath / "jpm_output.mat"
jpm_matlab2parquet1d(in_fpath, "data", schema, parquet_dpath)

from pathlib import Path

import numpy as np
import pyarrow as pa
import scipy.io as sio

from stormsim.hazard_curves.common import read_parquet, save_parquet


def matlab2parquet1d(
    in_fpath: str | Path,
    name: str,
    schema: list[tuple[str, pa.lib.DataType]],
    out_fpath: str | Path,
) -> None:
    data = sio.loadmat(in_fpath)[name]
    save_parquet(data, schema, out_fpath)


def jpm_matlab2parquet1d(
    in_fpath: str | Path,
    name: str,
    schema: list[tuple[str, pa.lib.DataType]],
    out_dpath: str | Path,
) -> None:
    out_dpath = Path(out_dpath)

    keys = ["HC_plt", "HC_tbl", "HC_tbl_rsp_x", "HC_tbl_rsp_y", "HC_plt_x", "HC_tbl_x"]
    out_data = sio.loadmat(in_fpath)[name]
    out_data = {k: out_data[0][0][i] for i, k in enumerate(keys, start=1)}

    data_plt = np.column_stack([out_data[k] for k in ["HC_plt_x", "HC_plt"]])
    fpath = out_dpath / "jpm_output_plt.parquet"
    save_parquet(data_plt, schema, fpath)

    data_tbl = np.column_stack([out_data[k] for k in ["HC_tbl_x", "HC_tbl"]])
    fpath = out_dpath / "jpm_output_tbl.parquet"
    save_parquet(data_tbl, schema, fpath)

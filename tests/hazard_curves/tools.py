from pathlib import Path

import numpy as np
import pyarrow as pa
import scipy.io as sio

from hazard_curves.common import read_parquet, save_parquet


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


def compare1d(name: str, fpath_test: Path, fpath_target: Path) -> None:

    header = f"  {name} Errors  "
    banner = "".join(["-"] * len(header))
    print(banner)
    print(header)
    print(banner)

    data_test = read_parquet(fpath_test)
    data_target = read_parquet(fpath_target)
    diff = np.abs(data_target - data_test)

    print(data_test)
    print(data_target)
    print(data_test.shape, data_target.shape)

    print(f"Max :  {np.nanmax(diff, axis=0)}")
    print(f"Mean: {np.nanmean(diff, axis=0)}")
    print(f"84% : {np.nanpercentile(diff, 84, axis=0)}")
    print(f"90% : {np.nanpercentile(diff, 90, axis=0)}")
    print(f"98% : {np.nanpercentile(diff, 98, axis=0)}")

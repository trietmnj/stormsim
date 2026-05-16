from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import scipy.io as sio
from tests.hazard_curves.tools import matlab2parquet1d, jpm_matlab2parquet1d

_MRL_STRUCT_COLS = ["Threshold", "MeanExcess", "Weight", "WMSE", "GPD_Shape", "GPD_Scale", "Events", "Rate"]
_MRL_STRUCT_FILES = {"03_pst_mrl_summary.mat", "03_pst_mrl_raw_stats.mat"}


def _pst_convert(mat_path: Path, out_dir: Path) -> None:
    try:
        mat_content = sio.loadmat(mat_path, struct_as_record=False, squeeze_me=True)
        data = mat_content.get("data")

        if mat_path.name in _MRL_STRUCT_FILES:
            df = pd.DataFrame({col: getattr(data, col) for col in _MRL_STRUCT_COLS})
        elif isinstance(data, np.ndarray) and data.dtype.names:
            df = pd.DataFrame([data[0][0]])
        else:
            df = pd.DataFrame(data)

        out_path = out_dir / mat_path.with_suffix(".parquet").name
        df.to_parquet(out_path)
        print(f"Converted {mat_path.name} -> {out_path}")
    except Exception as e:
        print(f"Failed to convert {mat_path.name}: {e}")


def _jpm_convert(mat_path: Path, out_dir: Path) -> None:
    try:
        mat_content = sio.loadmat(mat_path, struct_as_record=False, squeeze_me=True)
        data = mat_content.get("data")
        df = pd.DataFrame(data)
        out_path = out_dir / mat_path.with_suffix(".parquet").name
        df.to_parquet(out_path)
        print(f"Converted {mat_path.name} -> {out_path}")
    except Exception as e:
        print(f"Failed to convert {mat_path.name}: {e}")


def run_conversion():
    matlab_dpath = Path(__file__).parent / "matlab_data"
    repo_root = Path(__file__).parents[2]

    # PST: convert *_pst_*.mat files in matlab_data to data/hazard_curves/pst/
    pst_out = repo_root / "data" / "hazard_curves" / "pst"
    pst_out.mkdir(parents=True, exist_ok=True)
    for mat_file in sorted(matlab_dpath.glob("*_pst_*.mat")):
        _pst_convert(mat_file, pst_out)

    # JPM intermediates: convert *_jpm_*.mat files to data/hazard_curves/jpm/
    jpm_data_out = repo_root / "data" / "hazard_curves" / "jpm"
    jpm_data_out.mkdir(parents=True, exist_ok=True)
    for mat_file in sorted(matlab_dpath.glob("*_jpm_*.mat")):
        _jpm_convert(mat_file, jpm_data_out)

    # JPM input/output for existing test fixtures (source files live in bak/)
    jpm_in = matlab_dpath / "bak"
    jpm_out = Path(__file__).parent / "input_data"
    jpm_out.mkdir(exist_ok=True)

    dtype = pa.float32()
    schema = [
        ("datetime", dtype),
        ("response_wo_tides", dtype),
        ("response_skew_tides", dtype),
        ("discrete_storm_weights", dtype),
    ]
    matlab2parquet1d(jpm_in / "jpm_input.mat", "data", schema, jpm_out / "jpm_input.parquet")

    schema = [("aep", dtype), ("response", dtype), ("16.00", dtype), ("84.00", dtype)]
    jpm_matlab2parquet1d(jpm_in / "jpm_output.mat", "data", schema, jpm_out)


if __name__ == "__main__":
    run_conversion()

"""
I/O entry point for the StormSim-JPM hazard curve pipeline.
Loads input data via StorageContext, runs the pure compute pipeline, and writes outputs.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from ...utilities.storage import StorageContext
from .compute import compute
from .core import InputData, Options


def _write_outputs(results: list[tuple[str, Any]], opts: Options, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    x_col = "AEP" if opts.use_aep else "AEF"
    prc_cols = [f"{int(p)}" for p in opts.percentiles]
    cols = [x_col, "Best"] + prc_cols

    name_map = {"plot": "hc_plot", "table": "hc_table"}
    for name, arr in results:
        fname = name_map.get(name, name)
        pd.DataFrame(arr, columns=cols).to_parquet(out_dir / f"{fname}.parquet", index=False)


def run_jpm(
    config: dict[str, Any],
    is_lambda: bool = False,
    storage_context: StorageContext | None = None,
) -> dict[str, Any]:
    """
    Standard entry point for JPM hazard curve fitting.
    Loads input via StorageContext, runs compute, writes outputs.

    Config keys:
      inputs.data_file      — path to N×4 parquet [timestamp, response, skew_tides, DSW]
      outputs               — StorageContext output config
      jpm_params            — InputData fields: flag_value, slc
      jpm_options           — Options fields: ua, ur, tide_std, integration_mode, etc.

    Output files written to the configured output directory:
      hc_plot.parquet   — hazard curve on log-spaced AEF/AEP plot grid (~631 pts);
                          columns: AEF/AEP, Best, [percentiles]
      hc_table.parquet  — hazard curve on discrete return-period table grid (22 pts);
                          same columns; written only when return_table=True
    """
    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)

    input_path = ctx.get_input_path("data_file")
    data = pd.read_parquet(input_path).values

    jpm_params = config.get("jpm_params", {})
    input_data = InputData(
        data=data,
        flag_value=jpm_params.get("flag_value"),
        slc=jpm_params.get("slc", 0.0),
    )
    opts = Options(**config.get("jpm_options", {}))

    results = compute(input_data, opts)

    out_dir = Path(ctx.get_output_path())
    _write_outputs(results, opts, out_dir)

    print(f"JPM outputs written to {out_dir}")
    return {"status": "success", "output": str(out_dir)}

"""
I/O entry point for the StormSim-JPM hazard curve pipeline.
Loads input data via StorageContext, runs the pure compute pipeline, and writes outputs.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from ...utilities.storage import StorageContext
from .compute import compute
from .core import Options
from .plot import PlotOptions


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

    Output files written to the configured output directory:
      hc_plot.parquet   — hazard curve on log-spaced AEF/AEP plot grid (~631 pts);
                          columns: AEF/AEP, Best, [percentiles]
      hc_table.parquet  — hazard curve on discrete return-period table grid (22 pts);
                          same columns; written only when return_table=True

    See compute() for full pipeline details.
    """
    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)

    input_path = ctx.get_input_path("data_file")
    data = pd.read_parquet(input_path).values

    jpm_options = {**config.get("jpm_params", {}), **config.get("jpm_options", {})}
    opts = Options(**jpm_options)

    results = compute(data, opts)

    out_dir = Path(ctx.get_output_path())
    _write_outputs(results, opts, out_dir)

    print(f"JPM outputs written to {out_dir}")
    return {"status": "success", "output": str(out_dir)}

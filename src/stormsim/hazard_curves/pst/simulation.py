import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ...utilities.storage import StorageContext
from .core import PSTOptions, ResponseData
from .compute import compute


def _write_outputs(hc_output, mrl_output, pst_options: PSTOptions, out_dir: Path):
    """Write HC plot, HC empirical, GPD parameters, and MRL selection to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)

    json.dump(
        mrl_output["selection"],
        (out_dir / "mrl_selection.json").open("w"),
        indent=2,
    )

    if mrl_output["summary"] is not None:
        mrl_output["summary"].to_parquet(out_dir / "mrl_summary.parquet", index=False)

    pd.DataFrame(
        np.hstack([mrl_output["gpd_shapes"], mrl_output["gpd_shapes_clipped"]]),
        columns=["gpd_shapes", "gpd_shapes_clipped"],
    ).to_parquet(out_dir / "gpd_params.parquet", index=False)

    x_col = "AEP" if pst_options.use_aep else "AEF"
    prc_cols = [f"{int(p)}" for p in pst_options.percentiles]
    hc_cols = [x_col, "Mean"] + prc_cols
    pd.DataFrame(
        np.hstack([hc_output["hc_plot_x"][:, np.newaxis], hc_output["hc_plot"]]),
        columns=hc_cols,
    ).to_parquet(out_dir / "hc_plot.parquet", index=False)

    hc_output["hc_emp"].to_parquet(out_dir / "hc_emp.parquet", index=False)


def run_pst(
    config: dict[str, Any],
    is_lambda: bool = False,
    storage_context: StorageContext | None = None,
) -> dict[str, Any]:
    """
    Standard entry point for PST hazard curve fitting.
    Loads input via StorageContext, runs compute, writes outputs.

    Output files written to the configured output directory:
      hc_plot.parquet     — bootstrapped mean and percentile curves on a standard log-spaced
                            AEF/AEP grid (~540 pts); columns: AEF/AEP, Mean, [percentiles];
                            includes GPD tail and confidence limits
      hc_emp.parquet      — raw empirical HC from the POT sample, one row per storm event;
                            columns: Response, Rank, CCDF, Hazard (AEF or AEP), ARI
      gpd_params.parquet  — GPD shape parameter per bootstrap simulation, unadjusted and
                            clipped to [-0.5, 0.3]
      mrl_selection.json  — MRL-selected GPD threshold; keys: Criterion, Threshold,
                            Events, Rate
      mrl_summary.parquet — full MRL statistics across all candidate thresholds;
                            written only when GPD fit is applied (N >= 20, record >= 20 yrs)

    See fit_hazard_curve for full details on the hc_output and mrl_output structures.
    """
    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)

    input_path = ctx.get_input_path("data_file")
    data = pd.read_parquet(input_path).values

    pst_params = config.get("pst_params", {})
    response_data = ResponseData(
        data=data,
        flag_value=pst_params.get("flag_value"),
        n_years=pst_params.get("n_years"),
        slc=pst_params.get("slc", 0),
        data_type=pst_params.get("data_type", "POT"),
        gpr_mdl=pst_params.get("gpr_mdl"),
    )
    pst_options = PSTOptions(**config.get("pst_options", {}))

    hc_output, mrl_output = compute(response_data, pst_options)

    out_dir = Path(ctx.get_output_path())
    _write_outputs(hc_output, mrl_output, pst_options, out_dir)

    print(f"PST outputs written to {out_dir}")
    return {"status": "success", "output": str(out_dir)}

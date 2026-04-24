from pathlib import Path

import pyarrow as pa
from stormsim.hazard_curves.common import read_parquet, save_parquet
from .core import Options
from .engine import preprocess, integrate, interpolate_results
from .plot import PlotOptions

import pandas as pd

def compute(
    fpath: str | Path,
    key: str,
    options: dict | Options,
    plt_opts: dict | PlotOptions | None = None,
):
    """
    Orchestrates the JPM (Joint Probability Method) computation pipeline:
    data loading -> preprocessing -> integration -> interpolation -> export.
    """

    # Validating options
    if isinstance(options, dict):
        opts = Options(**options)
    else:
        opts = options

    # Dynamically construct schema based on key
    schema = [
        "datetime",
        f"{key}_wo_tides",
        f"{key}_skew_tides",
        "discrete_storm_weights",
    ]
    data = read_parquet(fpath, schema)

    # Preprocessing data before integration
    resp, prob_mass = preprocess(data, opts)

    # Computing integration
    x, y = integrate(resp, prob_mass, opts)

    # Interpolating data onto new partition(s)
    datai = interpolate_results(x, y, opts)

    dtype = pa.float32()
    schema = [("aep", dtype), ("response", dtype)]
    schema.extend([(f"{p:.2f}", dtype) for p in opts.percentiles])

    assert isinstance(opts.output_path, Path)

    opts.output_path.mkdir(exist_ok=True, parents=True)
    for f, d in datai:
        fpath = opts.output_path / f"{f}.parquet"
        save_parquet(d, schema, fpath)

    if not plt_opts is None:

        if isinstance(plt_opts, dict):
            plt_opts = PlotOptions(**plt_opts)

        _, d = datai[0]
        plt_opts.plot(d, opts)

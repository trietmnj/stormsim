from pathlib import Path

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from hazard_curves.jpm.plot import PlotOptions

from ..common import get_plot_x_values, get_table_x_values, read_parquet, save_parquet
from .core import IntegrationEnum, Options, TideEnum

# from scipy.stats import norm


def compute(
    fpath: str | Path,
    key: str,
    options: dict | Options,
    plt_opts: dict | PlotOptions | None = None,
):

    # Validating options
    if isinstance(options, dict):
        opts = Options(**options)
    else:
        opts = options

    # NOTE: Are we using standard column names?
    schema = [
        "datetime",
        f"{key}_wo_tides",
        f"{key}_skew_tides",
        "discrete_storm_weights",
    ]
    data = read_parquet(fpath, schema)

    # Preprocessing data before integration

    resp, prob_mass = _preprocess(data, opts)

    # Computing integration
    x, y = _integration(resp, prob_mass, opts)

    # Interpolating data onto new partition(s)
    datai = _interpolate(x, y, opts)

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


def _interpolate(x: NDArray, y: NDArray, opts: Options) -> list[tuple[str, NDArray]]:

    # kwargs = dict(
    #     k=0,
    #     extrapolate=False,
    # )
    # return BSpline(x, y, **kwargs)(np.log(xi))

    # NOTE: interp1d legacy command, closest replacement that
    #       that operates on 2D array is BSpline, however,
    #       returns slightly different result
    kwargs = dict(kind="linear", fill_value=np.nan, bounds_error=False, axis=0)
    interp = interp1d(x, y, **kwargs)

    plt_x = get_plot_x_values()
    plt_y = interp(np.log(plt_x))

    args = [("plot", plt_x, plt_y)]

    if opts.return_table:
        tbl_x = get_table_x_values(opts.use_aep)
        tbl_y = interp(np.log(tbl_x))
        tbl_y[tbl_y < 0] = np.nan
        args.append(("table", tbl_x, tbl_y))

    return [(p, np.column_stack([x, y])) for p, x, y in args]


def _preprocess(data: NDArray, opts: Options) -> tuple[NDArray, NDArray]:
    """Returns response and probability mass function after validation and preprocessing"""
    # Removing flag values
    if opts.flag_value is not None:

        mask = np.isin(data[:, 1], opts.flag_value, invert=True)
        # mask = data[:, 1] != opts.flag_value
        data = data[mask, :]

        if data.size == 0:
            raise RuntimeError("Flag value response removal yielded empty dataset.")

    # Removing invalid values
    mask = np.isfinite(data[:, 1]) & (data[:, 1] > 0)
    data = data[mask, :]
    if data.size == 0:
        raise RuntimeError("Invalid response removal yielded empty dataset.")

    idxs = [1, 2, 3]
    resp, u_tide, prob_mass = [data[:, i] for i in idxs]

    # Ignoring u_tide if skewed
    # Note: skewed is always False unless TideEnum=PREPROCESS
    if not opts.skewed:
        u_tide[:] = 0

    # Returning data if not further preprocessing
    # if opts.tide_mode != TideEnum.PREPROCESS:
    #    return resp, prob_mass

    nr = len(resp)
    random_norm = opts.get_random_norm(nr)
    u_tide[:] = opts.tide_std

    # Removing SLC before corrections
    resp = resp - opts.slc

    # Apply uncertainty correction for ITCS
    if opts.integration_mode == IntegrationEnum.ITCS:

        # Discrete Gaussian Z-scores
        nn = len(random_norm)
        random_norm = np.sort(np.tile(random_norm, nr))

        prob_mass = np.tile(prob_mass / nn, nn)
        resp = np.tile(resp, nn)
        u_tide = np.tile(u_tide, nn)

        # Apply first partition
        resp = resp + random_norm * (opts._p1_a + resp * opts._p1_r) / 2.0

    # Reapply tide correction
    resp = resp + random_norm * u_tide + opts.slc

    mask = np.isfinite(resp) & (resp > 0)
    resp = resp[mask]
    prob_mass = prob_mass[mask]
    if resp.size == 0:
        raise RuntimeError(
            "Invalid response removal after integration preprocessing yielded empty dataset."
        )

    return resp, prob_mass


def _integration(
    resp: NDArray, prob_mass: NDArray, opts: Options
) -> tuple[NDArray, NDArray]:
    """Returns integration of probability mass function and response
    with applied percentiles and confidence limits"""

    idx = np.argsort(resp)[::-1]
    y = resp[idx]
    x = np.cumsum(prob_mass[idx])

    # Offsetting zero for log plot
    x[x == 0] = 1e-16

    # Remove duplicates (x then y)
    _, ia = np.unique(x, return_index=True)
    x, y = x[ia], y[ia]
    _, iy = np.unique(y, return_index=True)
    x, y = x[iy], y[iy]

    # Sort ascending in x
    order = np.argsort(x)
    x = np.log(x[order])
    y = y[order]

    # Computing percentiles with confidence limits
    y = opts.apply_confidence_limits(y)

    return x, y

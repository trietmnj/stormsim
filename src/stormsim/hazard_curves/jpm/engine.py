import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from ..common import get_plot_x_values, get_table_x_values
from .core import IntegrationEnum, Options


def integrate(
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


def interpolate_results(
    x: NDArray, y: NDArray, opts: Options
) -> list[tuple[str, NDArray]]:

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


def preprocess(data: NDArray, opts: Options) -> tuple[NDArray, NDArray]:
    """Returns response and probability mass function after validation and preprocessing"""
    # Removing flag values
    if opts.flag_value is not None:

        mask = np.isin(data[:, 1], opts.flag_value, invert=True)
        data = data[mask, :]

        if data.size == 0:
            raise RuntimeError(
                f"Flag value removal (flag_value={opts.flag_value}) resulted in an empty dataset. "
                "Ensure flag_value matches the data values."
            )

    # Removing invalid values
    if data.ndim < 2 or data.shape[1] < 2:
        raise RuntimeError("Input data must be at least 2D with at least 2 columns.")
    mask = np.isfinite(data[:, 1]) & (data[:, 1] > 0)
    data = data[mask, :]
    if data.size == 0:
        raise RuntimeError(
            "Invalid response removal (masking finite and positive values) resulted in an empty dataset. "
            "Check for non-numeric or non-positive values in the response column."
        )

    idxs = [1, 2, 3]
    resp, u_tide, prob_mass = [data[:, i] for i in idxs]

    # Ignoring u_tide if skewed
    # Note: skewed is always False unless TideEnum=PREPROCESS
    if not opts.skewed:
        u_tide[:] = 0

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
            "Integration preprocessing resulted in an empty dataset after tide/SLC correction. "
            f"Check SLC parameter (slc={opts.slc}) and tide parameters."
        )

    return resp, prob_mass

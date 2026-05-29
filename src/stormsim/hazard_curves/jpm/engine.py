"""
Core integration engine for the StormSim-JPM pipeline.
Original MATLAB implementation: StormSim_JPM_integration.m
Authors: N.C. Nadal-Caraballo, E. Ramos-Santiago (ERDC-CHL Coastal Hazards Group)
"""

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from ..common import get_plot_x_values, get_table_x_values
from .core import IntegrationEnum, Options


def integrate(
    resp: NDArray, prob_mass: NDArray, opts: Options
) -> tuple[NDArray, NDArray]:
    """
    Integrate probability mass against response to produce the hazard curve (StormSim_JPM_integration.m).

    Sorts response descending, cumulates discrete storm weights to get exceedance
    frequencies, deduplicates in both x and y, takes log of x, then appends
    percentile columns via apply_confidence_limits.

    Returns:
        x  (K,)       log-exceedance frequencies (input to interpolation)
        y  (K, 1+n)   response column-stacked with n percentile columns
    """

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
    """
    Interpolate the integrated hazard curve onto standard plot and table grids.

    Plot grid uses NaN fill outside integration range (matching MATLAB interp1 default).
    Table grid uses linear extrapolation (matching MATLAB interp1(...,'extrap')); negative
    extrapolated values are replaced with NaN.

    Returns a list of (name, array) pairs:
        "plot"   — shape (n_plt, 1+n_prc); log-spaced AEF/AEP grid (~631 pts)
        "table"  — shape (n_tbl, 1+n_prc); discrete return-period grid (22 pts); return_table only
    """

    interp = interp1d(x, y, kind="linear", fill_value=np.nan, bounds_error=False, axis=0)
    interp_extrap = interp1d(x, y, kind="linear", fill_value="extrapolate", bounds_error=False, axis=0)

    plt_x = get_plot_x_values()
    plt_y = interp(np.log(plt_x))

    args = [("plot", plt_x, plt_y)]

    if opts.return_table:
        tbl_x = get_table_x_values(opts.use_aep)
        tbl_y = interp_extrap(np.log(tbl_x))
        tbl_y[tbl_y < 0] = np.nan
        args.append(("table", tbl_x, tbl_y))

    return [(name, np.column_stack([grid_x, grid_y])) for name, grid_x, grid_y in args]


def preprocess(data: NDArray, opts: Options) -> tuple[NDArray, NDArray]:
    """
    Validate, filter, and tile the input dataset before integration (StormSim_JPM_integration.m).

    Steps:
      1. Remove flag values and non-finite / non-positive response entries.
      2. For ITCS: tile response and DSW over the 444-point discrete Gaussian replicates;
         apply first-partition uncertainty correction (p1_a, p1_r) to the tiled response.
      3. Add tide uncertainty and sea-level-change correction to response.
      4. Remove any entries that become non-finite or non-positive after correction.

    Returns:
        resp       (M,)  preprocessed response (M = N × 444 for ITCS, M = N for ATCS)
        prob_mass  (M,)  corresponding discrete storm weights
    """
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

    nr = len(resp)
    random_norm = opts.get_random_norm(nr)
    # When skewed=True (TideEnum.PREPROCESS + ind_Skew=1), u_tide holds skew values from
    # the data column; otherwise opts.tide_std is the scalar std (0 when tide_mode=NONE).
    if not opts.skewed:
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

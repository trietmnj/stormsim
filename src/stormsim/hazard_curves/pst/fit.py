"""
Hazard curve fitting for the StormSim-PST pipeline.
Original MATLAB implementation: StormSim_PST_Fit.m, ecdf_boot.m, Monotonic_adjustment.m
Authors: N.C. Nadal-Caraballo, E. Ramos-Santiago (ERDC-CHL Coastal Hazards Group)
"""

import numpy as np
import pandas as pd
import scipy.stats as scstats
from scipy import interpolate

from ..common import aef2aep, get_grid_values_v1
from .core import PSTOptions
from .mrl import fit_mrl


def bootstrap_ecdf(emp_hc, n_sims: int, test_data: None | dict = None):
    """
    Bootstrap resampling of the empirical hazard curve (ecdf_boot.m).

    Resamples POT peaks with replacement (Weibull plotting position) and applies
    normal jitter scaled by adjacent-sample differences to smooth the empirical
    distribution. When test_data is supplied, fixed random seeds are used for
    reproducibility against MATLAB reference outputs.
    """
    np.random.seed()
    n_storms = len(emp_hc)
    diffs = np.abs(np.diff(emp_hc))
    diffs = np.append(diffs, diffs[-1])

    if test_data is None:
        shape = (n_sims, n_storms)
        indices = np.random.choice(np.arange(n_storms), shape, replace=True)
        rand = np.random.randn(*shape)
    else:
        # test_data supplies flat arrays matching the reference output shape
        indices = test_data["indices"].reshape(n_sims, n_storms).astype(int)
        rand = test_data["random"].reshape(n_sims, n_storms)

    boot = emp_hc[indices] + rand * diffs[indices]
    boot = np.fliplr(np.sort(boot, axis=1))

    return boot


def monotonic_adjustment(x_in, y_in):
    """
    Enforce non-increasing monotonicity on a hazard curve column (Monotonic_adjustment.m).

    SST can produce non-monotonic curves when the MRL-selected GPD threshold is too
    low, causing incomplete bootstrap samples and jumps in the mean curve or confidence
    limits. Positive slopes on the log-AEF axis are corrected by extrapolating from the
    two preceding slope values.
    """
    x_in = np.log(np.asarray(x_in).flatten())
    y_in = np.asarray(y_in).flatten()

    idx3 = ~np.isnan(y_in)
    y = y_in[idx3].copy()
    x = x_in[idx3].copy()

    dx = np.diff(x)
    dy = np.diff(y)
    s = dy / dx

    id_pos = np.where(s > 0)[0]

    if len(id_pos) > 0:
        for i in id_pos:
            start_idx = max(i - 2, 0)
            end_idx = i
            mean_slope = np.mean(s[start_idx:end_idx])
            y[i + 1] = mean_slope * dx[i] + y[i]

    y_in[idx3] = y
    return y_in.reshape(1, -1)  # row vector like MATLAB output


def fit_hazard_curve(
    pot_no_tides,
    _pot_with_tides,  # placeholder: tidal component not yet implemented
    _slc,  # placeholder: sea level change not yet implemented
    n_years,
    _gpr_mdl,  # placeholder: GPR skew correction not yet implemented
    pst_options: PSTOptions,
    test_ecdf_data: None | dict = None,
):
    """
    Fit a hazard curve from a POT sample using bootstrapped ECDF and optional
    GPD tail extension (StormSim_PST_Fit.m).

    Pipeline:
      1. Build empirical HC: Weibull plotting position with lambda (rate) correction.
      2. Bootstrap-resample the ECDF (bootstrap_ecdf).
      3. Select GPD threshold via MRL when N >= 20 and record >= 20 yrs,
         or when apply_gpd=1 is forced.
      4. Fit GPD to exceedances above threshold for each bootstrap simulation;
         clip shape parameter to [-0.5, 0.3] per NCNC guidance.
      5. Combine GPD tail with empirical body; interpolate onto standard AEF grid.
      6. Compute mean and percentile curves; apply monotonic adjustment.
      7. Interpolate onto standard response-level and AEF table grids.

    Returns:
        hc_output:
            hc_plot          (n_grid, 1+n_prc)       — bootstrapped mean and percentile curves on
                             the standard AEF/AEP plot grid; columns are [Mean, prc_1, ...]
            hc_plot_x        (n_grid,)                — standard log-spaced AEF/AEP plot grid
                             (~540 points, 10^1 down to 10^-6)
            hc_emp           DataFrame (N, 5)         — raw empirical HC from the POT sample,
                             one row per storm; columns: Response, Rank, CCDF, Hazard, ARI
            hc_table         (n_tbl, 1+n_prc)        — response values interpolated onto the
                             standard discrete return-period table grid
            hc_table_x       (n_tbl,)                 — standard AEF/AEP table grid (discrete
                             return periods, e.g. 1/2 to 1/1e6)
            hc_table_aef_at_response (n_rsp, 1+n_prc) — AEF at each standard response
                             level; inverse lookup of hc_table
            hc_table_response (n_rsp,)                — standard response grid (0.01 to 20 m,
                             step 0.01)
            record_length    float                    — record length in years

        mrl_output:
            summary          DataFrame or None        — MRL statistics at each candidate
                             threshold; columns: Threshold, MeanExcess, Weight, WMSE,
                             GPD_Shape, GPD_Scale, Events, Rate; None if GPD not applied
            selection        dict or None             — selected threshold; keys: Criterion,
                             Threshold, id_Summary, Events, Rate; None if no minimum found
            gpd_shapes       (n_sims, 1)              — fitted GPD shape parameter k, unadjusted
            gpd_scales       (n_sims, 1)              — fitted GPD scale parameter σ
            gpd_thresholds   (n_sims, 1)              — GPD threshold used per simulation
            gpd_shapes_clipped (n_sims, 1)            — k clipped to [-0.5, 0.3] per NCNC guidance
    """

    hc_table_x, hc_table_response, hc_plot_x = get_grid_values_v1(
        pst_options.use_aep == 1
    )

    # Pre-allocate output fields
    boot_responses = np.full((pst_options.bootstrap_sims, len(hc_plot_x)), np.nan)
    gpd_shapes = np.full((pst_options.bootstrap_sims, 1), np.nan)
    gpd_scales = gpd_shapes.copy()
    gpd_thresholds = gpd_shapes.copy()
    gpd_shapes_clipped = gpd_shapes.copy()

    # Sort POT sample in descending order for ECDF
    pot_no_tides = np.sort(pot_no_tides)[::-1]
    n_storms = len(pot_no_tides)
    hc_emp = np.full((n_storms, 5), np.nan)
    hc_emp[:, 0] = pot_no_tides.copy()
    hc_emp[:, 1] = np.arange(1, n_storms + 1)
    hc_emp[:, 2] = hc_emp[:, 1] / (n_storms + 1)
    rate_hist = n_storms / n_years

    hc_emp[:, 3] = hc_emp[:, 2] * rate_hist
    hc_emp[:, 4] = 1.0 / hc_emp[:, 3]

    sorted_peaks = hc_emp[:, 0]
    if pst_options.use_aep:
        hc_emp[:, 3] = aef2aep(hc_emp[:, 3])
        hc_plot_x = aef2aep(hc_plot_x)

    # Bootstrap resampling
    boot = bootstrap_ecdf(sorted_peaks, pst_options.bootstrap_sims, test_ecdf_data)
    boot[boot < 0] = np.nan

    # GPD fitting when conditions are met
    apply_gpd = (
        len(sorted_peaks) >= 20 and n_years >= 20
    ) or pst_options.apply_gpd == 1
    summary, selection = None, None
    if apply_gpd:
        try:
            summary, selection = fit_mrl(
                pst_options.gpd_criterion, sorted_peaks, n_years
            )
        except ValueError:
            pass

        if selection is None:
            # No threshold found (small N or no WMSE local minima): use per-simulation
            # minimum as fallback threshold, matching MATLAB's isnan(mrl_th) branch.
            thresholds = 0.99 * np.nanmin(boot, axis=1)
            above_th = boot > thresholds[:, None]
            below_th = boot <= thresholds[:, None]
            n_above = np.sum(above_th, axis=1)
        else:
            threshold = selection["Threshold"]
            above_th = boot > threshold
            below_th = boot <= threshold
            n_above = np.sum(above_th, axis=1)
            thresholds = np.full(pst_options.bootstrap_sims, threshold)

        rate_mrl = n_above / n_years
        for k in range(pst_options.bootstrap_sims):
            boot_peaks = boot[k, :]

            exceedances = boot_peaks[above_th[k, :]]
            if len(exceedances) == 0:
                continue
            fit_result = scstats.genpareto.fit(
                exceedances - thresholds[k], method="MLE", floc=0
            )
            gpd_shapes[k] = fit_result[0]
            gpd_thresholds[k] = thresholds[k]
            gpd_scales[k] = fit_result[2]

        # Correction of GPD shape parameter values. Limits determined by NCNC.
        gpd_shapes_clipped = gpd_shapes.copy()
        shape_min = -0.5
        shape_max = 0.3
        gpd_shapes_clipped[gpd_shapes_clipped < shape_min] = shape_min
        gpd_shapes_clipped[gpd_shapes_clipped > shape_max] = shape_max

    # Compute hazard curve per bootstrap simulation
    for k in range(pst_options.bootstrap_sims):
        if apply_gpd:
            if np.isnan(gpd_shapes[k]) or rate_mrl[k] == 0:
                continue

            gpd_params = {
                "c": gpd_shapes_clipped[k][0],
                "loc": gpd_thresholds[k][0],
                "scale": gpd_scales[k][0],
            }

            resp_gpd = scstats.genpareto.ppf(1 - hc_plot_x / rate_mrl[k], **gpd_params)

            valid = ~np.isnan(resp_gpd)
            aef_gpd = hc_plot_x[valid]
            resp_gpd = resp_gpd[valid]

            resp_ecdf = boot[k, below_th[k, :]]
            aef_ecdf = hc_emp[below_th[k, :], 3]

            aef_combined = np.concatenate([aef_gpd, aef_ecdf])
            resp_combined = np.concatenate([resp_gpd, resp_ecdf])

            if len(aef_combined) == 0:
                continue
        else:
            resp_combined = boot[k, :]
            aef_combined = hc_emp[:, 3]

        if pst_options.use_aep:
            aef_combined = aef2aep(aef_combined)

        _, uniq_idx = np.unique(aef_combined, return_index=True)
        uniq_idx = np.sort(uniq_idx)
        aef_combined = aef_combined[uniq_idx]
        resp_combined = resp_combined[uniq_idx]

        _, uniq_idx = np.unique(resp_combined, return_index=True)
        uniq_idx = np.sort(uniq_idx)
        resp_combined = resp_combined[uniq_idx]
        aef_combined = aef_combined[uniq_idx]

        # np.interp requires ascending x; MATLAB's interp1 handles descending,
        # so we sort here rather than flipud as the MATLAB code does.
        sort_idx = np.argsort(aef_combined)
        aef_combined = aef_combined[sort_idx]
        resp_combined = resp_combined[sort_idx]

        boot_responses[k, :] = np.interp(
            np.log(hc_plot_x),
            np.log(aef_combined),
            resp_combined,
            right=np.nan,
            left=np.nan,
        )

    mean_hc = np.mean(boot_responses, axis=0)
    prc_hc = np.nanpercentile(
        boot_responses, pst_options.percentiles, axis=0, method="midpoint"
    )

    hc_plot = np.vstack([mean_hc, prc_hc]).T

    if pst_options.apply_skew and (np.nanmax(mean_hc) >= 10**3):
        raise ValueError("Values above 10^3 found in mean hazard curve")

    for col_idx in range(hc_plot.shape[1]):
        hc_plot[:, col_idx] = monotonic_adjustment(hc_plot_x, hc_plot[:, col_idx])

    hc_table_aef_at_response = np.full(
        (len(hc_table_response), hc_plot.shape[1]), np.nan
    )
    hc_table = np.full((len(hc_table_x), hc_plot.shape[1]), np.nan)

    for col_idx in range(hc_plot.shape[1]):
        args = np.unique(hc_plot[:, col_idx], return_index=True)
        resp_vals, uniq_idx = (np.flipud(s) for s in args)
        log_aef_vals = np.log(hc_plot_x[uniq_idx])

        nan_mask = np.isnan(resp_vals) | np.isinf(resp_vals)
        resp_vals = resp_vals[~nan_mask]
        log_aef_vals = log_aef_vals[~nan_mask]

        if len(resp_vals) < 2:
            hc_table_aef_at_response[:, col_idx] = np.nan
            hc_table[:, col_idx] = np.nan
        else:
            interp_fn = interpolate.interp1d(
                resp_vals, log_aef_vals, fill_value="extrapolate"
            )
            hc_table_aef_at_response[:, col_idx] = np.exp(interp_fn(hc_table_response))

            interp_fn = interpolate.interp1d(
                log_aef_vals, resp_vals, fill_value="extrapolate"
            )
            hc_table[:, col_idx] = interp_fn(np.log(hc_table_x))

    hc_table[hc_table < 0] = np.nan
    hc_table_aef_at_response[hc_table_aef_at_response < 1e-4] = np.nan

    cols = ["Response", "Rank", "CCDF", "Hazard", "ARI"]
    hc_emp = pd.DataFrame(hc_emp, columns=cols)
    mrl_output = {
        "summary": summary,
        "selection": selection,
        "gpd_thresholds": gpd_thresholds,
        "gpd_shapes": gpd_shapes,
        "gpd_scales": gpd_scales,
        "gpd_shapes_clipped": gpd_shapes_clipped,
    }
    hc_output = {
        "record_length": n_years,
        "hc_plot": hc_plot,
        "hc_table": hc_table,
        "hc_table_aef_at_response": hc_table_aef_at_response,
        "hc_emp": hc_emp,
        "hc_table_response": hc_table_response,
        "hc_plot_x": hc_plot_x,
        "hc_table_x": hc_table_x,
    }

    return hc_output, mrl_output

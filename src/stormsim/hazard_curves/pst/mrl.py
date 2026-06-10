"""
Mean Residual Life (MRL) threshold selection for GPD fitting.
Original MATLAB implementation: StormSim_MRL.m
Authors: N.C. Nadal-Caraballo, E. Ramos-Santiago (ERDC-CHL Coastal Hazards Group)
"""

import numpy as np
import pandas as pd
import scipy.stats as scstats
from scipy.linalg import lstsq
from scipy.signal import find_peaks


def fit_mrl(gpd_criterion: int, peaks, n_years: float):
    """
    Automated GPD threshold selection via the Mean Residual Life method.

    Follows the five-step procedure from StormSim_MRL.m:
      1. Use sorted POT values as candidate thresholds.
      2. Estimate mean excesses e(u) and inverse-variance weights at each threshold.
      3. Fit weighted linear model to (u, e(u)); compute WMSE at each threshold.
      4. Smooth WMSE with kernel regression and identify local minima.
      5. Select threshold by sample-intensity criterion (gpd_criterion=1) or
         minimum-WMSE criterion (gpd_criterion=2).

    Returns (summary DataFrame, selection dict), or (summary, None) when no local
    minimum is found. Raises ValueError for N <= 20.
    """
    sorted_peaks = np.sort(peaks)
    n_peaks = len(sorted_peaks)

    if n_peaks <= 20:
        raise ValueError(f"Insufficient sample size for MRL: need >20, got {n_peaks}")

    mrl = np.full((n_peaks - 10, 8), np.nan)

    # Step 2: Estimate mean values of excesses
    for i in range(n_peaks - 10):
        mrl[i, 0] = sorted_peaks[i]
        exceedances = peaks[peaks > sorted_peaks[i]]
        mrl[i, 1] = np.mean(exceedances - sorted_peaks[i])
        # ddof=1 matches MATLAB's var()
        mrl[i, 2] = (n_peaks - i - 1) / np.nanvar(
            exceedances - sorted_peaks[i], ddof=1
        )

    weights = mrl[:, 2].ravel()
    sqrt_weights = np.sqrt(weights)
    x_wtd = np.stack([np.ones(n_peaks - 10), mrl[:, 0]]).T * sqrt_weights[:, None]
    y_wtd = mrl[:, 1] * sqrt_weights

    valid = ~np.isnan(y_wtd)
    # Step 3: Fit linear model and compute GPD parameters
    for j in range(n_peaks - 20):
        exceedances = peaks[peaks > sorted_peaks[j]]

        x_sub = x_wtd[j:, :][valid[j:], :]
        y_sub = y_wtd[j:][valid[j:]]
        _, residual_norm, *_ = lstsq(x_sub, y_sub)
        # Converting from L2 norm to mean
        mrl[j, 3] = residual_norm / len(y_sub)

        # Fit GPD to data above threshold
        gpd_params = scstats.genpareto.fit(
            exceedances - sorted_peaks[j], method="MLE", floc=0
        )

        mrl[j, 4] = gpd_params[0]  # Shape parameter (k)
        mrl[j, 5] = gpd_params[2]  # Scale parameter (sigma)

    # Step 4: Estimate sample intensity (lambda)
    for k in range(len(mrl)):
        mrl[k, 6] = np.sum(mrl[:, 0] > mrl[k, 0])
    mrl[:, 7] = mrl[:, 6] / n_years

    # Step 5: Threshold selection using WMSE and Sample Intensity criteria
    mrl = mrl[~np.isnan(mrl[:, 3])]

    # Hardcoded to match MATLAB's kernel bandwidth for WMSE smoothing
    bandwidth = 0.01 - 4.6613e-05
    _, mrl[:, 3] = kern_reg_local_mean(mrl[:, 0], mrl[:, 3], bandwidth)

    cols = [
        "Threshold",
        "MeanExcess",
        "Weight",
        "WMSE",
        "GPD_Shape",
        "GPD_Scale",
        "Events",
        "Rate",
    ]
    summary = pd.DataFrame(mrl, columns=cols)

    # Identify local minima using scipy.signal.find_peaks
    local_min_idx, _ = find_peaks(-mrl[:, 3])
    if len(local_min_idx) < 1:
        return summary, None

    mrl_at_minima = mrl[local_min_idx, :]

    if gpd_criterion == 2:
        criterion_name = "CritWMSE"
        # Match MATLAB: select local minimum with the smallest threshold
        i = np.nanargmin(mrl_at_minima[:, 0])
    else:
        criterion_name = "CritSI"
        rate_diff = mrl_at_minima[:, 7] - 2
        rate_diff[rate_diff < -1] = np.nan

        if np.all(np.isnan(rate_diff)):
            i = np.argmax(mrl_at_minima[:, 7])
        else:
            i = np.nanargmin(np.abs(rate_diff))

    selection = {
        "Criterion": criterion_name,
        "Threshold": float(mrl_at_minima[i, 0]),
        "id_Summary": int(local_min_idx[i]),
        "Events": int(mrl_at_minima[i, 6]),
        "Rate": float(mrl_at_minima[i, 7]),
    }

    return summary, selection


# d-variate normal kernel
def _kernel_weight(bandwidth, sq_dist, n_dims):
    return (bandwidth**-n_dims) * (2 * np.pi) ** (n_dims / 2) * np.exp(-0.5 * sq_dist)


def kern_reg_local_mean(x, y, bandwidth):
    """
    Nadaraya-Watson kernel regression (local mean) smoother.

    Used to remove noise from the WMSE curve before local-minima detection,
    matching KernReg_LocalMean.m. Bandwidth is derived from ksdensity in the
    original MATLAB code and hard-coded here for parity.
    """
    x = np.atleast_2d(x).T
    y = np.asarray(y).reshape(-1)

    n_pts, n_dims = x.shape
    x_mat = x.copy()

    y_out = np.zeros(n_pts)

    # regression loop
    for i in range(n_pts):
        sq_dist = np.sum((x_mat[i, :] - x) ** 2, axis=1) / (bandwidth**2)

        design_mat = np.ones((n_pts, 1))
        weight_mat = np.diag(_kernel_weight(bandwidth, sq_dist, n_dims))

        # (X'WX)^{-1} X'W y
        y_out[i] = np.linalg.solve(
            design_mat.T @ weight_mat @ design_mat, design_mat.T @ weight_mat @ y
        ).flatten()[0]

    return x_mat, y_out

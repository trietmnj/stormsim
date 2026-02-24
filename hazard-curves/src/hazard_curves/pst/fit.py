import numpy as np
import pandas as pd
import scipy.stats as scstats
from scipy import interpolate

from ..common import aef2aep, get_grid_values
from .core import PSTOptions
from .mrl import StormSim_MRL


def ecdf_boot(empHC, Nsim: int, test_data: None | dict = None):
    """
    Bootstrap resampling of the empirical hazard curve (HC) with normal noise
    applied to the samples based on their differences.
    """
    np.random.seed()
    Nstrm = len(empHC)
    dlt = np.abs(np.diff(empHC))
    dlt = np.append(dlt, dlt[-1])  # Repeat the last difference

    shp = (Nsim, Nstrm)

    if test_data is None:
        indices = np.random.choice(np.arange(Nstrm), shp, replace=True)
        rand = np.random.randn(*shp)
    else:
        # Using random data generated for MATLAB for testing
        indices = test_data["indices"].astype(int)
        rand = test_data["random"]

    boot = empHC[indices] + rand * dlt[indices]
    boot = np.fliplr(np.sort(boot, axis=1))

    return boot


def Monotonic_adjustment(x_in, y_in):
    """
    Adjust y-values to enforce monotonicity (non-increasing) along the log-scaled x-axis.
    """
    x_in = np.log(np.asarray(x_in).flatten())
    y_in = np.asarray(y_in).flatten()

    # Select non-NaN entries
    idx3 = ~np.isnan(y_in)
    y = y_in[idx3].copy()
    x = x_in[idx3].copy()

    # Compute slopes
    dx = np.diff(x)
    dy = np.diff(y)
    s = dy / dx

    # Identify positive slopes
    id_pos = np.where(s > 0)[0]

    if len(id_pos) > 0:
        for i in id_pos:
            # Take average of previous slopes, careful with index bounds
            start_idx = max(i - 2, 0)
            end_idx = i
            mean_slope = np.mean(s[start_idx:end_idx])
            y[i + 1] = mean_slope * dx[i] + y[i]

    # Return adjusted values to original positions
    y_in[idx3] = y
    return y_in.reshape(1, -1)  # row vector like MATLAB output


def StormSim_PST_Fit(
    POT_no_tides,
    POT_with_tides,
    SLC,
    Nyrs,
    gprMdl,
    pst_options: PSTOptions,
    #    plot_options: PlotOptions,
    test_ecdf_data: None | dict = None,
):
    """
    Function to perform StormSim hazard curve fitting with monotonic adjustment.
    """

    HC_tbl_x, HC_tbl_rsp_y, HC_plt_x = get_grid_values(pst_options.use_AEP == 1)

    # Pre-allocate Output Fields
    Resp_boot_plt = np.full((pst_options.bootstrap_sims, len(HC_plt_x)), np.nan)
    pd_k_wOut = np.full((pst_options.bootstrap_sims, 1), np.nan)
    pd_sigma = pd_k_wOut.copy()
    pd_TH_wOut = pd_k_wOut.copy()
    pd_k_mod = pd_k_wOut.copy()

    # Develop empirical CDF (using output of POT function)
    # Sort POT sample in descending order
    POT_no_tides = np.sort(POT_no_tides)[::-1]
    Nstrm_hist = len(POT_no_tides)
    HC_emp = np.full((Nstrm_hist, 5), np.nan)
    HC_emp[:, 0] = POT_no_tides.copy()
    HC_emp[:, 1] = np.arange(1, Nstrm_hist + 1)
    HC_emp[:, 2] = HC_emp[:, 1] / (Nstrm_hist + 1)
    Lambda_hist = Nstrm_hist / Nyrs

    HC_emp[:, 3] = HC_emp[:, 2] * Lambda_hist
    HC_emp[:, 4] = 1.0 / HC_emp[:, 3]

    ecdf_y = HC_emp[:, 0]
    if pst_options.use_AEP:
        HC_emp[:, 3] = aef2aep(HC_emp[:, 3])
        HC_plt_x = aef2aep(HC_plt_x)

    # Bootstrap resampling
    boot = ecdf_boot(ecdf_y, pst_options.bootstrap_sims, test_ecdf_data)

    # Remove negative values from bootstrapped data
    boot[boot < 0] = np.nan

    # Perform SST with GPD fitting
    # If conditions are met for GPD fitting, apply it
    gpd_pass = len(ecdf_y) >= 20 and Nyrs >= 20
    if gpd_pass:
        summary, selection = StormSim_MRL(pst_options.GPD_TH_crit, ecdf_y, Nyrs)

        if selection is None:

            raise NotImplementedError()
        else:

            mrl_th = selection["Threshold"]
            idx = boot > mrl_th
            sz = np.sum(idx, axis=1)
            idx2 = boot <= mrl_th
            mrl_th = np.full(pst_options.bootstrap_sims, mrl_th)

        Lambda_mrl = sz / Nyrs
        for k in range(pst_options.bootstrap_sims):
            PEAKS_rnd = boot[k, :]

            u = PEAKS_rnd[idx[k, :]]
            params = scstats.genpareto.fit(u - mrl_th[k], method="MLE", floc=0)
            pd_k_wOut[k] = params[0]
            # NOTE: Is this the same as pd.k?
            pd_TH_wOut[k] = mrl_th[k]
            pd_sigma[k] = params[2]

            # Apply Generalized Pareto Distribution fitting here...

        # Correction of GPD shape parameter values. Limits determined by NCNC.
        pd_k_mod = pd_k_wOut.copy()
        k_min = -0.5
        k_max = 0.3
        pd_k_mod[pd_k_mod < k_min] = k_min
        pd_k_mod[pd_k_mod > k_max] = k_max

    # Compute HC (hazard curve) with GPD fitting or empirical only
    for k in range(pst_options.bootstrap_sims):

        if gpd_pass:
            opts = {
                "c": pd_k_mod[k][0],
                "loc": pd_TH_wOut[k][0],
                "scale": pd_sigma[k][0],
            }

            PEAKS_rnd = boot[k, :]
            Resp_gpd = scstats.genpareto.ppf(1 - HC_plt_x / Lambda_mrl[k], **opts)

            filt = ~np.isnan(Resp_gpd)
            AEF_gpd = HC_plt_x[filt]
            Resp_gpd = Resp_gpd[filt]

            Resp_ecdf = boot[k, idx2[k, :]]
            AEF_ecdf = HC_emp[idx2[k, :], 3]

            x_comb = np.concatenate([AEF_gpd, AEF_ecdf])
            y_comb = np.concatenate([Resp_gpd, Resp_ecdf])

        else:
            x_comb = HC_emp[:, 3]
            y_comb = boot[:, k]  # Use empirical bootstrapped values

        if pst_options.use_AEP:
            x_comb = aef2aep(x_comb)

        x_comb, idx = np.unique(x_comb, return_index=True, sorted=True)
        y_comb = y_comb[idx]

        y_comb, idx = np.unique(y_comb, return_index=True, sorted=True)
        x_comb = x_comb[idx]

        x_comb = np.flipud(x_comb)
        y_comb = np.flipud(y_comb)

        # NOTE: right=left=np.nan for MATLAB equivalent
        Resp_boot_plt[k, :] = np.interp(
            np.log(HC_plt_x),
            np.log(x_comb),
            y_comb,
            right=np.nan,
            left=np.nan,
        )

    # Apply monotonic adjustment to the bootstrapped hazard curve
    # for k in range(pst_options.bootstrap_sims):
    #    Resp_boot_plt[k, :] = Monotonic_adjustment(HC_plt_x, Resp_boot_plt[k, :])

    # Calculate the mean and percentiles of the hazard curves
    Boot_mean_plt = np.mean(Resp_boot_plt, axis=0)
    # NOTE: Set method='midpoint' for MATLAB equivalent
    Boot_plt = np.nanpercentile(
        Resp_boot_plt, pst_options.prc, axis=0, method="midpoint"
    )

    HC_plt = np.vstack([Boot_mean_plt, Boot_plt]).T

    # For this application only: delete results if WL >= 1e3 meters
    if pst_options.ind_Skew and (np.nanmax(Boot_mean_plt) >= 10**3):
        raise ValueError("Values above 10^3 found in mean hazard curve")

    for kk in range(HC_plt.shape[1]):
        HC_plt[:, kk] = Monotonic_adjustment(HC_plt_x, HC_plt[:, kk])

    HC_tbl_rsp_x = np.full((len(HC_tbl_rsp_y), HC_plt.shape[1]), np.nan)
    HC_tbl_y = np.full((len(HC_tbl_x), HC_plt.shape[1]), np.nan)

    for kk in range(HC_plt.shape[1]):

        # Delete duplicates (stable)
        args = np.unique(HC_plt[:, kk], return_index=True, sorted=True)
        dm1, ia = (np.flipud(s) for s in args)

        # dm1 = HC_plt[ia, kk]
        dm2 = np.log(HC_plt_x[ia])

        # Delete NaN / Inf
        mask = np.isnan(dm1) | np.isinf(dm1)
        dm1 = dm1[~mask]
        dm2 = dm2[~mask]

        # Interpolate
        f = interpolate.interp1d(dm1, dm2, fill_value="extrapolate")
        HC_tbl_rsp_x[:, kk] = np.exp(f(HC_tbl_rsp_y))

        f = interpolate.interp1d(dm2, dm1, fill_value="extrapolate")
        HC_tbl_y[:, kk] = f(np.log(HC_tbl_x))

    # Seems to be a dead warning check
    # "At 0.1 AEP/AEF, best estimate HC value is greater than 1.75 times the empirical HC value. Manual verification is recommended."

    HC_tbl_y[HC_tbl_y < 0] = np.nan
    HC_tbl_rsp_x[HC_tbl_rsp_x < 1e-4] = np.nan

    # Store the output parameters
    cols = ["Response", "Rank", "CCDF", "Hazard", "ARI"]
    HC_emp = pd.DataFrame(HC_emp, columns=cols)
    MRL_output = {
        "summary": summary,
        "selection": selection,
        "pd_TH_wOut": pd_TH_wOut,
        "pd_k_wOut": pd_k_wOut,
        "pd_sigma": pd_sigma,
        "pd_k_mod": pd_k_mod,
    }
    SST_output = {
        "RL": Nyrs,
        "HC_plt": HC_plt,
        "HC_tbl": HC_tbl_y,
        "HC_tbl_rsp_x": HC_tbl_rsp_x,
        "HC_emp": HC_emp,
        "HC_tbl_rsp_y": HC_tbl_rsp_y,
        "HC_plt_x": HC_plt_x,
        "HC_tbl_x": HC_tbl_x,
    }

    return SST_output, MRL_output

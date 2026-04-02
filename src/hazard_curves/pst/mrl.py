import numpy as np
import pandas as pd
import scipy.stats as scstats
from scipy.linalg import lstsq
from scipy.signal import find_peaks


def StormSim_MRL(GPD_TH_crit: int, PEAKS, Nyrs: int):
    """
        SOFTWARE NAME:
            StormSim-SST-Fit (Statistics)

        DESCRIPTION:
        This script applies the mean residual life (MRL) methodology to
        objectively select the parameters of the Generalized Pareto Distribution
        function.

        INPUT ARGUMENTS:
        - POT_samp: empirical distribution of the Peaks-Over-Threshold sample, as
            computed in StormSim_SST_Fit.m
        - Nyrs: record length in years of the input time series data set;
            specified as a positive scalar

        AUTHORS:
            Norberto C. Nadal-Caraballo, PhD (NCNC)
            Efrain Ramos-Santiago (ERS)

        HISTORY OF REVISIONS:
        20200903-ERS: revised.
        20201015-ERS: revised. Updated documentation.
        20201215-ERS: added break in for loop to avoid evaluating thresholds
            returning excesses of same magnitude.
        20210325-ERS: organized the threshold computation; the 3rd threshold not included
            in the output anymore; output organized into table arrays stored in a structure array.
        20210406-ERS: identified error when input sample size <10. When this
            happens, an empty array is returned and the Default GPD threshold computed
            in the three fit scripts.
        20210412-ERS: now selecting a minima when no inflexion point exists; avoiding the script to crash.
        20210429-ERS: now removing noise from the min WMSE through kernel
    H        regression. Also corrected the minimum WMSE criterion based on Langousis. Removed patch
            applied on 20210412.
        20210430-ERS: script will stop and return empty arrays when no minima is
            found by WRMS criterion.

        ***************  ALPHA  VERSION  **  FOR INTERNAL TESTING ONLY ************
    """
    th = np.sort(PEAKS)  # Sort the threshold parameter in ascending order
    N = len(th)  # Number of thresholds

    if N > 20:
        mrl = np.full((N - 10, 8), np.nan)  # Pre-allocate matrix for speed

        # Step 2: Estimate mean values of excesses
        for i in range(N - 10):
            mrl[i, 0] = th[i]  # Store threshold
            u = PEAKS[PEAKS > th[i]]  # Sample values above threshold
            mrl[i, 1] = np.mean(u - th[i])  # Compute mean excess
            # mrl[i, 2] = (N - i) / np.nanvar(u - th[i])  # Compute weights

            # Note: ddof=1 (degrees of freedom) for same calculation as MATLAB
            mrl[i, 2] = (N - i - 1) / np.nanvar(
                u - th[i], mean=mrl[i, 1], ddof=1
            )  # Compute weights

        w = mrl[:, 2].ravel()  # weights
        sqrt_w = np.sqrt(w)
        x = mrl[:, 0]  # threshold, u
        # Fitting  threshold u to weighted line, m*x + c
        x = np.stack([np.ones(N - 10), mrl[:, 0]]).T * sqrt_w[:, None]
        y = mrl[:, 1] * sqrt_w  # weighted mean excess, e(u)

        filt = ~np.isnan(y)
        # Step 3: Fit linear model and compute GPD parameters
        #
        for j in range(N - 20):
            u = PEAKS[PEAKS > th[j]]  # Values above threshold
            # Linear regression for (u, e(u))

            xf = x[j:, :][filt[j:], :]
            yf = y[j:][filt[j:]]
            _, norm, *_ = lstsq(xf, yf)
            # Converting from L2 norm to mean
            mrl[j, 3] = norm / len(yf)

            # Fit GPD to data above threshold
            params = scstats.genpareto.fit(u - th[j], method="MLE", floc=0)

            mrl[j, 4] = params[0]  # Shape parameter (k)
            mrl[j, 5] = params[2]  # Scale parameter (sigma)

        # Step 4: Estimate sample intensity (lambda)

        for k in range(len(mrl)):
            mrl[k, 6] = np.sum(mrl[:, 0] > mrl[k, 0])  # Number of events
        mrl[:, 7] = mrl[:, 6] / Nyrs  # Annual rate (lambda)

        # Step 5: Threshold selection using WMSE and Sample Intensity criteria

        mrl = mrl[~np.isnan(mrl[:, 3])]  # Remove rows with NaN WMSE

        # Remove noise (smoothing using kernel density estimation)
        H = scstats.gaussian_kde(mrl[:, 0])  # , bw_method='silverman')

        # NOTE: A guess
        H = float(H.cho_cov) / 7
        H = 0.01 - 4.6613e-05
        _, mrl[:, 3] = KernReg_LocalMean(mrl[:, 0], mrl[:, 3], H)

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

        _, props = find_peaks(-mrl[:, 3], plateau_size=2 * np.diff(mrl[:, 0]).min())
        TH_id = props["left_edges"]

        if len(TH_id) < 1:
            return summary, None

        mrl2 = mrl[TH_id, :]

        if GPD_TH_crit == 2:
            name = "CritWMSE"
            i = np.nanargmin(mrl[:, 0])
        else:
            name = "CritSI"
            aux = mrl2[:, 7] - 2
            aux[aux < -1] = np.nan

            if np.all(np.isnan(aux)):
                i = np.argmax(mrl2[:, 7])
            else:
                i = np.nanargmin(np.abs(aux))

        selection = {
            "Criterion": name,
            "Threshold": float(mrl2[i, 0]),
            "id_Summary": int(TH_id[i]),
            "Events": int(mrl2[i, 6]),
            "Rate": float(mrl2[i, 7]),
        }

        return summary, selection


# d-variate normal kernel
def Kh(H, t, k):
    return (H**-k) * (2 * np.pi) ** (k / 2) * np.exp(-0.5 * t)


def KernReg_LocalMean(x, y, H):
    """ """
    x = np.asarray(x)
    y = np.asarray(y).reshape(-1)

    x = x[:, np.newaxis]
    n, k = x.shape
    X = x.copy()

    NN = X.shape[0]
    Y = np.zeros(NN)

    # d-variate normal kernel
    def Kh(H, t, k):
        return (H**-k) * (2 * np.pi) ** (k / 2) * np.exp(-0.5 * t)

    # regression loop
    for i in range(NN):
        # squared distances scaled by H^2
        t = np.sum((X[i, :] - x) ** 2, axis=1) / (H**2)

        Xx = np.ones((n, 1))
        Wx = np.diag(Kh(H, t, k))

        # (X'WX)^{-1} X'W y
        Y[i] = np.linalg.solve(Xx.T @ Wx @ Xx, Xx.T @ Wx @ y)

    return X, Y

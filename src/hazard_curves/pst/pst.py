import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..common import bool_check, dict_to_dataclass
from .core import PSTOptions, ResponseData
from .fit import StormSim_PST_Fit

# ---------------- Data classes ----------------


def error_handling(response_data: ResponseData, pst_options: PSTOptions):

    checks = [
        (pst_options, "use_AEP", [0, 1], "0 (AEF) or 1 (AEP)"),
        (pst_options, "apply_GPD_to_SS", [0, 1], "0 (empirical) or 1 (GPD fit)"),
        (pst_options, "GPD_TH_crit", [1, 2], "1 (lambda) or 2 (WMSE)"),
    ]

    bool_check(checks)

    # DataType-specific checks
    if response_data.DataType == "POT":
        pst_options.tLag = None
        response_data.lambda_ = None

        if response_data.Nyrs is None or response_data.Nyrs <= 0:
            raise ValueError("When DataType='POT': Nyrs must be positive.")

        if response_data.SLC is None:
            response_data.SLC = 0

        if pst_options.ind_Skew not in [0, 1]:
            raise ValueError("ind_Skew must be 0 or 1")

        if pst_options.ind_Skew == 1 and response_data.gprMdl is None:
            raise ValueError("When ind_Skew=1: gprMdl cannot be empty")

    elif response_data.DataType == "Timeseries":
        if response_data.data.shape[1] >= 3:
            response_data.data[:, 2] = 0

        response_data.Nyrs = None
        response_data.SLC = 0
        response_data.gprMdl = None
        pst_options.ind_Skew = 0

        if pst_options.tLag is None or pst_options.tLag <= 0:
            raise ValueError("For Timeseries: tLag must be positive")

        if response_data.lambda_ is None or response_data.lambda_ <= 0:
            raise ValueError("For Timeseries: lambda must be positive")

    else:
        raise ValueError("DataType must be 'POT' or 'Timeseries'")

    # prc
    if pst_options.prc is None:
        pst_options.prc = [2.28, 15.87, 84.13, 97.72]
    else:
        if len(pst_options.prc) > 4 or any(p < 0 for p in pst_options.prc):
            raise ValueError("prc must contain 1–4 values")
        pst_options.prc = sorted(pst_options.prc)

    # response_data
    if response_data.data is None or response_data.data.shape[1] < 2:
        raise ValueError("response_data.data must be M×2 or M×3 array")

    return response_data, pst_options


# ---------------- Main PST function ----------------
def StormSim_PST(
    response_data_dict: dict,
    pst_options_dict: dict,
    # plot_options_dict: dict,
    test_ecdf_data: None | dict = None,
):
    """ """
    # Convert dicts to dataclasses
    response_data = dict_to_dataclass(ResponseData, response_data_dict)
    pst_options = dict_to_dataclass(PSTOptions, pst_options_dict)
    # plot_options = dict_to_dataclass(PlotOptions, plot_options_dict)

    # Step 1: Status printing
    response_data, pst_options = error_handling(response_data, pst_options)

    # NOTE:: Needed anymore?
    col_idx = 4 if pst_options.ind_Skew == 1 else 3

    # Create output dict
    SST_output = {
        "staID": "",
        "RL": None,
        "POT": None,
        "MRL_output": None,
        "HC_plt": None,
        "HC_tbl": None,
        "HC_tbl_rsp_x": None,
        "HC_emp": None,
        "Warning": "",
        "ME": None,
    }

    procData = response_data.data.copy()

    if response_data.DataType == "Timeseries":

        if response_data.flag_value is not None:
            mask = np.ones(len(procData), dtype=bool)
            for fv in response_data.flag_value:
                mask &= procData[:, 1] != fv
            procData = procData[mask]

        good = ~np.isnan(procData[:, 1]) & ~np.isinf(procData[:, 1])
        procData = procData[good]

        # compute Nyrs
        dates = [datetime.datetime.fromordinal(int(d)) for d in procData[:, 0]]
        unique_days = len({(d.year, d.month, d.day) for d in dates})
        response_data.Nyrs = unique_days / 365.25

        fail_flag = procData.size == 0

    else:  # POT

        if response_data.flag_value is not None:
            mask = np.ones(len(procData), dtype=bool)
            for fv in response_data.flag_value:
                mask &= ~(procData[:, 1:] == fv).any(axis=1)
            procData = procData[mask]

        d = procData[:, 1:]
        good = ((~np.isnan(d) & ~np.isinf(d)) & (d > 0)).any(axis=1)
        procData = procData[good]

        fail_flag = len(np.unique(procData[:, 1])) <= 3

    if fail_flag:
        raise ValueError("Data cleaning removed all values. Aborting PST.")

    # Step 4: Run StormSim POT or use existing POT

    if response_data.DataType == "Timeseries":
        raise NotImplementedError("Timeseries SST")
    else:
        POT_samp = procData

    # add tiny noise for duplicates - LAA 2023/12/07
    _, unique_idx = np.unique(POT_samp[:, 1], return_index=True)
    dup = np.setdiff1d(np.arange(len(POT_samp)), unique_idx)

    POT_samp[dup, 1] += 1e-6

    # Perform PST fit
    SST_output, MRL_output = StormSim_PST_Fit(  # Placeholder
        POT_samp[:, 1],
        POT_samp[:, 2] if POT_samp.shape[1] > 2 else None,
        response_data.SLC,
        response_data.Nyrs,
        response_data.gprMdl,
        pst_options,
        test_ecdf_data=test_ecdf_data,
    )

    # Step 5: Save results

    dpath = Path()

    fname = "selection.json"
    with open(dpath / fname, "w") as fh:
        json.dump(MRL_output["selection"], fh, indent=2)

    fname = "summary.csv"
    MRL_output["summary"].to_csv(dpath / fname, index=False)

    a = MRL_output["pd_k_wOut"]
    b = MRL_output["pd_k_mod"]
    data = np.hstack([a, b])
    cols = ["pd_k_wOut", "pd_k_mod"]

    fname = "pareto.csv"
    pd.DataFrame(data, columns=cols).to_csv(dpath / fname, index=False)

    a = SST_output["HC_plt_x"][:, np.newaxis]
    b = SST_output["HC_plt"]
    data = np.hstack([a, b])
    cols = [f"{int(x)}" for x in pst_options.prc]
    cols.insert(0, "Mean")
    if pst_options.use_AEP:
        cols.insert(0, "AEP")
    else:
        cols.insert(0, "AEF")

    fname = "HC_plt.csv"
    pd.DataFrame(data, columns=cols).to_csv(dpath / fname, index=False)

    fname = "HC_emp.csv"
    SST_output["HC_emp"].to_csv(dpath / fname, index=False)

    return SST_output, MRL_output

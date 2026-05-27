import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..common import bool_check, dict_to_dataclass
from .core import Options, ResponseData
from .fit import StormSim_PST_Fit


def _error_handling(response_data: ResponseData, opts: Options):

    checks = [
        (opts, "use_AEP", [0, 1], "0 (AEF) or 1 (AEP)"),
        (opts, "apply_GPD_to_SS", [0, 1], "0 (empirical) or 1 (GPD fit)"),
        (opts, "GPD_TH_crit", [1, 2], "1 (lambda) or 2 (WMSE)"),
    ]

    bool_check(checks)

    if response_data.DataType == "POT":
        opts.tLag = None
        response_data.lambda_ = None

        if response_data.Nyrs is None or response_data.Nyrs <= 0:
            raise ValueError("When DataType='POT': Nyrs must be positive.")

        if response_data.SLC is None:
            response_data.SLC = 0

        if opts.ind_Skew not in [0, 1]:
            raise ValueError("ind_Skew must be 0 or 1")

        if opts.ind_Skew == 1 and response_data.gprMdl is None:
            raise ValueError("When ind_Skew=1: gprMdl cannot be empty")

    elif response_data.DataType == "Timeseries":
        if response_data.data.shape[1] >= 3:
            response_data.data[:, 2] = 0

        response_data.Nyrs = None
        response_data.SLC = 0
        response_data.gprMdl = None
        opts.ind_Skew = 0

        if opts.tLag is None or opts.tLag <= 0:
            raise ValueError("For Timeseries: tLag must be positive")

        if response_data.lambda_ is None or response_data.lambda_ <= 0:
            raise ValueError("For Timeseries: lambda must be positive")

    else:
        raise ValueError("DataType must be 'POT' or 'Timeseries'")

    if opts.prc is None:
        opts.prc = [2.28, 15.87, 84.13, 97.72]
    else:
        if len(opts.prc) > 4 or any(p < 0 for p in opts.prc):
            raise ValueError("prc must contain 1–4 values")
        opts.prc = sorted(opts.prc)

    if response_data.data is None or response_data.data.shape[1] < 2:
        raise ValueError("response_data.data must be M×2 or M×3 array")

    return response_data, opts


def compute(
    response_data: ResponseData | dict,
    opts: Options | dict,
    test_ecdf_data: None | dict = None,
) -> tuple[dict, dict]:
    """
    Run PST/POT hazard curve analysis.

    Parameters
    ----------
    response_data : ResponseData or dict
        Input data. Use ResponseData(data=arr, DataType="POT", Nyrs=...).
        ``data`` must be an (N, 2) or (N, 3) array; column 1 is the response.
    opts : Options or dict
        Algorithm options. ``opts.output_path`` controls where CSV results are
        written (default: ``"data/outputs/pst"``).
    test_ecdf_data : dict, optional
        Inject fixed random draws for reproducible testing.

    Returns
    -------
    sst_output : dict
        Keys: HC_plt, HC_plt_x, HC_emp, HC_tbl, HC_tbl_rsp_x, ...
    mrl_output : dict
        Keys: summary (DataFrame), selection (dict), pd_k_wOut, pd_k_mod
    """
    if isinstance(response_data, dict):
        response_data = dict_to_dataclass(ResponseData, response_data)
    if isinstance(opts, dict):
        opts = dict_to_dataclass(Options, opts)

    response_data, opts = _error_handling(response_data, opts)

    SST_output = {
        "staID": "", "RL": None, "POT": None, "MRL_output": None,
        "HC_plt": None, "HC_tbl": None, "HC_tbl_rsp_x": None,
        "HC_emp": None, "Warning": "", "ME": None,
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

    if response_data.DataType == "Timeseries":
        raise NotImplementedError("Timeseries SST")

    POT_samp = procData

    # add tiny noise to break exact duplicates
    _, unique_idx = np.unique(POT_samp[:, 1], return_index=True)
    dup = np.setdiff1d(np.arange(len(POT_samp)), unique_idx)
    POT_samp[dup, 1] += 1e-6

    SST_output, MRL_output = StormSim_PST_Fit(
        POT_samp[:, 1],
        POT_samp[:, 2] if POT_samp.shape[1] > 2 else None,
        response_data.SLC,
        response_data.Nyrs,
        response_data.gprMdl,
        opts,
        test_ecdf_data=test_ecdf_data,
    )

    # Write outputs
    dpath = Path(opts.output_path)
    dpath.mkdir(parents=True, exist_ok=True)

    with open(dpath / "selection.json", "w") as fh:
        json.dump(MRL_output["selection"], fh, indent=2)

    MRL_output["summary"].to_csv(dpath / "summary.csv", index=False)

    pd.DataFrame(
        np.hstack([MRL_output["pd_k_wOut"], MRL_output["pd_k_mod"]]),
        columns=["pd_k_wOut", "pd_k_mod"],
    ).to_csv(dpath / "pareto.csv", index=False)

    hc_cols = [f"{int(x)}" for x in opts.prc]
    hc_cols.insert(0, "Mean")
    hc_cols.insert(0, "AEP" if opts.use_AEP else "AEF")
    pd.DataFrame(
        np.hstack([SST_output["HC_plt_x"][:, np.newaxis], SST_output["HC_plt"]]),
        columns=hc_cols,
    ).to_csv(dpath / "HC_plt.csv", index=False)

    SST_output["HC_emp"].to_csv(dpath / "HC_emp.csv", index=False)

    return SST_output, MRL_output


def StormSim_PST(
    response_data_dict: dict,
    pst_options_dict: dict,
    output_path: str | Path = "data/outputs/pst",
    test_ecdf_data: None | dict = None,
) -> tuple[dict, dict]:
    """Backward-compatible wrapper. Prefer ``pst.compute``."""
    if isinstance(pst_options_dict, dict):
        pst_options_dict = {**pst_options_dict, "output_path": output_path}
    return compute(response_data_dict, pst_options_dict, test_ecdf_data=test_ecdf_data)

import datetime

import numpy as np

from ..common import bool_check
from .cleaner import clean_pot_data
from .core import PSTOptions, ResponseData
from .fit import fit_hazard_curve
from .utils import add_noise_to_duplicates


def validate_inputs(response_data: ResponseData, pst_options: PSTOptions):
    """Validate and normalise ResponseData and PSTOptions before fitting."""

    checks = [
        (pst_options, "use_aep", [0, 1], "0 (AEF) or 1 (AEP)"),
        (pst_options, "apply_gpd", [0, 1], "0 (empirical) or 1 (GPD fit)"),
        (pst_options, "gpd_criterion", [1, 2], "1 (lambda) or 2 (WMSE)"),
    ]

    bool_check(checks)

    if response_data.data_type == "POT":
        pst_options.t_lag = None
        response_data.annual_rate = None

        if response_data.n_years is None or response_data.n_years <= 0:
            raise ValueError("When data_type='POT': n_years must be positive.")

        if response_data.slc is None:
            response_data.slc = 0

        if pst_options.apply_skew not in [0, 1]:
            raise ValueError("apply_skew must be 0 or 1")

        if pst_options.apply_skew == 1 and response_data.gpr_mdl is None:
            raise ValueError("When apply_skew=1: gpr_mdl cannot be empty")

    elif response_data.data_type == "Timeseries":
        if response_data.data.shape[1] >= 3:
            response_data.data[:, 2] = 0

        response_data.n_years = None
        response_data.slc = 0
        response_data.gpr_mdl = None
        pst_options.apply_skew = 0

        if pst_options.t_lag is None or pst_options.t_lag <= 0:
            raise ValueError("For Timeseries: t_lag must be positive")

        if response_data.annual_rate is None or response_data.annual_rate <= 0:
            raise ValueError("For Timeseries: annual_rate must be positive")

    else:
        raise ValueError("data_type must be 'POT' or 'Timeseries'")

    if pst_options.percentiles is None:
        pst_options.percentiles = [2.28, 15.87, 84.13, 97.72]
    else:
        if len(pst_options.percentiles) > 4 or any(
            p < 0 for p in pst_options.percentiles
        ):
            raise ValueError("percentiles must contain 1–4 values")
        pst_options.percentiles = sorted(pst_options.percentiles)

    if response_data.data is None or response_data.data.shape[1] < 2:
        raise ValueError("response_data.data must be M×2 or M×3 array")

    return response_data, pst_options


def compute(
    response_data: ResponseData,
    pst_options: PSTOptions,
    test_ecdf_data: None | dict = None,
):
    """
    Pure entry point for PST hazard curve fitting — no file I/O.

    Validates inputs, cleans the POT sample (flag removal, NaN/Inf/non-positive
    filtering, duplicate jitter), then delegates to fit_hazard_curve.
    Use run_pst for the full pipeline including I/O.
    """
    response_data, pst_options = validate_inputs(response_data, pst_options)

    data = response_data.data.copy()

    if response_data.data_type == "Timeseries":
        if response_data.flag_value is not None:
            mask = np.ones(len(data), dtype=bool)
            for flag_val in response_data.flag_value:
                mask &= data[:, 1] != flag_val
            data = data[mask]

        valid = ~np.isnan(data[:, 1]) & ~np.isinf(data[:, 1])
        data = data[valid]

        dates = [datetime.datetime.fromordinal(int(d)) for d in data[:, 0]]
        unique_days = len({(d.year, d.month, d.day) for d in dates})
        response_data.n_years = unique_days / 365.25

        data_invalid = data.size == 0

    else:
        data = clean_pot_data(data, flag_value=response_data.flag_value)
        data_invalid = False

    if data_invalid:
        raise ValueError("Data cleaning removed all values. Aborting PST.")

    if response_data.data_type == "Timeseries":
        raise NotImplementedError("Timeseries SST")

    pot_sample = add_noise_to_duplicates(data.copy(), col_idx=1)

    hc_output, mrl_output = fit_hazard_curve(
        pot_sample[:, 1],
        pot_sample[:, 2] if pot_sample.shape[1] > 2 else None,
        response_data.slc,
        response_data.n_years,
        response_data.gpr_mdl,
        pst_options,
        test_ecdf_data=test_ecdf_data,
    )

    return hc_output, mrl_output

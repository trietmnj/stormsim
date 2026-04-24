import numpy as np


def clean_pot_data(data, flag_value=None):
    """
    Cleans POT data by removing flagged values, NaNs, Infs, and non-positive values.
    """
    data = data.copy()

    if flag_value is not None:
        mask = np.ones(len(data), dtype=bool)
        for flag_val in flag_value:
            mask &= ~(data[:, 1:] == flag_val).any(axis=1)
        data = data[mask]

    response_cols = data[:, 1:]
    valid = (
        (~np.isnan(response_cols) & ~np.isinf(response_cols)) & (response_cols > 0)
    ).any(axis=1)
    data = data[valid]

    if len(np.unique(data[:, 1])) <= 3:
        raise ValueError("Data cleaning removed all values. Aborting PST.")

    return data

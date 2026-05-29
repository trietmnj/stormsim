import numpy as np


def add_noise_to_duplicates(data, col_idx=1, noise=1e-6):
    """Adds tiny noise to duplicates in the specified column."""
    _, unique_idx = np.unique(data[:, col_idx], return_index=True)
    dup = np.setdiff1d(np.arange(len(data)), unique_idx)
    data[dup, col_idx] += noise
    return data

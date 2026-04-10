from pathlib import Path

import numpy as np
import scipy.io as sio

from hazard_curves.pst.fit import ecdf_boot

# Get path to the data directory relative to this file
data_dpath = Path(__file__).parent / "data"

# Loading in test data
empHC = sio.loadmat(data_dpath / "ecdf_emphc.mat")["empHC"].flatten()
boot_trg = sio.loadmat(data_dpath / "ecdf_boot.mat")["boot"]
test_data = {
    "random": sio.loadmat(data_dpath / "ecdf_random.mat")["rand_vals"],
    "indices": sio.loadmat(data_dpath / "ecdf_indices.mat")["idxs"] - 1,
}

n_sims, _ = test_data["random"].shape


boot = ecdf_boot(empHC, n_sims, test_data=test_data)
error = np.max(np.abs(boot - boot_trg))

print(f"Max Error: {error}")

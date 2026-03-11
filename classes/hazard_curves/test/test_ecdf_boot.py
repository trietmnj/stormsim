from pathlib import Path

import numpy as np
import scipy.io as sio
import tables

from hazard_curves.pst.fit import ecdf_boot

root_dpath = "/Users/rdchlmyl/projects/chart/matlab-conversion/hazard-curves/tests"
root_dpath = Path(root_dpath)

# Note: Not sure why tables is not working
# file = tables.open_file(root_dpath / "data/ecdf_random.mat")
# random_val = file.root.rand_val[:]

# Loading in test data
empHC = sio.loadmat("./data/ecdf_emphc.mat")["empHC"].flatten()
boot_trg = sio.loadmat("./data/ecdf_boot.mat")["boot"]
test_data = {
    "random": sio.loadmat("./data/ecdf_random.mat")["rand_vals"],
    "indices": sio.loadmat("./data/ecdf_indices.mat")["idxs"] - 1,
}

n_sims, _ = test_data["random"].shape


boot = ecdf_boot(empHC, n_sims, test_data=test_data)
error = np.max(np.abs(boot - boot_trg))

print(f"Max Error: {error}")

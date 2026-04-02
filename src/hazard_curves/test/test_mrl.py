from pathlib import Path

import numpy as np
import scipy.io as sio
import tables

from hazard_curves.pst.mrl import StormSim_MRL

root_dpath = "/Users/rdchlmyl/projects/chart/matlab-conversion/hazard-curves/tests"
root_dpath = Path(root_dpath)

# Note: Not sure why tables is not working
# file = tables.open_file(root_dpath / "data/ecdf_random.mat")
# random_val = file.root.rand_val[:]


# Loading in test data
empHC = sio.loadmat("./data/ecdf_emphc.mat")["empHC"].flatten()
mrl_trg = sio.loadmat("./data/mrl_step4.mat")["mrl"]

Nyrs = 75
GPD_TH_crit = 2


# print(empHC)

mrl = StormSim_MRL(GPD_TH_crit, empHC, Nyrs)

i0 = 3
i1 = 5

sl = slice(i0, i1)


sl2 = slice(0, 5)
print("==================")

print(mrl[sl2, sl])

print("==================")
print(mrl_trg[sl2, sl])

print("==================")

error = (mrl - mrl_trg) / mrl_trg
print(error[sl2, sl])

print("==================")
print(f"Shape: {error.shape}")
print(f"Max: {np.nanmax(error[:,i0:i1], axis=0)}")
print(f"Mean: {np.nanmean(error[:,i0:i1], axis=0)}")
# print(f"Median: {np.nanmedian(error[:,:i_max], axis=0)}")

print(np.nanpercentile(error[:, i0:i1], [90, 97, 99], axis=0).T)


import matplotlib.pyplot as plt

plt.plot(mrl[:, 3], "-x")
plt.plot(mrl_trg[:, 3])
plt.xlim(15, 20)
plt.ylim(0.18, 0.24)
plt.show()

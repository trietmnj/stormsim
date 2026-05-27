from pathlib import Path

import numpy as np
import scipy.io as sio

from stormsim.hazard_curves.pst.mrl import StormSim_MRL

data_dpath = Path(__file__).parent / "data"

empHC = sio.loadmat(data_dpath / "ecdf_emphc.mat")["empHC"].flatten()
mrl_trg = sio.loadmat(data_dpath / "mrl_step4.mat")["mrl"]

Nyrs = 75
GPD_TH_crit = 2

mrl_df, _ = StormSim_MRL(GPD_TH_crit, empHC, Nyrs)
mrl = mrl_df.values

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

print(np.nanpercentile(error[:, i0:i1], [90, 97, 99], axis=0).T)

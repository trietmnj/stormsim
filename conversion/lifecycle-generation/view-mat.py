from pathlib import Path

from scipy.io import loadmat
import numpy as np

DATA_PATH = "/Users/rdcrltmn/Downloads/North_Atlantic_Studies_Metadata/Savepoints/NACCS_DSW.mat"
OUT_CSV  = Path("DSW_ITCS_TC.csv")


mat = loadmat(DATA_PATH, squeeze_me=True, struct_as_record=False)
print(mat.keys())

m = mat["DSW_ITCS"]
print(type(m))
print(m)
print(m.shape)

m_flat = np.ravel(m)
s0 = m_flat[0]          # first struct
print(type(s0))
print(s0._fieldnames)

tc = s0.TC
print(type(tc), getattr(tc, "shape", None))
print(tc)
# for tab in m:
#     print(tab)

m = mat["DSW_ITCS"]          # ndarray of mat_struct, shape (18977,)
m_flat = np.ravel(m)

rows = []
for i, s in enumerate(m_flat):
    tc = np.asarray(s.TC).ravel()

    # Optional safety check: all rows must be length 1050
    if tc.shape != (1050,):
        raise ValueError(f"Row {i} has TC shape {tc.shape}, expected (1050,)")

    rows.append(tc)

# Stack into a 2D array: (18977, 1050)
arr = np.vstack(rows)
print(arr.shape)  # should print (18977, 1050)

# Save as CSV
np.savetxt(OUT_CSV, arr, delimiter=",", fmt="%.8e")
print(f"Wrote {OUT_CSV}")

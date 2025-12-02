import numpy as np
import h5py
from scipy.io import loadmat
from pathlib import Path
import pandas as pd

BASE_INPUT_DIR = Path("../data/raw/conversion-lifecycle-generation/CHS_Files")
INPUT_MAT_FILES = [
    "CHS-NA_nodeID_v4.mat",
    "CHS_Atl_CRLs_v1.6.mat",
    "SRR_TC_All_600km.mat",
    "SRR_TC_HI_600km.mat",
    "SRR_TC_LI_600km.mat",
    "SRR_TC_MI_600km.mat",
    "CHS-NA_ITCS_Param.mat",
    "CHS-NA_ITCS_DSW_600km.mat",
]
OUTPUT_PATH = Path("../data/intermediate/conversion-lifecycle-generation/stormprob.csv")
EARTH_RADIUS_KM = 6371.0


def extract_mat_struct(filename: str) -> dict[str, pd.DataFrame]:
    """
    Load a MATLAB .mat file and return a dict mapping variable names
    to pandas DataFrames with generic 'Col0', 'Col1', ... column names.

    Supports both classic MAT files and v7.3 (HDF5) via h5py fallback.
    """
    try:
        print(filename)
        raw = loadmat(filename, struct_as_record=False, squeeze_me=True)
        var_list = [
            key
            for key in raw.keys()
            if not (key.startswith("__") and key.endswith("__"))
        ]

        mat_struct: dict[str, pd.DataFrame] = {}

        for vv in var_list:
            val = raw[vv]

            # Convert to ndarray and standardize shape: 2D (n, m)
            arr = np.asarray(val)
            if arr.ndim == 0:
                # scalar
                arr = arr.reshape(1, 1)
            elif arr.ndim == 1:
                # vector
                arr = arr.reshape(-1, 1)
            elif arr.ndim > 2:
                # collapse higher dims to 2D
                arr = arr.reshape(arr.shape[0], -1)

            n_cols = arr.shape[1]
            columns = [f"Col{i}" for i in range(n_cols)]
            mat_struct[vv] = pd.DataFrame(arr, columns=columns)

        return mat_struct

    except NotImplementedError:
        # Likely a v7.3 MAT file (HDF5)
        result: dict[str, pd.DataFrame] = {}
        with h5py.File(filename, "r") as f:
            for ds in list(f.keys()):
                arr = f[ds][()]
                arr = np.asarray(arr)
                if arr.ndim == 0:
                    arr = arr.reshape(1, 1)
                elif arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                elif arr.ndim > 2:
                    arr = arr.reshape(arr.shape[0], -1)

                n_cols = arr.shape[1]
                columns = [f"Col{i}" for i in range(n_cols)]
                result[ds] = pd.DataFrame(arr, columns=columns)

        return result


def find_nearest_latlon(
    target_lat: float | np.ndarray,
    target_lon: float | np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    max_radius_km: float | None = None,
):
    """
    Find the nearest (lat, lon) among 'latitudes', 'longitudes'
    to the target point using the haversine formula.

    Returns
    -------
    nearest_lat : float | None
    nearest_lon : float | None
    within_radius : np.ndarray | None
        Boolean mask of points within 'max_radius_km', or None if no radius given.
    distance_km : np.ndarray
        Distance from target to each point (km).
    min_index : int | None
        Index of the nearest point in the original arrays, or None if no point
        lies within max_radius_km (when specified).
    """
    # Ensure scalar target (if you passed 1-element arrays)
    target_lat = float(np.asarray(target_lat).ravel()[0])
    target_lon = float(np.asarray(target_lon).ravel()[0])

    # Convert degrees to radians
    target_lat_rad = np.deg2rad(target_lat)
    target_lon_rad = np.deg2rad(target_lon)
    lat_rad = np.deg2rad(latitudes)
    lon_rad = np.deg2rad(longitudes)

    # Differences
    dlat = lat_rad - target_lat_rad
    dlon = lon_rad - target_lon_rad

    # Haversine formula
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(target_lat_rad) * np.cos(lat_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distance_km = EARTH_RADIUS_KM * c

    if max_radius_km is None:
        min_index = int(np.argmin(distance_km))
        nearest_lat = float(latitudes[min_index])
        nearest_lon = float(longitudes[min_index])
        within_radius = None
    else:
        within_radius = distance_km <= max_radius_km
        if not np.any(within_radius):
            return None, None, within_radius, distance_km, None

        filtered_distances = distance_km[within_radius]
        min_indx_local = int(np.argmin(filtered_distances))

        filtered_lat = latitudes[within_radius]
        filtered_lon = longitudes[within_radius]

        nearest_lat = float(filtered_lat[min_indx_local])
        nearest_lon = float(filtered_lon[min_indx_local])

        # Map back to original indices
        original_indices = np.where(within_radius)[0]
        min_index = int(original_indices[min_indx_local])

    return nearest_lat, nearest_lon, within_radius, distance_km, min_index


def main():
    ## LOAD MAT FILES FROM CHS
    mat_files = INPUT_MAT_FILES
    base_dir = BASE_INPUT_DIR
    files_to_load = [base_dir / f for f in mat_files]

    # Define CHS-Region
    chs_region = "CHS-NA"

    # Define Radius Of Influence For Storm Tracks (Intensity Bucket Population)
    trk_dist_km = 200.0

    ## DEFINE CHS-NA EXCEPTION (storms rate scaling factor)
    if "CHS-NA" in chs_region:
        srr_to_stmperyr = 400.0
    else:
        srr_to_stmperyr = 600.0

    ## BUILD DICTIONARIES
    grid = extract_mat_struct(files_to_load[0])  # Grid File
    CRL = extract_mat_struct(files_to_load[1])  # Coastal Reference Locations
    SRR_All = extract_mat_struct(files_to_load[2])  # SRR Total
    SRR_HI = extract_mat_struct(files_to_load[3])  # SRR High Intensity
    SRR_LI = extract_mat_struct(files_to_load[4])  # SRR Low Intensity
    SRR_MI = extract_mat_struct(files_to_load[5])  # SRR Mid Intensity
    MasterTrack = extract_mat_struct(files_to_load[6])  # Master Track Table
    DSW = extract_mat_struct(files_to_load[7])  # Prob Mass

    ## FIND NEAREST CRL TO FIND ASSOCIATED SRR
    sp_id = 133  # FROM ADCIRC H5 FILE

    # Build arrays from CRL dictionary
    crl_lat = CRL["CRL"]["Col1"].values
    crl_lon = CRL["CRL"]["Col0"].values

    # Get SP Lat, Lon
    if "nodeID" in grid:
        sp_mask = grid["nodeID"]["Col0"] == sp_id
        sp_lat = grid["nodeID"].loc[sp_mask, "Col2"].values
        sp_lon = grid["nodeID"].loc[sp_mask, "Col3"].values
    else:
        sp_mask = grid["staID"]["Col0"] == sp_id
        sp_lat = grid["staID"].loc[sp_mask, "Col1"].values
        sp_lon = grid["staID"].loc[sp_mask, "Col2"].values

    if sp_lat.size == 0:
        raise ValueError(f"sp_id {sp_id} not found in grid file")

    # Find distance between CRLs and SP location
    nearest_lat, nearest_lon, _, distance_km, min_indx = find_nearest_latlon(
        sp_lat, sp_lon, crl_lat, crl_lon, max_radius_km=None
    )

    # Pull SRRs associated to SP and convert to [storms/year]
    # NOTE: convert to np.array BEFORE multiplying to avoid list repetition
    srr_vals = np.array(
        [
            SRR_LI["SRR"]["Col0"].iloc[min_indx],
            SRR_MI["SRR"]["Col0"].iloc[min_indx],
            SRR_HI["SRR"]["Col0"].iloc[min_indx],
            SRR_All["SRR"]["Col0"].iloc[min_indx],
        ],
        dtype=float,
    )
    SSR_SP = srr_vals * srr_to_stmperyr

    print("SSR_SP [LI, MI, HI, All] (storms/year):", SSR_SP)

    ## LOAD PROB MASS
    TC_Freq = DSW["DSW_ITCS"]["Col0"].values
    TotalFreq = float(TC_Freq.sum())
    print("Total TC frequency (sum of DSW):", TotalFreq)

    ## FIND INFLUENTIAL STORMS AND POPULATE INTENSITY BUCKETS
    # Grab Lat/Lon from Master Track Table
    track_lat = MasterTrack["Param_ITCS"]["Col3"].values
    track_lon = MasterTrack["Param_ITCS"]["Col4"].values

    # Find distance between track reference location & SP location
    _, _, _, track_dist_km, _ = find_nearest_latlon(
        sp_lat, sp_lon, track_lat, track_lon, max_radius_km=None
    )

    # Create mask for storms within trk_dist_km radius
    dist_mask = track_dist_km <= trk_dist_km

    # Only keep events that fall within the radius from SP
    reduced_set = MasterTrack["Param_ITCS"].loc[dist_mask].copy()

    if "NACCS" in chs_region:
        # NACCS thresholds
        LI_pop = reduced_set.loc[reduced_set["Col6"].values < 48, "Col0"].values
        MI_pop = np.array([])  # No MI defined
        HI_pop = reduced_set.loc[reduced_set["Col6"].values >= 48, "Col0"].values
    else:
        # CHS thresholds
        LI_pop = reduced_set.loc[reduced_set["Col6"].values < 28, "Col0"].values
        MI_pop = reduced_set.loc[
            (reduced_set["Col6"].values >= 28) & (reduced_set["Col6"].values < 48),
            "Col0",
        ].values
        HI_pop = reduced_set.loc[reduced_set["Col6"].values >= 48, "Col0"].values

    print(f"Low-intensity storms (ID count): {LI_pop.size}")
    print(f"Mid-intensity storms (ID count): {MI_pop.size}")
    print(f"High-intensity storms (ID count): {HI_pop.size}")

    print("Tada!")

    ## HAILIE ADDED: BUILD STORM ID + PROBABILITIES TABLE
    SID = MasterTrack["Param_ITCS"].copy()
    SID.columns = [
        "storm_ID",
        "Region_ID",
        "Track_ID",
        "Track_lat",
        "Track_lon",
        "Heading",
        "dP",
        "Rmax",
        "Translational_speed",
    ]

    prob_dsw = DSW["DSW_ITCS"].copy()
    prob_dsw.columns = ["DSW"]

    SIDprob = pd.concat([SID, prob_dsw], axis=1)

    out_path = OUTPUT_PATH
    SIDprob.to_csv(out_path, index=False)
    print(f"Wrote storm ID + probability table to {out_path.resolve()}")


if __name__ == "__main__":
    main()

import numpy as np
import h5py
from scipy.io import loadmat
from os import path
import pandas as pd


def extract_mat_struct(filename):
    try:
        raw = loadmat(filename, struct_as_record=False, squeeze_me=True)
        varList = [
            key
            for key in list(raw.keys())
            if not (key.startswith("__") and key.endswith("__"))
        ]
        mat_struct = {}
        for vv in varList:
            # Define N Columns
            if raw[vv].ndim == 1:
                columns = ["Col0"]
            else:
                columns = [f"Col{i}" for i in range(raw[vv].shape[1])]
            mat_struct[vv] = pd.DataFrame(raw[vv], columns=columns)
        return mat_struct
    except NotImplementedError:
        result = {}
        with h5py.File(filename, "r") as f:
            for ds in list(f.keys()):
                result[ds] = f[ds][()].flatten()
        return result

    import numpy as np


def find_nearest_latlon(
    target_lat, target_lon, latitudes, longitudes, max_radius_km=None
):
    # Convert degrees to radians
    target_lat = np.deg2rad(target_lat)
    target_lon = np.deg2rad(target_lon)
    latitudes = np.deg2rad(latitudes)
    longitudes = np.deg2rad(longitudes)

    # Compute differences
    dlat = latitudes - target_lat
    dlon = longitudes - target_lon

    # Haversine formula
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(target_lat) * np.cos(latitudes) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance_km = 6371 * c  # Earth's radius in km

    # Find nearest point
    if max_radius_km is None:
        min_indx = np.argmin(distance_km)
        nearest_lat = np.rad2deg(latitudes[min_indx])
        nearest_lon = np.rad2deg(longitudes[min_indx])
        within_radius = None
    else:
        within_radius = distance_km <= max_radius_km
        if not np.any(within_radius):
            return None, None, within_radius, distance_km, None
        filtered_distances = distance_km[within_radius]
        min_indx_local = np.argmin(filtered_distances)
        filtered_latitudes = latitudes[within_radius]
        filtered_longitudes = longitudes[within_radius]
        nearest_lat = np.rad2deg(filtered_latitudes[min_indx_local])
        nearest_lon = np.rad2deg(filtered_longitudes[min_indx_local])
        min_indx = np.where(within_radius)[0][min_indx_local]

    return nearest_lat, nearest_lon, within_radius, distance_km, min_indx


## LOAD MAT FILES FROM CHS
Files_to_load = [
    "CHS-NA_nodeID_v4.mat",
    "CHS_Atl_CRLs_v1.6.mat",
    "SRR_TC_All_600km.mat",
    "SRR_TC_HI_600km.mat",
    "SRR_TC_LI_600km.mat",
    "SRR_TC_MI_600km.mat",
    "CHS-NA_ITCS_Param.mat",
    "CHS-NA_ITCS_DSW_600km.mat",
]
Files_to_load = [
    path.join(r"C:\Users\RDCRLHPS\Documents\Chart-Python\CHS_Files", f)
    for f in Files_to_load
]
# Define CHS-Region
chs_region = "CHS-NA"
# Define Radius Of Influence For Storm Tracks (Intensity Bucket Population)
trk_dist = 200

## DEFINE CHS-NA EXCEPTION
if "CHS-NA" in chs_region:
    srr_to_stmperyr = np.array(400)
else:
    srr_to_stmperyr = np.array(600)


## BUILD DICTIONARIES
grid = extract_mat_struct(Files_to_load[0])  # Grid File
CRL = extract_mat_struct(Files_to_load[1])  # Coastal Reference Locations
SRR_All = extract_mat_struct(Files_to_load[2])  # SRR Total
SRR_HI = extract_mat_struct(Files_to_load[3])  # SRR High Intensity
SRR_LI = extract_mat_struct(Files_to_load[4])  # SRR Low Intensity
SRR_MI = extract_mat_struct(Files_to_load[5])  # SRR Mid Intensity
MasterTrack = extract_mat_struct(Files_to_load[6])  # MAster Track Table
DSW = extract_mat_struct(Files_to_load[7])  # Prob Mass

## FIND NEAREST CRL TO FIND ASSOCIATED SRR
sp_id = 133  # FROM ADCIRC H5 FILE
# Build Array From CRL Dictionary
crl_lat = CRL["CRL"]["Col1"].values
crl_lon = CRL["CRL"]["Col0"].values

# Get SP Lat, Lon
if "nodeID" in list(grid.keys()):
    sp_mask = grid["nodeID"]["Col0"] == sp_id
    sp_lat = grid["nodeID"][sp_mask]["Col2"].values
    sp_lon = grid["nodeID"][sp_mask]["Col3"].values
else:
    sp_mask = grid["staID"]["Col0"] == sp_id
    sp_lat = grid["staID"][sp_mask]["Col1"].values
    sp_lon = grid["staID"][sp_mask]["Col2"].values

# Find Distance Between CRLs And SP Location
nearest_lat, nearest_lon, within_radius, distance_km, min_indx = find_nearest_latlon(
    sp_lat, sp_lon, crl_lat, crl_lon, max_radius_km=None
)
# Pull SRRs Assocaited To SP And Convert To [storm/year]
SSR_SP = [
    SRR_LI["SRR"]["Col0"][min_indx],
    SRR_MI["SRR"]["Col0"][min_indx],
    SRR_HI["SRR"]["Col0"][min_indx],
    SRR_All["SRR"]["Col0"][min_indx],
] * srr_to_stmperyr

## LOAD PROB MASS
TC_Freq = DSW["DSW_ITCS"]["Col0"].values
TotalFreq = np.sum(TC_Freq)

## FIND INFLUENTIAL STORMS AND POPULATE INTENSITY BUCKETS
# Grab Lat/Lon From Master Track Table
track_lat = MasterTrack["Param_ITCS"]["Col3"].values
track_lon = MasterTrack["Param_ITCS"]["Col4"].values
# Find Distance Between Track Reference Location And SP Location
nearest_lat, nearest_lon, within_radius, distance_km, min_indx = find_nearest_latlon(
    sp_lat, sp_lon, track_lat, track_lon, max_radius_km=None
)
# Create Mask
dist200 = distance_km <= trk_dist
# Only Keep Events That Fall Within 200 Km From SP
ReducedSet = MasterTrack["Param_ITCS"][dist200]
np.where(dist200)
if "NACCS" in chs_region:
    LI_pop = ReducedSet[ReducedSet["Col6"].values < 48]["Col0"].values
    MI_pop = np.array([])  # Empty , No MI
    HI_pop = ReducedSet[ReducedSet["Col6"].values >= 48]["Col0"].values
else:
    LI_pop = ReducedSet[ReducedSet["Col6"].values < 28]["Col0"].values
    MI_pop = ReducedSet[
        (ReducedSet["Col6"].values >= 28) & (ReducedSet["Col6"].values < 48)
    ]["Col0"].values
    HI_pop = ReducedSet[ReducedSet["Col6"].values >= 48]["Col0"].values

print("Tada!")


### HAILIE ADDED FOR PULLING THE STORM ID AND PROBABILITIES - OUTPUT CSV TO BE INPUTTED IN LIFECYCLE GENERATOR
SID = MasterTrack["Param_ITCS"]
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
probDSW = DSW["DSW_ITCS"]
probDSW.columns = ["DSW"]
SIDprob = pd.concat([SID, probDSW], axis=1)
SIDprob.to_csv("stormprob.csv", index=False)

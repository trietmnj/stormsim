
# Import Packages 
import h5py
import numpy as np
from HydroManipulator import HydroManipulator
import pandas as pd
import os
from datetime import datetime

# LC Population Implementation 
# Define Input JSON 
hydro_config = "hydroManipulator_config.json"
# Initalize HydroManipulator Class
hm = HydroManipulator(hydro_config)
'''
storm_types -> XC, TC, CC 
node_data_path -> Folder containing CHS Node ADCIRC/STWAVE data 
add_tides, add_slr, add_depth_limitaiton -> Boolean Switches for Hydro Manipulations
lc_path -> LC file to process
outpath -> path to dump csvs 
write_single_file -> Write populated LC as a single file or individual file per event

'''
# Get HDF5 Files Included 
h5_list = hm.list_h5_files()
# Identify ADCIRC File (Dictates Node ID For Bias Correction)
'''
For now, ingoring "Peaks" files , XC Files -> Future Implementation will need to account for this (i.e ignore bias correction for XCs)

'''
adcirc_files = [f for f in h5_list if "ADCIRC" in f]
wave_files = [f for f in h5_list if "ADCIRC" not in f]
# Pull Node ID From Name (5 identifier is always the nodeID)
nodeID = int(adcirc_files[0].split("_")[4].replace("SP", "")) 
region = adcirc_files[0].split("_")[0] # Identify CHS Regional Study
# Read LC Data ( Do we want to loop here?)
lc_data = pd.read_csv(hm.config["lc_path"])
#  Initialize HDF5 Object 
adcirc_h5 = h5py.File(os.path.join(hm.config["node_data_path"], adcirc_files[0]), 'r')
wave_h5 = h5py.File(os.path.join(hm.config["node_data_path"], wave_files[0]), 'r')
# Get Storms Stored In H5 
Groups = np.array(list(adcirc_h5.keys())) # keys will list Datasets/Groups at Base Level
groupIDs = np.array([int(s.split("-")[1].strip()) for s in Groups], dtype=int)
# Get Datasets In Groups 
adcirc_Datasets = list(adcirc_h5[Groups[0]].keys())
wave_Datasets = list(wave_h5[Groups[0]].keys())
# Get Wave Model Headers (Can vary by model)
wave_headers, Tp_flag = hm.chs_wave_model_header_locator(wave_Datasets)
# Initialize List 
stm_dic = lc_data.to_dict(orient="records")
# Loop Through Each Sampled Storm
for i, stormID in enumerate(lc_data["storm_id"].values):
    # Pull Dictionary 
    data = stm_dic[i]
    # Build Seed Date 
    hour_float = data["hour"]
    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)
    seconds = int(((hour_float - hours) * 60 - minutes) * 60)
    seed_date = datetime(data["year"], data["month"], data["day"], hours, minutes, seconds)
    # 
    adcirc_date = np.array(adcirc_h5[Groups[np.isin(groupIDs, stormID)][0]]["yyyymmddHHMM"])
    wave_date = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]]["yyyymmddHHMM"])
    #
    adcirc_date, adcirc_dt = hm.parse_timestamps(adcirc_date)
    wave_date, wave_dt = hm.parse_timestamps(wave_date)
    # This Is Temporary Patch , Storms With NaNs Should Not Reach Hydro Manipulator
    if len(adcirc_date) == 1:
        data["Water Elevation"] = np.nan
        data["Hm0"] = np.nan
        data["Tp"] = np.nan
        data["Wave Direction"] = np.nan
        data["Date"] = [seed_date]
    else:
        # Find Lowest Temporal Resolution To Use
        target_dt = np.max([np.max(adcirc_dt), np.max(wave_dt)])
        # Interp Model Data According To Resolutions
        if np.max(adcirc_dt)<np.max(wave_dt): # Circulation Model Has Finer Temporal Resolution 
            # Need To Downscale Surge Signal 
            tq = wave_date # Can Use Wave Model As Target Date Since It Resides Within ADCIRC's Time Domain 
            y = np.array(adcirc_h5[Groups[np.isin(groupIDs, stormID)][0]]["Water Elevation"])
            yt = hm.interp_hydrograph(y, adcirc_date, tq)
            # Append Storm Data To Dictionary 
            data["Water Elevation"] = yt
            data["Hm0"] = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["Hm0"]])
            data["Tp"] = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["Tp"]])
            data["Wave Direction"] = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["wDir"]])
        elif np.max(adcirc_dt)>np.max(wave_dt): # Wave Model Has Finer Temporal Resolution
            # Need To Downscale Wave Signal (Hm0, Tp, Wave Direction)
            # Need To Keep Time Window For Query Points Within Wave Model (No Extrapolation)
            # Find min/max of wave_date
            tmin, tmax = min(wave_date), max(wave_date)
            # Boolean mask: adcirc_date within [tmin, tmax]
            mask = (np.array(adcirc_date) >= tmin) & (np.array(adcirc_date) <= tmax)
            # Define Query Dates As ADCIRC's
            tq = [x for x, m in zip(adcirc_date, mask) if m]
            # Pull Wave Data
            y_hm0 = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["Hm0"]])
            y_tp = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["Tp"]])
            y_wdir = np.array(wave_h5[Groups[np.isin(groupIDs, stormID)][0]][wave_headers["wDir"]])
            # Interpolate TO ADCIRCs Date
            yt_hm0 = hm.interp_hydrograph(y_hm0, wave_date, tq)
            yt_tp = hm.interp_hydrograph(y_hm0, wave_date, tq)
            yt_wdir = hm.interp_hydrograph(y_hm0, wave_date, tq)
            # Append To Dictionary 
            data["Water Elevation"] = np.array(adcirc_h5[Groups[np.isin(groupIDs, stormID)][0]]["Water Elevation"])[mask]
            data["Hm0"] = yt_hm0
            data["Tp"] = yt_tp
            data["Wave Direction"] = yt_wdir
        else: # They are the same , Unlikely 
            pass # TBD 
        # Build Hydorgraph Date Vector As A Function Of The Seed Date 
        data["Date"] = hm.datetime_vector(seed_date, target_dt, len(yt))
        data["hydro_tstp"] = np.arange(0, len(yt))
        # ---------------- INSERT MANIPULATIONS HERE, ACT UPON data
        '''
        Call any manipulation methods here for each field as needed 
        can also be done on an outside loop so long as its done to stm_dic
        '''
        # Replace Entry In Storm Dictionary 
        stm_dic[i] = data

# Grab LC Name For SubFolder
LC_name, _ = os.path.splitext(os.path.basename(hm.config["lc_path"]))
# Create Output Directory 
if not os.path.isdir(os.path.join(hm.config["outpath"], LC_name)):
    os.makedirs(os.path.join(hm.config["outpath"], LC_name))
# Define Fields To Remove From Dictionaries
#fields_to_remove = ["lifecycle", "year_offset", "year", "month", "day", "hour", "storm_id"]
fields_to_remove = ["year_offset", "year", "month", "day", "hour"]
# Remove Fields Before Writting
for row in stm_dic:
    for field in fields_to_remove:
        row.pop(field, None) 
# Write CSV File Group 
if hm.config["write_single_file"] == "True":
    hm.write_dicts_to_csv(stm_dic, os.path.join(hm.config["outpath"], LC_name + ".csv"))
else:
    for i, row in enumerate(stm_dic, start=1):
        # Name Pattern LC_ # _ stmType _stormID_ # _ seed_date .csv
        filename = f"LC_{stm_dic[i]["lifecycle"]}_stormID_{stm_dic[i]["storm_id"]}_TC_{stm_dic[i]['Date'][0]}UTC.csv"
        filename = filename.replace(" ", "_").replace(":", "")
        hm.write_dict_to_csv(stm_dic[i], os.path.join(hm.config["outpath"], LC_name, filename))



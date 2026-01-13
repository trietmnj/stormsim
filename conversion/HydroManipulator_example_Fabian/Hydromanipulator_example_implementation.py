# Import Packages
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import h5py
from HydroManipulator import HydroManipulator

def parse_hour_float(hour_float):
    """Parses a float hour (e.g. 12.5) into hours, minutes, seconds."""
    hours = int(hour_float)
    minutes_remainder = (hour_float - hours) * 60
    minutes = int(minutes_remainder)
    seconds = int((minutes_remainder - minutes) * 60)
    return hours, minutes, seconds

def process_single_storm(hm, storm_id, data, adcirc_h5, wave_h5, group_ids, groups, wave_headers):
    """
    Processes a single storm event: aligns ADCIRC and Wave model data
    and performs interpolation/downscaling.
    """
    # Build Seed Date
    hours, minutes, seconds = parse_hour_float(data["hour"])
    seed_date = datetime(data["year"], data["month"], data["day"], hours, minutes, seconds)

    # Find the group index for this stormID
    # Assuming stormID matches one of the groupIDs
    match_indices = np.where(group_ids == storm_id)[0]
    if len(match_indices) == 0:
        print(f"Warning: Storm ID {storm_id} not found in H5 groups. Skipping...")
        return None

    group_idx = match_indices[0]
    group_name = groups[group_idx]

    # Extract Dates
    adcirc_date_raw = np.array(adcirc_h5[group_name]["yyyymmddHHMM"])
    wave_date_raw = np.array(wave_h5[group_name]["yyyymmddHHMM"])

    adcirc_date, adcirc_dt = hm.parse_timestamps(adcirc_date_raw)
    wave_date, wave_dt = hm.parse_timestamps(wave_date_raw)

    # Handle degenerate/missing data case
    if len(adcirc_date) <= 1:
        data["Water Elevation"] = np.nan
        data["Hm0"] = np.nan
        data["Tp"] = np.nan
        data["Wave Direction"] = np.nan
        data["Date"] = [seed_date]
        # data["hydro_tstp"] might need to be set if downstream expects it,
        # but original code didn't set it in this branch explicitly?
        # Original code: data["Date"] = [seed_date] and that's it.
        return data

    # Determine resolution dominance
    # Note: Using max() of dt arrays gives the coarsest resolution found in the series
    max_adcirc_dt = np.max(adcirc_dt)
    max_wave_dt = np.max(wave_dt)
    target_dt = max(max_adcirc_dt, max_wave_dt)

    if max_adcirc_dt < max_wave_dt:
        # Circulation Model Has Finer Temporal Resolution (smaller dt)
        # We need to downscale the Surge Signal (ADCIRC) to match Wave Model resolution?
        # Original logic: "Need To Downscale Surge Signal" -> "tq = wave_date"
        # Wait, if ADCIRC is finer (e.g. 10min) and Wave is coarser (e.g. 30min),
        # interpolating ADCIRC to Wave dates effectively downsamples (downscales resolution) ADCIRC.

        tq = wave_date # Use Wave Model timestamps as query points

        # Interpolate Water Elevation
        y_elev = np.array(adcirc_h5[group_name]["Water Elevation"])
        yt_elev = hm.interp_hydrograph(y_elev, adcirc_date, tq)

        # Wave data is already at the target resolution (coarser one)
        data["Water Elevation"] = yt_elev
        data["Hm0"] = np.array(wave_h5[group_name][wave_headers["Hm0"]])
        data["Tp"]  = np.array(wave_h5[group_name][wave_headers["Tp"]])
        data["Wave Direction"] = np.array(wave_h5[group_name][wave_headers["wDir"]])

        result_len = len(yt_elev)

    elif max_adcirc_dt > max_wave_dt:
        # Wave Model Has Finer Temporal Resolution
        # "Need To Downscale Wave Signal" -> Interpolate Wave to ADCIRC timestamps

        # Constrain query range to avoid extrapolation if ADCIRC extends beyond Wave data
        tmin, tmax = min(wave_date), max(wave_date)

        # Boolean mask: adcirc_date within [tmin, tmax]
        mask = (np.array(adcirc_date) >= tmin) & (np.array(adcirc_date) <= tmax)
        tq = [x for x, m in zip(adcirc_date, mask) if m]

        # Pull Wave Data
        y_hm0  = np.array(wave_h5[group_name][wave_headers["Hm0"]])
        y_tp   = np.array(wave_h5[group_name][wave_headers["Tp"]])
        y_wdir = np.array(wave_h5[group_name][wave_headers["wDir"]])

        # Interpolate TO ADCIRC Dates
        yt_hm0  = hm.interp_hydrograph(y_hm0, wave_date, tq)
        yt_tp   = hm.interp_hydrograph(y_tp,  wave_date, tq) # Fixed bug: was y_hm0
        yt_wdir = hm.interp_hydrograph(y_wdir, wave_date, tq) # Fixed bug: was y_hm0

        # ADCIRC Data (masked)
        data["Water Elevation"] = np.array(adcirc_h5[group_name]["Water Elevation"])[mask]
        data["Hm0"] = yt_hm0
        data["Tp"]  = yt_tp
        data["Wave Direction"] = yt_wdir

        result_len = len(yt_hm0)

    else:
        # Resolutions are similar/same
        # Original code: "pass # TBD"
        # We should probably just pick one timeline.
        # For safety, let's treat it like the first case (Wave dates as master)
        # or just fail gracefully if logic isn't defined.
        # Implemented fallback: Use Wave dates.

        tq = wave_date
        y_elev = np.array(adcirc_h5[group_name]["Water Elevation"])
        # If dates are identical, interp is just copy, but safer to interp to handle slight offsets
        yt_elev = hm.interp_hydrograph(y_elev, adcirc_date, tq)

        data["Water Elevation"] = yt_elev
        data["Hm0"] = np.array(wave_h5[group_name][wave_headers["Hm0"]])
        data["Tp"]  = np.array(wave_h5[group_name][wave_headers["Tp"]])
        data["Wave Direction"] = np.array(wave_h5[group_name][wave_headers["wDir"]])

        result_len = len(yt_elev)

    # Build Hydrograph Date Vector
    data["Date"] = hm.datetime_vector(seed_date, target_dt, result_len)
    data["hydro_tstp"] = np.arange(0, result_len)

    return data

def main():
    # Define Input JSON
    hydro_config = "../data/raw/HydroManipulator_example_Fabian/hydroManipulator_config.json"

    # Initialize HydroManipulator Class
    if not os.path.exists(hydro_config):
        print(f"Error: Configuration file '{hydro_config}' not found.")
        sys.exit(1)

    hm = HydroManipulator(hydro_config)

    # Validate Paths
    if not os.path.exists(hm.config["lc_path"]):
        print(f"Error: LC Path '{hm.config['lc_path']}' not found.")
        sys.exit(1)
    if not os.path.exists(hm.config["node_data_path"]):
        print(f"Error: Node Data Path '{hm.config['node_data_path']}' not found.")
        sys.exit(1)

    # Get HDF5 Files Included
    h5_list = hm.list_h5_files()

    # Identify ADCIRC File and Wave Files
    adcirc_files = [f for f in h5_list if "ADCIRC" in f]
    wave_files = [f for f in h5_list if "ADCIRC" not in f]

    if not adcirc_files:
        print("Error: No ADCIRC H5 files found.")
        sys.exit(1)
    if not wave_files:
        print("Error: No Wave H5 files found.")
        sys.exit(1)

    # Pull Node ID From Name (Identifier is always the nodeID in standard naming)
    # File naming assumption: Region_Type_NodeID_...
    try:
        parts = adcirc_files[0].split("_")
        region = parts[0]
        # Assuming index 4 is the node identifier based on original code
        node_id_str = parts[4].replace("SP", "")
        nodeID = int(node_id_str)
    except IndexError:
        print(f"Warning: Could not parse NodeID from filename '{adcirc_files[0]}'. Using default or skipping specific logic.")
        nodeID = 0
        region = "Unknown"

    print(f"Processing Region: {region}, NodeID: {nodeID}")

    # Load Data Sources
    try:
        lc_data = pd.read_csv(hm.config["lc_path"])
        adcirc_h5 = h5py.File(os.path.join(hm.config["node_data_path"], adcirc_files[0]), 'r')
        wave_h5 = h5py.File(os.path.join(hm.config["node_data_path"], wave_files[0]), 'r')
    except Exception as e:
        print(f"Error opening files: {e}")
        sys.exit(1)

    # Get Storms Stored In H5 (Groups)
    # Keys at Base Level are assumed to be groups like 'Storm-001', etc.
    groups = np.array(list(adcirc_h5.keys()))

    # Extract numeric IDs from Group names (e.g., 'Storm-123' -> 123)
    try:
        group_ids = np.array([int(s.split("-")[1].strip()) for s in groups], dtype=int)
    except IndexError:
        print("Error: H5 Group names do not match expected format 'Name-ID'.")
        group_ids = np.zeros(len(groups))

    # Get Datasets Metadata
    if len(groups) == 0:
        print("Error: No groups found in ADCIRC H5 file.")
        sys.exit(1)

    first_group = groups[0]
    wave_datasets = list(wave_h5[first_group].keys())

    # Get Wave Model Headers
    try:
        wave_headers, tp_flag = hm.chs_wave_model_header_locator(wave_datasets)
    except ValueError as e:
        print(f"Error locating wave headers: {e}")
        sys.exit(1)

    # Prepare Data Dictionary
    stm_dic = lc_data.to_dict(orient="records")

    # Loop Through Each Sampled Storm
    print(f"Processing {len(stm_dic)} storms...")

    for i, storm_data in enumerate(stm_dic):
        storm_id = storm_data["storm_id"]

        processed_data = process_single_storm(
            hm, storm_id, storm_data,
            adcirc_h5, wave_h5,
            group_ids, groups,
            wave_headers
        )

        if processed_data:
            # ---------------- INSERT MANIPULATIONS HERE ----------------
            '''
            Call any manipulation methods here for each field as needed.
            Example:
            processed_data["Water Elevation"] = hm.add_slr(processed_data["Water Elevation"], ...)
            '''
            # Update the dictionary record
            stm_dic[i] = processed_data

    # Cleanup H5 Resources
    adcirc_h5.close()
    wave_h5.close()

    # Output Preparation
    lc_name_base, _ = os.path.splitext(os.path.basename(hm.config["lc_path"]))
    output_dir = os.path.join(hm.config["outpath"], lc_name_base)

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Define Fields To Remove
    fields_to_remove = ["year_offset", "year", "month", "day", "hour"]

    # Clean up dictionary before writing
    for row in stm_dic:
        for field in fields_to_remove:
            row.pop(field, None)

    # Write Output
    if str(hm.config.get("write_single_file", "False")) == "True":
        output_file = os.path.join(hm.config["outpath"], lc_name_base + ".csv")
        print(f"Writing single output file to: {output_file}")
        hm.write_dicts_to_csv(stm_dic, output_file)
    else:
        print(f"Writing {len(stm_dic)} individual files to: {output_dir}")
        for row in stm_dic:
            if "lifecycle" not in row or "storm_id" not in row or "Date" not in row:
                continue

            # Date formatting for filename
            try:
                date_str = str(row['Date'][0]).replace(" ", "_").replace(":", "")
            except (IndexError, TypeError):
                date_str = "UNKNOWN_DATE"

            filename = f"LC_{row['lifecycle']}_stormID_{row['storm_id']}_TC_{date_str}UTC.csv"
            hm.write_dict_to_csv(row, os.path.join(output_dir, filename))

    print("Processing complete.")

if __name__ == "__main__":
    main()

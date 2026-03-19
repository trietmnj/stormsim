import os
import sys
import json
import logging
from datetime import datetime
from typing import Tuple, Any, Optional
import numpy as np
import pandas as pd
import h5py
# --- Custom Imports ---
from classes.hydrograph_manipulator.HydroManipulator import HydroManipulator
from classes import noaa_py
from classes.utilities.time_utils import parse_hour_float, parse_timestamps, datetime_vector
from classes.utilities.chs_utils import list_h5_files, chs_wave_model_header_locator, find_nearest_latlon, write_parquet
from classes.utilities.csv_utils import write_dict_to_csv, write_dicts_to_csv, merge_dicts

# --- Configuration Constants ---
HYDRO_CONFIG_PATH = "config-files/hydroManipulator_config.json"
CHS_META_DIR = "data/chs-files/regional-files/"
GRAVITY_CONSTANT = 9.81 # m/s^2 CHS Data Is m, s, deg

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_json_config(path: str) -> Any:
    """Helper to load JSON files with error handling."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, 'r') as f:
        return json.load(f)

def extract_h5_lat_lon(h5_obj: h5py.File) -> Tuple[float, float]:
    """Extracts latitude and longitude from H5 attributes flexibly."""
    try:
        # One-liner to find keys containing 'latitude'/'longitude' but not 'units'
        lat_val = next(h5_obj.attrs[k] for k in h5_obj.attrs
                       if 'latitude' in k.lower() and 'units' not in k.lower())
        lon_val = next(h5_obj.attrs[k] for k in h5_obj.attrs
                       if 'longitude' in k.lower() and 'units' not in k.lower())

        # Convert bytes to float if necessary
        if isinstance(lat_val, (bytes, np.bytes_)):
            lat_val = lat_val.decode('utf-8')
        if isinstance(lon_val, (bytes, np.bytes_)):
            lon_val = lon_val.decode('utf-8')

        return float(lat_val), float(lon_val)
    except StopIteration:
        raise ValueError("Could not find Latitude/Longitude attributes in H5 file.")

def get_node_metadata(region: str, lat: float, lon: float) -> Tuple[float, float, float]:
    """Finds the nearest node metadata (Ba, Br, depth) from CSV."""
    meta_path = os.path.join(CHS_META_DIR, f"{region}_nodes_metadata.csv")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Regional metadata not found: {meta_path}")

    chs_grid = pd.read_csv(meta_path)

    # Returns row index of nearest point
    # Note: find_nearest_latlon returns a tuple, index 4 is the row index in your utility
    nearest_info = find_nearest_latlon(
        lat, lon,
        chs_grid["lat"].to_numpy(),
        chs_grid["lon"].to_numpy(),
        max_radius_km=None
    )
    grd_row = nearest_info[4]

    return (
        chs_grid["Ba"].to_numpy()[grd_row],
        chs_grid["Br"].to_numpy()[grd_row],
        chs_grid["depth"].to_numpy()[grd_row]
    )

def process_single_storm(
    hm: HydroManipulator,
    storm_id: int,
    data: dict,
    adcirc_h5: h5py.File,
    wave_h5: h5py.File,
    group_ids: np.ndarray,
    groups: np.ndarray,
    wave_headers: dict
) -> Optional[dict]:
    """
    Core logic to align and interpolate ADCIRC and Wave data for a single storm.
    """
    # 1. Identify Group
    match_indices = np.where(group_ids == storm_id)[0]
    if len(match_indices) == 0:
        logging.warning(f"Storm ID {storm_id} not found in H5 groups. Skipping...")
        return None
    group_name = groups[match_indices[0]]

    # 2. Parse Dates
    hours, minutes, seconds = parse_hour_float(data["hour"])
    seed_date = datetime(data["year"], data["month"], data["day"], hours, minutes, seconds)

    adcirc_dates, adcirc_dt = parse_timestamps(np.array(adcirc_h5[group_name]["yyyymmddHHMM"]))
    wave_dates, wave_dt = parse_timestamps(np.array(wave_h5[group_name]["yyyymmddHHMM"]))

    # 3. Handle Missing Data
    if len(adcirc_dates) <= 1:
        return {**data, "water_elevation": np.nan, "date": [seed_date]}

    # 4. Determine Master Resolution (Coarsest dt dominates)
    max_adcirc_dt = np.max(adcirc_dt)
    max_wave_dt = np.max(wave_dt)
    target_dt = max(max_adcirc_dt, max_wave_dt)

    # 5. Interpolation Logic
    # Case A: Wave is coarser or equal -> Interpolate ADCIRC to Wave dates
    if max_adcirc_dt <= max_wave_dt:
        tq = wave_dates
        y_elev = np.array(adcirc_h5[group_name]["Water Elevation"])
        yt_elev = hm.interp_hydrograph(y_elev, adcirc_dates, tq)

        data.update({
            "water_elevation": yt_elev,
            "wave_height": np.array(wave_h5[group_name][wave_headers["Hm0"]]),
            "wave_peak_period": np.array(wave_h5[group_name][wave_headers["Tp"]]),
            "wave_direction": np.array(wave_h5[group_name][wave_headers["wDir"]])
        })
        result_len = len(yt_elev)

    # Case B: ADCIRC is coarser -> Interpolate Wave to ADCIRC dates (masked range)
    else:
        tmin, tmax = min(wave_dates), max(wave_dates)
        mask = (np.array(adcirc_dates) >= tmin) & (np.array(adcirc_dates) <= tmax)
        tq = [x for x, m in zip(adcirc_dates, mask) if m]

        # Interpolate Wave Data to ADCIRC timestamps
        data.update({
            "water_elevation": np.array(adcirc_h5[group_name]["Water Elevation"])[mask],
            "wave_height": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["Hm0"]]), wave_dates, tq),
            "wave_peak_period": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["Tp"]]), wave_dates, tq),
            "wave_direction": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["wDir"]]), wave_dates, tq)
        })
        result_len = len(data["wave_height"])

    # 6. Finalize Time Vectors
    data["date"] = datetime_vector(seed_date, target_dt, result_len)
    data["hydro_tstp"] = np.arange(0, result_len)

    return data

def main():
    # --- 1. Initialization ---
    if not os.path.exists(HYDRO_CONFIG_PATH):
        logging.error(f"Config file missing: {HYDRO_CONFIG_PATH}")
        sys.exit(1)

    hm = HydroManipulator(HYDRO_CONFIG_PATH)

    # Load Sub-Configs
    try:
        tides_config = load_json_config(hm.config["tide_config"])[0]
        lc_data = pd.read_csv(hm.config["lc_path"])
    except Exception as e:
        logging.error(f"Failed loading initial data: {e}")
        sys.exit(1)

    # --- 2. File Identification ---
    h5_list = list_h5_files(hm.config["node_data_path"])
    adcirc_files = [f for f in h5_list if "ADCIRC" in f]
    wave_files = [f for f in h5_list if "ADCIRC" not in f]

    if not adcirc_files or not wave_files:
        logging.error("Missing ADCIRC or Wave H5 files.")
        sys.exit(1)

    # Identify Node/Region from filename
    # Assumes format: Region_Type_NodeID_...
    parts = adcirc_files[0].split("_")
    region = parts[0]
    try:
        node_id = int(parts[4].replace("SP", ""))
    except (IndexError, ValueError):
        node_id = 0
        logging.warning("Could not parse NodeID, defaulting to 0")

    logging.info(f"Processing Region: {region}, NodeID: {node_id}")

    # --- 3. Main Processing Loop (Context Manager for Safety) ---
    adcirc_path = os.path.join(hm.config["node_data_path"], adcirc_files[0])
    wave_path = os.path.join(hm.config["node_data_path"], wave_files[0])

    with h5py.File(adcirc_path, 'r') as adcirc_h5, h5py.File(wave_path, 'r') as wave_h5:

        # A. Get Metadata & Bias
        sp_lat, sp_lon = extract_h5_lat_lon(adcirc_h5)
        Ba, Br, depth = get_node_metadata(region, sp_lat, sp_lon)

        # B. Prep Groups & Headers
        groups = np.array(list(adcirc_h5.keys()))
        try:
            # Vectorized ID extraction
            group_ids = np.array([int(s.split("-")[1]) for s in groups])
        except IndexError:
            group_ids = np.zeros(len(groups))

        wave_datasets = list(wave_h5[groups[0]].keys())
        wave_headers, _ = chs_wave_model_header_locator(wave_datasets)

        # C. Prep Tides & Trends
        season_trend = noaa_py.seasonal_cycle.get_station_seasonal_trend(tides_config["station"])
        season_mask_indices = np.searchsorted(np.array(season_trend['month']), lc_data['month'].to_numpy())

        tidal_ds = None
        if hm.config.get("add_tides"):
            tides_config["start_date"] = f"{lc_data['year'].min()}0101"
            tides_config["end_date"] = f"{lc_data['year'].max()}1231"
            tidal_ds = noaa_py.tides.get_tidal_prediction(tides_config)

        # D. Process Storms
        stm_records = lc_data.to_dict(orient="records")
        logging.info(f"Processing {len(stm_records)} storms...")

        for i, storm_data in enumerate(stm_records):
            processed_data = process_single_storm(
                hm, storm_data["storm_id"], storm_data,
                adcirc_h5, wave_h5, group_ids, groups, wave_headers
            )

            if processed_data:
                # -- Bias Correction --
                processed_data["water_elevation"] = hm.correct_bias(processed_data["water_elevation"], Ba, Br)

                # -- Steric Adjustment --
                trend_val = season_trend['level'][season_mask_indices[i]]
                processed_data["water_elevation"] += trend_val

                # -- Tides --
                if hm.config.get("add_tides"):
                    t_start, t_end = processed_data["date"][0], processed_data["date"][-1]
                    tide_time, tide_signal = noaa_py.data_query.filter_tide_data(tidal_ds, t_start, t_end)
                    processed_data["water_elevation"] = hm.add_tides(
                        processed_data["water_elevation"],
                        processed_data["date"],
                        tide_signal,
                        tide_time
                    )

                # Depth Limited Waves
                if hm.config.get("add_depth_limitation"):
                    # Compute Water Depth (h)
                    h = processed_data["water_elevation"] + depth
                    # Adjust Waves That Meet Criteria
                    processed_data["wave_height"], _ = hm.add_depth_limitation(processed_data["wave_height"],
                                             processed_data["wave_peak_period"],
                                               h, GRAVITY_CONSTANT)

                # Update record in place
                stm_records[i] = processed_data

    # --- 4. Output Writing ---
    lc_name_base = os.path.splitext(os.path.basename(hm.config["lc_path"]))[0]
    output_dir = os.path.join(hm.config["outpath"], lc_name_base)
    os.makedirs(output_dir, exist_ok=True)

    # Clean unneeded fields
    keys_to_drop = ["year_offset", "year", "month", "day", "hour"]
    for rec in stm_records:
        for k in keys_to_drop:
            rec.pop(k, None)

    # Write
    write_single = str(hm.config.get("write_single_file", "False")).lower() == "true"

    if write_single:
        out_file = os.path.join(hm.config["outpath"], f"{lc_name_base}.parquet")
        logging.info(f"Writing single file: {out_file}")
        #write_dicts_to_csv(stm_records, out_file)
        aa = merge_dicts(stm_records)
        write_parquet(out_file, aa)
    else:
        logging.info(f"Writing individual files to: {output_dir}")
        for row in stm_records:
            if not all(k in row for k in ["lifecycle", "storm_id", "date"]):
                continue

            try:
                date_str = str(row['date'][0]).replace(" ", "_").replace(":", "")
            except (IndexError, TypeError):
                date_str = "UNKNOWN_DATE"

            fname = f"LC-{row['lifecycle']}_{date_str}UTC_stormID-{row['storm_id']}_TC_.parquet"
            # write_dict_to_csv(row, os.path.join(output_dir, fname))
            write_parquet(os.path.join(output_dir, fname), row)
    logging.info("Processing complete.")

if __name__ == "__main__":
    main()

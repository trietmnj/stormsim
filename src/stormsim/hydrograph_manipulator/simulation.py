import os
import json
import logging
from datetime import datetime
from typing import Tuple, Any, Optional, Dict, List
import numpy as np
import pandas as pd
import h5py
import fsspec

from .HydroManipulator import HydroManipulator
from .. import noaa_py
from ..utilities.time_utils import parse_hour_float, parse_timestamps, datetime_vector
from ..utilities.chs_utils import list_h5_files, chs_wave_model_header_locator, find_nearest_latlon, write_parquet
from ..utilities.csv_utils import merge_dicts
from .. import sea_level_rise as slr
from ..utilities.storage import StorageContext

GRAVITY_CONSTANT = 9.81

def extract_h5_lat_lon(h5_obj: h5py.File) -> Tuple[float, float]:
    try:
        lat_val = next(h5_obj.attrs[k] for k in h5_obj.attrs
                       if 'latitude' in k.lower() and 'units' not in k.lower())
        lon_val = next(h5_obj.attrs[k] for k in h5_obj.attrs
                       if 'longitude' in k.lower() and 'units' not in k.lower())
        if isinstance(lat_val, (bytes, np.bytes_)):
            lat_val = lat_val.decode('utf-8')
        if isinstance(lon_val, (bytes, np.bytes_)):
            lon_val = lon_val.decode('utf-8')
        return float(lat_val), float(lon_val)
    except StopIteration:
        raise ValueError("Could not find Latitude/Longitude attributes in H5 file.")

def get_node_metadata(meta_path: str, lat: float, lon: float) -> Tuple[float, float, float]:
    if not meta_path.startswith("s3://") and not os.path.exists(meta_path):
        raise FileNotFoundError(f"Regional metadata not found: {meta_path}")
    chs_grid = pd.read_csv(meta_path)
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

def resolve_tides_config(tide_config_path: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assemble the NOAA gauge config from inputs.tide_station and/or a
    inputs.tide_config json file (a single-element list).

    inputs.tide_station wins, so callers holding the gauge id in a database
    need not stage a one-field json per job. Its defaults match the shipped
    tidal_gauge.json rather than get_tidal_prediction's own signature defaults
    (interval 'h'), so moving to inline cannot silently coarsen tides from
    1-minute to hourly. Read via fsspec so s3:// works -- plain open() behind
    os.path.exists() yielded {} for any URI, which disabled SLR/tides silently.
    """
    tides_config = {}
    if tide_config_path:
        with fsspec.open(tide_config_path, 'r') as f:
            tides_config = json.load(f)[0]

    if inputs.get("tide_station") is not None:
        tides_config = {
            "datum": "MSL",
            "interval": "1",
            **tides_config,
            "station": str(inputs["tide_station"]),
        }
    return tides_config


def select_h5_files(node_data_path: str, inputs: Dict[str, Any]) -> Tuple[str, str]:
    """
    Pick the single ADCIRC (water level) + wave H5 pair for this savepoint.

    Explicit inputs.adcirc_file / inputs.wave_file win. Otherwise fall back to
    sniffing CHS naming, where the water level file carries "ADCIRC" in its name.
    """
    adcirc_name = inputs.get("adcirc_file")
    wave_name = inputs.get("wave_file")
    if not (adcirc_name and wave_name):
        h5_list = list_h5_files(node_data_path)
        adcirc_name = adcirc_name or next((f for f in h5_list if "ADCIRC" in f), None)
        wave_name = wave_name or next((f for f in h5_list if "ADCIRC" not in f), None)

    if not adcirc_name or not wave_name:
        raise FileNotFoundError(
            f"Missing ADCIRC or Wave H5 files in {node_data_path!r}; "
            "set inputs.adcirc_file and inputs.wave_file to name them explicitly."
        )
    return adcirc_name, wave_name


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
    match_indices = np.where(group_ids == storm_id)[0]
    if len(match_indices) == 0:
        return None
    group_name = groups[match_indices[0]]

    hours, minutes, seconds = parse_hour_float(data["hour"])
    seed_date = datetime(data["year"], data["month"], data["day"], hours, minutes, seconds)

    adcirc_dates, adcirc_dt = parse_timestamps(np.array(adcirc_h5[group_name]["yyyymmddHHMM"]))
    wave_dates, wave_dt = parse_timestamps(np.array(wave_h5[group_name]["yyyymmddHHMM"]))

    if len(adcirc_dates) <= 1 or len(wave_dates) <= 1:
        return {
            **data,
            "water_elevation": np.array([np.nan]),
            "wave_height": np.array([np.nan]),
            "wave_peak_period": np.array([np.nan]),
            "wave_direction": np.array([np.nan]),
            "date": [seed_date],
            "hydro_tstp": np.array([0])
        }

    max_adcirc_dt = np.max(adcirc_dt)
    max_wave_dt = np.max(wave_dt)
    target_dt = max(max_adcirc_dt, max_wave_dt)

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
    else:
        tmin, tmax = min(wave_dates), max(wave_dates)
        mask = (np.array(adcirc_dates) >= tmin) & (np.array(adcirc_dates) <= tmax)
        tq = [x for x, m in zip(adcirc_dates, mask) if m]
        data.update({
            "water_elevation": np.array(adcirc_h5[group_name]["Water Elevation"])[mask],
            "wave_height": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["Hm0"]]), wave_dates, tq),
            "wave_peak_period": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["Tp"]]), wave_dates, tq),
            "wave_direction": hm.interp_hydrograph(np.array(wave_h5[group_name][wave_headers["wDir"]]), wave_dates, tq)
        })
        result_len = len(data["wave_height"])

    data["date"] = datetime_vector(seed_date, target_dt, result_len)
    data["hydro_tstp"] = np.arange(0, result_len)
    return data

def run_hydro_manipulator(config: Dict[str, Any], is_lambda: bool = False, storage_context: Optional[StorageContext] = None) -> Dict[str, Any]:
    """
    Run the hydrograph manipulator for a SINGLE savepoint.

    Exactly one ADCIRC (water level) and one wave H5 file are read per call.
    Supply them explicitly via inputs.adcirc_file / inputs.wave_file, or leave
    them off to sniff CHS naming ("ADCIRC" substring) from node_data_path.
    inputs.region overrides the region token used to locate
    {region}_nodes_metadata.csv in chs_meta_dir.

    The NOAA gauge for tides/SLR comes from inputs.tide_station (preferred) or
    inputs.tide_config, a json file holding a single-element list. Either is
    required when add_slr or add_tides is set.
    """
    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)

    # 1. Initialization
    hm = HydroManipulator(config)

    # Use ctx to resolve all paths
    lc_path = ctx.get_input_path("lc_path")
    node_data_path = ctx.get_input_path("node_data_path")
    tide_config_path = ctx.get_input_path("tide_config")
    chs_meta_dir = ctx.get_input_path("chs_meta_dir") or "data/chs-files/regional-files/"

    tides_config = resolve_tides_config(tide_config_path, ctx.inputs)

    if (hm.config.get("add_slr") or hm.config.get("add_tides")) and tides_config.get("station") is None:
        raise ValueError(
            "add_slr/add_tides require a NOAA station: set inputs.tide_station "
            "or point inputs.tide_config at a config supplying 'station'"
        )

    lc_data = pd.read_csv(lc_path)

    # 2. File Identification
    adcirc_name, wave_name = select_h5_files(node_data_path, ctx.inputs)

    # Download H5 files from S3 to /tmp so h5py can open them locally.
    # Only the two files actually read -- the prefix may hold many savepoints
    # and Lambda /tmp is 512MB (CHS files run ~25-40MB each).
    if node_data_path.startswith("s3://"):
        import boto3
        from urllib.parse import urlparse
        parsed = urlparse(node_data_path)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip("/").rstrip("/") + "/"
        local_node_dir = "/tmp/node_data"
        os.makedirs(local_node_dir, exist_ok=True)
        s3 = boto3.client("s3")
        for fname in (adcirc_name, wave_name):
            s3.download_file(bucket, f"{prefix}{fname}", os.path.join(local_node_dir, fname))
        node_data_path = local_node_dir

    region = ctx.inputs.get("region") or adcirc_name.split("_")[0]

    adcirc_path = os.path.join(node_data_path, adcirc_name)
    wave_path = os.path.join(node_data_path, wave_name)

    with h5py.File(adcirc_path, 'r') as adcirc_h5, h5py.File(wave_path, 'r') as wave_h5:
        sp_lat, sp_lon = extract_h5_lat_lon(adcirc_h5)
        meta_path = os.path.join(chs_meta_dir, f"{region}_nodes_metadata.csv")
        Ba, Br, depth = get_node_metadata(meta_path, sp_lat, sp_lon)

        groups = np.array(list(adcirc_h5.keys()))
        group_ids = np.array([int(s.split("-")[1]) if "-" in s else 0 for s in groups])

        wave_datasets = list(wave_h5[groups[0]].keys())
        wave_headers, _ = chs_wave_model_header_locator(wave_datasets)

        season_trend = None
        season_mask_indices = None
        if tides_config.get("station") is not None:
            season_trend = noaa_py.seasonal_cycle.get_station_seasonal_trend(tides_config["station"])
            season_mask_indices = np.searchsorted(np.array(season_trend['month']), lc_data['month'].to_numpy())

        tidal_ds = None
        if hm.config.get("add_tides"):
            tides_config["start_date"] = f"{lc_data['year'].min()}0101"
            tides_config["end_date"] = f"{lc_data['year'].max()}1231"
            tidal_ds = noaa_py.tides.get_tidal_prediction(tides_config)

        slr_scenarios_df = None
        if hm.config.get("add_slr"):
            # station presence already validated above
            _, alpha = slr.linear_trend_api.get_noaa_linear_trend(int(tides_config["station"]))
            _, slr_scenarios_df = hm.get_slr_projections(
                hm.config.get("slr_projection"),
                hm.config.get("slr_projection_scenario"),
                alpha,
                lc_data['year'].min(),
                lc_data['year'].max()
            )

        stm_records = lc_data.to_dict(orient="records")
        for i, storm_data in enumerate(stm_records):
            processed_data = process_single_storm(
                hm, storm_data["storm_id"], storm_data,
                adcirc_h5, wave_h5, group_ids, groups, wave_headers
            )

            if processed_data:
                processed_data["water_elevation"] = hm.correct_bias(processed_data["water_elevation"], Ba, Br)
                if season_trend is not None:
                    trend_val = season_trend['level'][season_mask_indices[i]]
                    processed_data["water_elevation"] += trend_val
                if tidal_ds is not None:
                    t_start, t_end = processed_data["date"][0], processed_data["date"][-1]
                    tide_time, tide_signal = noaa_py.data_query.filter_tide_data(tidal_ds, t_start, t_end)
                    processed_data["water_elevation"] = hm.add_tides(
                        processed_data["water_elevation"], processed_data["date"], tide_signal, tide_time
                    )
                if slr_scenarios_df is not None:
                    slr_adj = slr_scenarios_df[slr_scenarios_df['year'] == storm_data['year']].iloc[:, 1].to_numpy()
                    processed_data["water_elevation"] += slr_adj / 1000.0

                if hm.config.get("add_depth_limitation"):
                    h = processed_data["water_elevation"] + depth
                    processed_data["wave_height"], _ = hm.add_depth_limitation(
                        processed_data["wave_height"], processed_data["wave_peak_period"], h, GRAVITY_CONSTANT
                    )
                stm_records[i] = processed_data

    # Output Writing
    lc_name_base = os.path.splitext(os.path.basename(lc_path))[0]
    output_target = ctx.get_output_path()
    
    keys_to_drop = ["year_offset", "year", "month", "day", "hour"]
    for rec in stm_records:
        for k in keys_to_drop:
            rec.pop(k, None)

    write_single = str(hm.config.get("write_single_file", "False")).lower() == "true"
    if write_single:
        aa = merge_dicts(stm_records)
        write_parquet(output_target, aa) # ctx.get_output_path() handles S3 if storage_type is s3
    else:
        # For multiple files, we currently assume local or specialized S3 logic
        # For now, let's keep the single file approach as the primary cloud-friendly one
        if output_target.startswith("s3://"):
             aa = merge_dicts(stm_records)
             write_parquet(output_target, aa)
        else:
            os.makedirs(output_target, exist_ok=True)
            for row in stm_records:
                if not all(k in row for k in ["lifecycle", "storm_id", "date"]): continue
                date_str = str(row['date'][0]).replace(" ", "_").replace(":", "")
                fname = f"LC-{row['lifecycle']}_{date_str}UTC_stormID-{row['storm_id']}_TC.parquet"
                write_parquet(os.path.join(output_target, fname), row)

    return {"status": "success", "output": output_target}

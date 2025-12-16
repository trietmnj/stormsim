# noaa-requests/noaa-py/download.py
import datetime
from typing import Any, Dict, List, Tuple, Iterable, Optional
from dataclasses import dataclass

import pandas as pd

import noaapy


@dataclass
class DownloadDataConfig:
    stations: Dict[str, Dict[str, Any]]
    datum: str
    products: List[str]
    date_range: Optional[pd.Interval] = None


def download(
    download_request_cfg: DownloadDataConfig,
    stations: dict,
):
    """Entry point to the download."""
    station_ids: List[str] = [s for s in stations.keys()]
    start_time = datetime.datetime.now()
    # Station lookup and validity check
    station_ids, not_found = _filter_station_ids(
        station_ids, stations
    )

    # Results container
    data: List[Dict[str, Any]] = []

    # Loop over stations and products
    for station_id in station_ids:
        station = stations[station_id]
        for product in download_request_cfg.products:
            station_product = {
                "id": station_id,
                "name": station["name"],
                "lon": station["lng"],
                "lat": station["lat"],
                "state": station["state"],
                "WL_datum": "Not found",
                "TP_datum": "Not found",
                "WL_downloaded_product": "Not found",
                "TP_downloaded_product": "Not found",
                "record_length": "Not found",
                "WL": "Not found",
                "TP": "Not found",
            }

            interval_param: str = noaapy.globals.INTERVAL_NAME_TO_PARAM[product]
            if product not in noaapy.globals.INTERVAL_NAME_TO_PARAM:
                continue

            # download based on dates
            if download_request_cfg.date_range:
                print(
                    f"Download specific date range for station {station_id} and product {product}. From {download_request_cfg.start_date} to {download_request_cfg.end_date}"
                )
                idx, end_date, begin_date = noaapy.dates.get_valid_station_interval(
                    station,
                    download_request_cfg.date_range
                )
                # Update station record dates if needed
                station["start_date"][idx] = (
                    f"{begin_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )
                station["end_date"][idx] = (
                    f"{end_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )
            else:
                print(
                    f"Downloading full record for station '{station_id}' and product '{product}'"
                )

            water_level_datum, tide_prediction_datum, _ = noaapy.params.get_datum(
                station, download_request_cfg.datum
            )
            # Tidal prediction interval
            interval, _ = noaapy.params.get_prediction_interval(
                station, interval_param, station["greatlakes"]
            )

            # Update metadata on the entry
            station_product.update(
                {
                    "WL_datum": water_level_datum,
                    "TP_datum": tide_prediction_datum,
                    "WL_downloaded_product": noaapy.globals.PRODUCT_LABELS[
                        interval_param
                    ],
                    "TP_downloaded_product": interval,
                    "record_length": station["record_length"][idx],
                }
            )

            # NAVD88 adjustment for NOAA endpoints
            water_level_datum = water_level_datum.replace("NAVD88", "NAVD")
            tide_prediction_datum = tide_prediction_datum.replace("NAVD88", "NAVD")

            # Download water levels
            data = noaapy.download.download_wl(
                entry_idx,
                data,
                water_level_datum,
                station_id,
                timezone,
                units,
                data_format,
                st_dates,
                end_dates,
                gen_url,
                request_options,  # dict expected by _wl_download
                interval_param,
            )

            # Download tidal predictions
            data = noaapy.download.download_tidal_predictions(
                entry_idx,
                data,
                tide_prediction_datum,
                station_id,
                timezone,
                units,
                data_format,
                interval,
                st_dates_p,
                end_dates_p,
                gen_url,
                timeout,  # keep as-is if tidal_predictions_downloader expects a scalar
                station["greatlakes"],
                interval_param,
                station,
            )

            # Great Lakes special handling
            if station["greatlakes"] == 0:
                data = noaapy.processing.vector_length_check(
                    entry_idx,
                    data,
                    interval_param,
                    station["greatlakes"],
                )

            # Compute total record length (non-NaN data)
            data = noaapy.processing.record_length_calc(entry_idx, data, interval_param)

            # Add Begin / End timestamps to this entry
            _set_beg_end_from_wl_entry(station_product)

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print(f"Total Run Time: {run_time}")

    return data, not_found


def _filter_station_ids(
    id_list: Iterable[str], station_lookup: Dict[str, Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """
    Split requested ids into valid ones (present in station_lookup)
    and not_found ones.
    """
    valid_ids: List[str] = []
    not_found: List[str] = []

    for station_id in id_list:
        if station_id in station_lookup:
            valid_ids.append(station_id)
        else:
            not_found.append(station_id)

    return valid_ids, not_found


def _set_beg_end_from_wl_entry(entry: Dict[str, Any]) -> None:
    """Set 'Beg' and 'End' keys on an s_data entry based on its WL DataFrame."""
    wl = entry.get("WL")
    if isinstance(wl, pd.DataFrame) and not wl.empty:
        entry["Beg"] = wl["DateTime"].iloc[0].strftime("%Y-%m-%d %H:%M")
        entry["End"] = wl["DateTime"].iloc[-1].strftime("%Y-%m-%d %H:%M")

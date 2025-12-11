# noaa-requests/noaa-py/download.py
import datetime
from typing import Any, Dict, List, Tuple, Iterable, Optional
from dataclasses import dataclass

import pandas as pd

import noaapy


@dataclass
class DownloadDataConfig:
    station_ids: List[str]
    datum: str
    products: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def download(
    download_data_cfg: DownloadDataConfig,
    station_list,
):
    """Entry point to the download."""
    # station_ids = download_data_cfg.station_ids
    # requested_datum = download_data_cfg.datum
    # prod = download_data_cfg.prod
    # operation = download_data_cfg.op_mode
    # begin_date = download_data_cfg.d_beg
    # end_date = download_data_cfg.d_end

    start_time = datetime.datetime.now()

    default_cfg = DownloadDataConfig(
        station_ids=[],
        datum=noaapy.globals.DEFAULT_DATUM,
        products=noaapy.globals.DEFAULT_PRODUCTS,
        operation_mode="full_record",
    )

    # Defaults from globals
    # datum = noaapy.globals.DEFAULT_DATUM
    # timezone = noaapy.globals.DEFAULT_TIMEZONE
    # units = noaapy.globals.DEFAULT_UNITS
    # data_format = noaapy.globals.DEFAULT_DATA_FORMAT
    # gen_url = noaapy.globals.BASE_API_URL
    # timeout = noaapy.globals.DEFAULT_TIMEOUT
    # request_options = {"timeout": timeout}

    # Station lookup and validity check
    stations = _build_station_lookup(station_list)
    station_ids, not_found = _filter_station_ids(
        download_data_cfg.station_ids, stations
    )

    # Results container
    data: List[Dict[str, Any]] = []

    # Loop over stations and products
    for station_id in station_ids:
        station = stations[station_id]
        for product in download_data_cfg.products:
            # Create base entry and append immediately so all helpers
            # can rely on its index.
            s_data_entry = _base_data_entry(station_id, station)
            data.append(s_data_entry)
            entry_idx = len(data) - 1

            interval_param: str = noaapy.globals.INTERVAL_NAME_TO_PARAM[product]
            if product not in noaapy.globals.INTERVAL_NAME_TO_PARAM:
                continue

            # use data range rather than full record
            if download_data_cfg.start_date and download_data_cfg.end_date:
                # For "specific_date", ensure requested date range is available
                idx, end_date, begin_date = noaapy.dates.date_search(
                    station,
                    download_data_cfg.start_date,
                    download_data_cfg.end_date,
                    idx,
                )

                # Update station record dates if needed
                station["start_date"][idx] = (
                    f"{begin_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )
                station["end_date"][idx] = (
                    f"{end_date.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                )

            # Datum selection
            datum, datum_p = noaapy.params.datum_selector(
                station, download_data_cfg.datum
            )

            # Tidal prediction interval
            interval, _ = noaapy.params.prediction_interval_selector(
                station, interval_param, station["greatlakes"]
            )

            # Update metadata on the entry
            s_data_entry.update(
                {
                    "WL_datum": datum,
                    "TP_datum": datum_p,
                    "WL_downloaded_product": noaapy.globals.PRODUCT_LABELS[
                        interval_param
                    ],
                    "TP_downloaded_product": interval,
                    "record_length": station["record_length"][idx],
                }
            )

            # NAVD88 adjustment for NOAA endpoints
            wl_datum_for_api = datum.replace("NAVD88", "NAVD")
            tp_datum_for_api = datum_p.replace("NAVD88", "NAVD")

            # Download water levels
            data = noaapy.download.download_wl(
                entry_idx,
                data,
                wl_datum_for_api,
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
                tp_datum_for_api,
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
            _set_beg_end_from_wl_entry(s_data_entry)

    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    print(f"Total Run Time: {run_time}")

    return data, not_found


def _build_station_lookup(
    station_list: Iterable[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Map station id -> station dict."""
    return {s["id"]: s for s in station_list}


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


def _base_data_entry(station_id: str, station: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize a result entry with common fields + 'Not found' defaults."""
    return {
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


def _set_beg_end_from_wl_entry(entry: Dict[str, Any]) -> None:
    """Set 'Beg' and 'End' keys on an s_data entry based on its WL DataFrame."""
    wl = entry.get("WL")
    if isinstance(wl, pd.DataFrame) and not wl.empty:
        entry["Beg"] = wl["DateTime"].iloc[0].strftime("%Y-%m-%d %H:%M")
        entry["End"] = wl["DateTime"].iloc[-1].strftime("%Y-%m-%d %H:%M")

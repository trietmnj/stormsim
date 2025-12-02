# noaa-requests/noaa-py/noaapy/wl_downloader_v2.py
import datetime
import numpy as np
import noaapy


def wl_downloader_v2(
    id_list, station_list, requested_datum, prod, op_mode, d_beg, d_end
):
    """Entry point to the download"""
    if op_mode not in [1, 2]:
        raise ValueError(
            "Please use a valid operational mode (1 - full record, 2 - Specific Date)"
        )

    # Start Timer
    start_time = datetime.datetime.now()

    # Define Initial Variables
    datum = "MSL"  # Preferred Datum for Data Download
    timezone = "GMT"  # Preferred Time Zone for Data Download
    units = "metric"  # Preferred Units for Data Download
    data_format = "csv"  # Download Data Format
    gen_url = "https://api.tidesandcurrents.noaa.gov"  # NOAA CO-OPS URL
    timeout = 800

    # Check if stations are in inventory
    logical_matrix = np.array([[s["id"] == id for id in id_list] for s in station_list])
    max_logical = np.max(logical_matrix, axis=0)
    valid_indices = np.argmax(logical_matrix, axis=0)

    # Single out stations that were not found in StationList
    not_found = [id_list[i] for i, val in enumerate(max_logical) if not val]

    # Create valid station id list
    id_list = [
        station_list[valid_indices[i]]["id"] for i, val in enumerate(max_logical) if val
    ]

    # Initialize Counter
    ctr = 0

    # Initialize Results
    s_data = []

    # Download Data for Each Station
    for i, station_id in enumerate(id_list):
        print(f"------------------ {i + 1} / {len(id_list)} ---------------------")
        for product in prod:
            # Extract Station from Data Structure
            d_struct = next(s for s in station_list if s["id"] == station_id)
            s_data_entry = {
                "id": station_id,
                "name": d_struct["name"],
                "lon": d_struct["lon"],
                "lat": d_struct["lat"],
                "state": d_struct["state"],
            }

            # Check WL Measurements Products Available
            flag4, flag1, indx = noaapy.wl_measurements_product_selector_v2(
                d_struct, product
            )

            if flag4 == 1:
                s_data_entry.update(
                    {
                        "WL_datum": "Not found",
                        "TP_datum": "Not found",
                        "WL_downloaded_product": "Not found",
                        "TP_downloaded_product": "Not found",
                        "record_length": "Not found",
                        "WL": "Not found",
                        "TP": "Not found",
                    }
                )
                s_data.append(s_data_entry)
                ctr += 1
                continue

            # Check if Date Range of Interest is Available
            if op_mode == 2:
                indx, d_end, d_beg, dummy3 = noaapy.date_search(
                    d_struct, d_beg, d_end, indx
                )
                if not dummy3:
                    d_struct["start_date"][indx] = (
                        f"{d_beg.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                    )
                    d_struct["end_date"][indx] = (
                        f"{d_end.strftime('%Y-%m-%d %H:%M:%S')} GMT"
                    )
                else:
                    s_data_entry.update(
                        {
                            "WL_datum": "Not found",
                            "TP_datum": "Not found",
                            "WL_downloaded_product": "Not found",
                            "TP_downloaded_product": "Not found",
                            "record_length": "Not found",
                            "WL": "Not found",
                            "TP": "Not found",
                        }
                    )
                    s_data.append(s_data_entry)
                    ctr += 1
                    continue

            # Divide Date Range in Allowed Segments
            st_dates, end_dates, st_dates_p, end_dates_p = noaapy.download_segmentation(
                d_struct, flag1, indx
            )

            # Check Datum Availability
            datum, datum_p = noaapy.datum_selector(d_struct, requested_datum)

            # Check Tidal Predictions Intervals
            interval, _ = noaapy.prediction_interval_selector(
                d_struct, flag1, d_struct["greatlakes"]
            )

            # Assign Info to Sdata
            s_data_entry.update(
                {
                    "WL_datum": datum,
                    "TP_datum": datum_p,
                    "WL_downloaded_product": product_label(flag1),
                    "TP_downloaded_product": interval,
                    "record_length": d_struct["record_length"][indx],
                }
            )

            # NAVD88 Adjustment
            if datum == "NAVD88":
                datum = "NAVD"
            if datum_p == "NAVD88":
                datum_p = "NAVD"

            # Build URL & Download Measured Data
            s_data = noaapy.wl_download(
                ctr,
                s_data,
                datum,
                station_id,
                timezone,
                units,
                data_format,
                st_dates,
                end_dates,
                gen_url,
                timeout,
                flag1,
            )

            # Download Tidal Predictions
            s_data = tidal_predictions_downloader(
                ctr,
                s_data,
                datum_p,
                station_id,
                timezone,
                units,
                data_format,
                interval,
                st_dates_p,
                end_dates_p,
                gen_url,
                timeout,
                d_struct["greatlakes"],
                flag1,
                d_struct,
            )

            # Make Sure Time Vectors Are the Same Length
            if d_struct["greatlakes"] == 0:
                s_data = vector_length_check(ctr, s_data, flag1, d_struct["greatlakes"])

            # Compute Total Record Length (Non NaN Data)
            s_data = record_length_calc(ctr, s_data, flag1)

            # Add DateRange
            s_data_entry.update(
                {
                    "Beg": s_data[ctr]["WL"]["DateTime"][0].strftime("%Y-%m-%d %H:%M"),
                    "End": s_data[ctr]["WL"]["DateTime"][-1].strftime("%Y-%m-%d %H:%M"),
                }
            )

            # Increment Counter for Product Loop
            ctr += 1

    # End Timer
    end_time = datetime.datetime.now()
    run_time = end_time - start_time

    return s_data, not_found


def product_label(flag):
    labels = {
        "6": "6 minutes",
        "1": "hourly",
        "6p": "6 minutes preliminary",
        "hilo": "High/Low",
        "m": "monthly",
    }
    return labels.get(flag, "unknown")

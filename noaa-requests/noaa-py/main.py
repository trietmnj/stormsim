# noaa-requests/noaa-py/main.py
import noaapy

if __name__ == "__main__":
    station_list = [
        {
            "id": "123456",
            "name": "Example Station",
            "lon": -70.12345,
            "lat": 40.67891,
            "state": "MA",
            "record_length": [10],
            "start_date": ["1900-01-01"],
            "end_date": ["2025-12-29"],
            "greatlakes": 0,
            "WL_products": [
                "Verified Monthly Mean Water Level",
                "Verified Hourly Height Water Level",
                "Verified 6-Minute Water Level",
            ],
        }
    ]

    id_list = ["123456"]  # station ids
    requested_datum = "MSL"
    prod = ["Verified Monthly Mean Water Level"]
    op_mode = 1  # Full record
    d_beg = None  # Not used in full record mode
    d_end = None  # Not used in full record mode

    # Call the downloader function
    downloaded_data, not_found = noaapy.wl_downloader_v2(
        id_list,
        station_list,
        requested_datum,
        prod,
        op_mode,
        d_beg,
        d_end,
    )

    print("Downloaded Data:", downloaded_data)
    print("Not Found Stations:", not_found)

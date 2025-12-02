# noaa-requests/noaa-py/main.py
from noaapy.wl_downloader_v2 import wl_downloader_v2

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
        }
    ]

    id_list = ["123456"]  # station ids
    requested_datum = "MSL"
    prod = ["water_level"]
    op_mode = 1  # Full record
    d_beg = None  # Not used in full record mode
    d_end = None  # Not used in full record mode

    # Call the downloader function
    try:
        downloaded_data, not_found = wl_downloader_v2(
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

    except Exception as e:
        print("Error during downloading NOAA data:", e)

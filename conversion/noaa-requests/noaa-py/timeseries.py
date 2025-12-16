# conversion/noaa-requests/noaa-py/main.py
import pandas as pd
import json

import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/
# https://tidesandcurrents.noaa.gov/api-helper/url-generator.html

# This script downloads a specific data need:
# Contribution from tides - interpolated mapped to the time step as the hydrograph

STATION_PATH = "../data/intermediate/noaa-requests/stations.json"


def main():

    with open(STATION_PATH, "r", encoding="utf-8") as f:
        stations = json.load(f)

    download_request_cfg = noaapy.download.DownloadDataConfig(
        stations=stations,
        datum="MSL",
        products=["water_level", "predictions"],
        date_range=pd.Interval(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31")),
    )
    data, not_found = noaapy.download.download(
        download_request_cfg=download_request_cfg,
        stations=stations,
    )

    save_path = "../data/intermediate/noaa-requests/noaa_data.csv"
    # data[0].to_csv(save_path, index=False)

    print("Station List:", station_list)
    print("Downloaded Data:", data)
    print("Not Found Stations:", not_found)


if __name__ == "__main__":
    main()

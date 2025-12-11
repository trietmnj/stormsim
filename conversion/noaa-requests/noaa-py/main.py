# conversion/noaa-requests/noaa-py/main.py
import pandas as pd

import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/
# https://tidesandcurrents.noaa.gov/api-helper/url-generator.html


def main():
    station_list_build_cfg = noaapy.station_list.StationListBuildConfig(
        selection_type=1,
        station_ids=["9414290"],
        include_historical=True,
    )
    station_list = noaapy.station_list.build(station_list_build_cfg)
    stations = {s["id"]: s for s in station_list}  # convert to dict for easy ref

    download_request_cfg = noaapy.download.DownloadDataConfig(
        station_ids=["9414290"],
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

# noaa-requests/noaa-py/main.py
from dataclasses import dataclass
from typing import List, Optional

import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/


def main():
    download_data_cfg = noaapy.download.DownloadDataConfig(
        station_ids=["9414290"],
        datum="MSL",
        prod=["Verified Monthly Mean Water Level"],
        op_mode="full_record",  # Full record
        d_beg=None,  # Not used in full record mode
        d_end=None,  # Not used in full record mode
    )
    station_list_build_cfg = noaapy.station_list.StationListBuildConfig(
        selection_type=1,
        station_ids=["9414290"],
        include_historical=True,
    )
    station_list = noaapy.station_list.build(station_list_build_cfg)

    data, not_found = noaapy.download.download(
        download_data_cfg=download_data_cfg,
        station_list=station_list,
    )
    save_path = "../data/intermediate/noaa-requests/noaa_data.csv"
    data[0].to_csv(save_path, index=False)

    print("Downloaded Data:", data)
    print("Not Found Stations:", not_found)


if __name__ == "__main__":
    main()

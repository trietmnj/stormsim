# conversion/noaa-requests/noaa-py/main.py
import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/


def main():
    station_list_build_cfg = noaapy.station_list.StationListBuildConfig(
        selection_type=1,
        station_ids=["9414290"],
        include_historical=True,
    )
    station_list = noaapy.station_list.build(station_list_build_cfg)


    download_data_cfg = noaapy.download.DownloadDataConfig(
        station_ids=["9414290"],
        datum="MSL",
        products=["Verified Monthly Mean Water Level"],
        start_date=None,  # Not used in full record mode
        end_date=None,  # Not used in full record mode
    )
    data, not_found = noaapy.download.download(
        download_data_cfg=download_data_cfg,
        station_list=station_list,
    )

    save_path = "../data/intermediate/noaa-requests/noaa_data.csv"
    # data[0].to_csv(save_path, index=False)

    print("Station List:", station_list)
    print("Downloaded Data:", data)
    print("Not Found Stations:", not_found)


if __name__ == "__main__":
    main()

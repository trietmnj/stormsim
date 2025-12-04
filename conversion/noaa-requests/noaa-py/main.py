# noaa-requests/noaa-py/main.py
import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/

if __name__ == "__main__":
    id_list = ["9414290"]  # station ids
    requested_datum = "MSL"
    prod = ["Verified Monthly Mean Water Level"]
    op_mode = "full_record"  # Full record
    d_beg = None  # Not used in full record mode
    d_end = None  # Not used in full record mode

    station_list_build_cfg = noaapy.station_list.StationListBuildConfig(
        selection_type=1,
        station_ids=["9414290"],
        include_historical=True,
    )
    station_list = noaapy.station_list.build(station_list_build_cfg)

    # Call the downloader function
    downloaded_data, not_found = noaapy.download(
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

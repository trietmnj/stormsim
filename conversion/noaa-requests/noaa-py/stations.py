# conversion/noaa-requests/noaa-py/main.py
import json

import noaapy

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/
# https://tidesandcurrents.noaa.gov/api-helper/url-generator.html


# 2 data pieces needed from the NOAA CO-OPS API for each storm event:
# 1. Contribution from tides - interpolated mapped to the time step as the hydrograph
# 2. Steric adjustment - singular value


def main():
    """
    Find the relevant stations
    """
    station_list_build_cfg = noaapy.station_list.StationListBuildConfig(
        selection_type=1,
        station_ids=["9414290"],
        include_historical=True,
    )
    station_list = noaapy.station_list.build(station_list_build_cfg)
    stations: dict[str,dict] = {s["id"]: s for s in station_list}

    save_path = "../data/intermediate/noaa-requests/stations.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(stations, f)

if __name__ == "__main__":
    main()

# conversion/noaa-requests/noaa-py/main.py
import requests

# api docs
# https://api.tidesandcurrents.noaa.gov/api/prod/
# https://tidesandcurrents.noaa.gov/api-helper/url-generator.html

# This script downloads a specific data need:
# Contribution from tides - interpolated mapped to the time step as the hydrograph


STATION_IDS = ["9414290"]
START_DATE = "2023-01-01"
END_DATE = "2027-01-31"
DATUM = "MSL"
SAVE_FOLDER = "../data/intermediate/noaa-requests/"


def main():

    for id in STATION_IDS:
        print(f"Preparing to download data for station ID: {id}")
        url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?begin_date={START_DATE.replace('-', '')}"
        f"&end_date={END_DATE.replace('-', '')}"
        f"&station={id}"
        "&product=predictions"
        f"&datum={DATUM}"
        "&time_zone=gmt"
        "&units=english"
        "&format=csv"
    )

    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()

    out_path = SAVE_FOLDER + f"tide_prediction_{id}_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}.csv"
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()

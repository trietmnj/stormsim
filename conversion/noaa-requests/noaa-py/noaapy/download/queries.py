from __future__ import annotations

import requests


def get_available_datums(station_id: str) -> list(str):
    data = requests.get(
        f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}/datums.json"
    ).json()
    return [d["name"] for d in data["datums"]]

# https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=historicwl

import csv
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import requests


BASE_STATION_URL = "https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json"
HIST_URL = BASE_STATION_URL + "?type=historicwl"
ACTIVE_URL = BASE_STATION_URL + "?type=waterlevels"

##### station_list example
# {
#     "count": 301,
#     "units": null,
#     "stations": [
#         {
#             "tidal": true,
#             "greatlakes": false,
#             "shefcode": "NWWH1",
#             "details": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/details.json"
#             },
#             "sensors": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/sensors.json"
#             },
#             "floodlevels": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/floodlevels.json"
#             },
#             "datums": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/datums.json"
#             },
#             "supersededdatums": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/supersededdatums.json"
#             },
#             "harmonicConstituents": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/harcon.json"
#             },
#             "benchmarks": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/benchmarks.json"
#             },
#             "tidePredOffsets": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/tidepredoffsets.json"
#             },
#             "ofsMapOffsets": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/ofsmapoffsets.json"
#             },
#             "state": "HI",
#             "timezone": "HAST",
#             "timezonecorr": -10,
#             "observedst": false,
#             "stormsurge": false,
#             "nearby": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/nearby.json"
#             },
#             "forecast": false,
#             "outlook": true,
#             "HTFhistorical": true,
#             "HTFmonthly": true,
#             "nonNavigational": false,
#             "id": "1611400",
#             "name": "Nawiliwili",
#             "lat": 21.9544,
#             "lng": -159.3561,
#             "affiliations": "NWLON",
#             "portscode": null,
#             "products": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/products.json"
#             },
#             "disclaimers": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/disclaimers.json"
#             },
#             "notices": {
#                 "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400/notices.json"
#             },
#             "self": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/1611400.json",
#             "expand": "details,sensors,floodlevels,datums,harcon,tidepredoffsets,ofsmapoffsets,products,disclaimers,notices",
#             "tideType": "Mixed",
#         },
#         ...,
#     ],
# }
#


@dataclass
class StationListBuildConfig:
    """
    Fields
    ------
    selection_type : int
        0 = all stations
        1 = by station ID(s)
        2 = by state(s)
        3 = inside polygon from CSV file
        4 = inside polygon from coordinates
    station_ids : list[str] | None
        Used when selection_type == 1.
    states : list[str] | None
        Used when selection_type == 2.
    csv_poly_path : str | None
        Used when selection_type == 3.
    x_poly, y_poly : list[float] | None
        Used when selection_type == 4.
    include_historical : bool
        If False, only return active stations.
    """

    selection_type: int = 0
    station_ids: Optional[List[str]] = None
    states: Optional[List[str]] = None
    csv_poly_path: Optional[str] = None
    x_poly: Optional[List[float]] = None
    y_poly: Optional[List[float]] = None
    include_historical: bool = True


def build(config: StationListBuildConfig, timeout: int = 300) -> List[Dict[str, Any]]:
    """
    Parameters
    ----------
    config : ToolConfig
        Selection and filtering options.
    timeout : int, optional
        HTTP timeout in seconds for NOAA requests (default 300).

    Returns
    -------
    station_inventory : list of dict
        Each dict is a NOAA station record with an extra key:
        - 'active_index' : 'active' or 'historical'
    """
    # 1) Fetch and merge inventories
    hist, active = _fetch_station_inventory(timeout=timeout)
    stations = _merge_and_mark_active(hist, active)

    # 2) Select indices based on config
    indices = _select_station_indices(stations, config)
    station_inventory = [stations[i] for i in indices]

    # 3) Optionally filter out historical stations
    if not config.include_historical:
        station_inventory = [
            s for s in station_inventory if s.get("active_index") == "active"
        ]

    return station_inventory


def _fetch_station_inventory(
    timeout: int = 300,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch historical and active station inventories from NOAA."""
    hist_resp = requests.get(HIST_URL, timeout=timeout)
    hist_resp.raise_for_status()
    hist = hist_resp.json()["stations"]

    active_resp = requests.get(ACTIVE_URL, timeout=timeout)
    active_resp.raise_for_status()
    active = active_resp.json()["stations"]

    return hist, active


def _merge_and_mark_active(
    hist: List[Dict[str, Any]],
    active: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge historical + active inventories and mark each station
    with 'active_index' = 'active' or 'historical'.
    """
    stations_by_id: Dict[str, Dict[str, Any]] = {s["id"]: s for s in hist}

    # Add any active stations missing from historical inventory
    for s in active:
        if s["id"] not in stations_by_id:
            stations_by_id[s["id"]] = s

    active_ids = {s["id"] for s in active}

    stations: List[Dict[str, Any]] = []
    for s in stations_by_id.values():
        s_copy = dict(s)  # shallow copy
        s_copy["active_index"] = (
            "active" if s_copy["id"] in active_ids else "historical"
        )
        stations.append(s_copy)

    return stations


def _points_in_polygon(
    x: np.ndarray,
    y: np.ndarray,
    xv: np.ndarray,
    yv: np.ndarray,
) -> np.ndarray:
    """
    Simple point-in-polygon test (ray casting algorithm).

    Parameters
    ----------
    x, y : array-like
        Coordinates of points to test.
    xv, yv : array-like
        Polygon vertex coordinates.

    Returns
    -------
    inside : np.ndarray of bool
        True where point is inside the polygon.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    xv = np.asarray(xv)
    yv = np.asarray(yv)

    nvert = len(xv)
    inside = np.zeros_like(x, dtype=bool)

    j = nvert - 1
    for i in range(nvert):
        xi, yi = xv[i], yv[i]
        xj, yj = xv[j], yv[j]

        # Check if the horizontal ray at y intersects edge (xi,yi)-(xj,yj)
        intersect = ((yi > y) != (yj > y)) & (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        inside ^= intersect
        j = i

    return inside


def _select_station_indices(
    stations: List[Dict[str, Any]],
    cfg: StationListBuildConfig,
) -> List[int]:
    """Return indices of stations that satisfy the selection criteria."""
    if cfg.selection_type == 0:
        # All stations
        return list(range(len(stations)))

    if cfg.selection_type == 1:
        # By station ID
        ids = cfg.station_ids or []
        id_to_idx = {s["id"]: i for i, s in enumerate(stations)}
        return [id_to_idx[station_id] for station_id in ids if station_id in id_to_idx]

    if cfg.selection_type == 2:
        # By state
        states = set(cfg.states or [])
        return [i for i, s in enumerate(stations) if s.get("state") in states]

    if cfg.selection_type == 3:
        # Inside polygon (from CSV)
        if not cfg.csv_poly_path:
            raise ValueError("csv_poly_path must be set for selection_type=3")

        xv: List[float] = []
        yv: List[float] = []
        with open(cfg.csv_poly_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                xv.append(float(row[0]))
                yv.append(float(row[1]))

        lons = np.array([s["lng"] for s in stations], dtype=float)
        lats = np.array([s["lat"] for s in stations], dtype=float)
        inside = _points_in_polygon(lons, lats, np.array(xv), np.array(yv))
        return list(np.where(inside)[0])

    if cfg.selection_type == 4:
        # Inside polygon (coordinates provided directly)
        if cfg.x_poly is None or cfg.y_poly is None:
            raise ValueError("x_poly and y_poly must be set for selection_type=4")

        lons = np.array([s["lng"] for s in stations], dtype=float)
        lats = np.array([s["lat"] for s in stations], dtype=float)
        inside = _points_in_polygon(
            lons, lats, np.array(cfg.x_poly), np.array(cfg.y_poly)
        )
        return list(np.where(inside)[0])

    raise ValueError(f"Unknown selection_type: {cfg.selection_type}")

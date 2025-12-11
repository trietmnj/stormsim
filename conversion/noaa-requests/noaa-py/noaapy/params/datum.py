from __future__ import annotations

from typing import Any, List, Tuple
import requests


NO_TIDAL_TEXT = "No Tidal Predictions"


def get_datum(
    station: dict(str, Any),
    requested_datum: str,
) -> Tuple[str, str, bool]:
    """
    Returns:
      datum     – main water-level datum (observations)
      datum_p   – prediction datum
      valid_pred     – True when IGLD / No Tidal Predictions logic is applied
    """

    datum_names = _get_available_datums(station["id"])

    # --- Prediction datums (may be list or string) ---
    preds = station.get("datums_predictions")
    is_tidal = station["tidal"]
    if isinstance(preds, list):
        pred_names = [d["name"] for d in preds]
        is_tidal = False
    else:
        pred_names = []
        is_tidal = preds and NO_TIDAL_TEXT in preds

    # --- Preference order depends on requested NAVD vs MSL family ---
    if "NAVD" in requested_datum:
        preferred_main = ["GL_LWD", "NAVD88", "MSL", "MLLW"]
        preferred_pred = ["NAVD88", "MSL", "MLLW"]
    else:
        preferred_main = ["GL_LWD", "MSL", "MLLW", "NAVD88"]
        preferred_pred = ["MSL", "MLLW", "NAVD88"]

    # --- Great Lakes or no tidal predictions → override everything ---
    if station.get("greatlakes", False) or is_tidal or "GL_LWD" in datum_names:
        return "IGLD", NO_TIDAL_TEXT, True

    # --- Normal case: choose best available ---
    datum_val = _pick_preferrence_datum(preferred_main, datum_names, default="STND")

    datum_p = (
        _pick_preferrence_datum(
            preferred_pred, pred_names, default="Preferred Datums Not Found"
        )
        if pred_names
        else "Preferred Datums Not Found"
    )

    return datum_val, datum_p, False


# --- Helper to pick the first available preferred datum ---
def _pick_preferrence_datum(
    preferred: List[str], available: List[str], default: str
) -> str:
    return next((p for p in preferred if p in available), default)


def _get_available_datums(station_id: str) -> list(str):
    data = requests.get(
        f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}/datums.json"
    ).json()
    return [d["name"] for d in data["datums"]]

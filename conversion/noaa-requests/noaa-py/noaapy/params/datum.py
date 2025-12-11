from typing import Any, Dict, List, Tuple


def get_datum(
    station: Dict[str, Any],
    requested_datum: str,
) -> Tuple[str, str, bool]:
    """
    Choose:
      - datum: main water-level datum
      - datum_p: prediction datum
      - flag2: True if IGLD / no tidal predictions branch used

    d_struct["datums"]:
        list of {"name": <datum_name>}
    d_struct["datums_predictions"]:
        either list of {"name": <datum_name>}
        or a string message like "No Tidal Predictions".
    """

    # --- Extract names from main datums ---
    datum_names = [d["name"] for d in station.get("datums", [])]

    # --- Extract prediction datums OR detect "no tidal predictions" text ---
    pred_names: List[str] = []
    no_tidal_predictions = False

    preds = station.get("datums_predictions")

    if isinstance(preds, list):
        # Normal case: list of dicts with "name"
        pred_names = [d["name"] for d in preds]
    elif isinstance(preds, str):
        # Text note case
        no_tidal_predictions = (
            "Great Lakes Gauge. No Tidal Predictions" in preds
            or "No Tidal Predictions" in preds
        )

    # --- Decide preference order based on requested_datum ---
    if "NAVD" in requested_datum:
        preferred_main = ["GL_LWD", "NAVD88", "MSL", "MLLW"]
        preferred_pred = ["NAVD88", "MSL", "MLLW"]
    else:
        preferred_main = ["GL_LWD", "MSL", "MLLW", "NAVD88"]
        preferred_pred = ["MSL", "MLLW", "NAVD88"]

    # --- Check for Great Lakes / IGLD logic ---
    has_gl_lwd = "GL_LWD" in datum_names

    if has_gl_lwd or no_tidal_predictions:
        # Great Lakes or explicitly no tidal predictions:
        # force IGLD / No Tidal Predictions
        datum_val = "IGLD"
        datum_p = "No Tidal Predictions"
        flag2 = True
        return datum_val, datum_p, flag2

    # --- Otherwise: pick best matching datum from available names ---
    def first_match(preferred: List[str], available: List[str], default: str) -> str:
        for name in preferred:
            if name in available:
                return name
        return default

    datum_val = first_match(preferred_main, datum_names, default="STND")

    # For predictions, only if we *do* have prediction names
    if pred_names:
        datum_p = first_match(
            preferred_pred,
            pred_names,
            default="Preferred Datums Not Found",
        )
    else:
        datum_p = "Preferred Datums Not Found"

    flag2 = False
    return datum_val, datum_p, flag2

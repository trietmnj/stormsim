from dataclasses import dataclass


@dataclass
class PredictionInterval:
    interval: str
    message_or_flag: str | bool


def get_prediction_interval(station, flag1, flag2):
    """
    Returns:
      interval (str)
      message_or_flag (str or bool)

    Logic:
      - If flag2 is True → no tidal predictions available.
      - If station['datums_predictions'] is not a list → we must determine
        interval from station['predictions_products'].
      - Otherwise → return "No Tidal Predictions".
    """

    # Case: Great Lakes or explicitly no tidal predictions
    if flag2 or not isinstance(station.get("datums_predictions"), list):
        # Available prediction intervals for this station
        available = [p["value"] for p in station.get("predictions_products", [])]

        # Preferred order depends on flag1
        if flag1 in ["1", "m"]:
            preferred = ["h", "30", "15", "6", "1"]
        else:
            preferred = ["6", "1", "15", "30", "h"]

        # Pick first matching interval
        for interval in preferred:
            if interval in available:
                return interval, False

        # No match → fall back to hilo
        return "hilo", f"Station {station['id']} is using hilo interval"

    # Not a prediction station / no list of datums available
    return "No Tidal Predictions", "No Tidal Predictions"

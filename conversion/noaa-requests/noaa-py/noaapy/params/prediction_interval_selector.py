def get_prediction_interval(d_struct, flag1, flag2):
    if not flag2 and not isinstance(d_struct["datums_predictions"], list):
        dummy = [prediction["value"] for prediction in d_struct["predictions_products"]]
        dummy2 = (
            ["h", "30", "15", "6", "1"]
            if flag1 in ["1", "m"]
            else ["6", "1", "15", "30", "h"]
        )

        chk2 = [sum(pred == d for d in dummy) for pred in dummy2]

        for pred, match in zip(dummy2, chk2):
            if match:
                return pred, False

        return "hilo", f"Station {d_struct['id']} is using hilo interval"

    return "No Tidal Predictions", "No Tidal Predictions"

from .HydroManipulator import HydroManipulator as hm
import pandas as pd
import numpy as np

# Instantiate Class
obj = hm()
# Define LC File ANd Headers
lc_file = "LC_dummy_data.txt"
data_headers = [
    "stormID",
    "number_of_tstps",
    "timestep",
    "event_date",
    "surge",
    "hm0",
    "period",
    "wDir",
    "dt",
    "sim_year",
]
slr = 1.5

# Parse LC Data
lc_data = obj.parse_lc(lc_file, data_headers)
# Pull First Timestep For Each Event In LC
events = lc_data[lc_data["timestep"] == 0]
# Create Tidal Signal For Each Event (Tidal Predictions)

row_ctr = np.array(0)  # Initialize Row Counter
for ii in range(0, events.shape[0]):
    # Pull From NOAA API , Assumes Data Is Available
    if ii == 0:
        tide_event = obj.get_tidal_prediction(
            "8735180",
            events["event_date"].values[ii],
            lc_data["event_date"].values[
                np.array(ii - 1) + events["number_of_tstps"].values[ii]
            ],
            "MSL",
        )
        tide_df = tide_event
        row_ctr = row_ctr + events["number_of_tstps"].values[ii] - np.array(1)
    else:
        row_ctr = row_ctr + events["number_of_tstps"].values[ii]
        tide_event = obj.get_tidal_prediction(
            "8735180",
            events["event_date"].values[ii],
            lc_data["event_date"].values[row_ctr],
            "MSL",
        )
        tide_df = pd.concat([tide_df, tide_event], ignore_index=True)
# Apply Tidal Signal To Surge
surge_w_tides = obj.add_tides(lc_data["surge"].values, tide_df["Prediction"].values)
# Apply SLR
surge_w_slr = obj.add_slr(lc_data["surge"].values, slr)

import numpy as np
import json
import pandas as pd
import os
import sys
import warnings
# Add To Path (this is temporary, ensures main.py can run in current hierarchy)
# 1. Get the path to current file (main.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Go UP one level to 'project_root'
project_root = os.path.dirname(current_dir)
# 3. Add root to path
sys.path.append(project_root)
# Import StormSim Packages
from classes.eurotop.runup_and_ot_eurotop_2018 import runup_and_ot_eurotop_2018
from classes.utilities.csv_utils import split_df_on_zero, write_dict_to_csv, write_dicts_to_csv

# Define Local Methods 
def resolve_input_paths(config):
    lc_path = config["lc_data"]

    if os.path.isfile(lc_path):
        config["single_file"] = True
        return [lc_path], config["outpath"]

    if os.path.isdir(lc_path):
        config["single_file"] = False
        subfol = os.path.basename(lc_path)
        outfol = os.path.join(config["outpath"], subfol)

        files = [
            os.path.join(lc_path, f)
            for f in os.listdir(lc_path)
            if f.lower().endswith(".csv")
        ]
        return files, outfol

    raise FileNotFoundError(f"Invalid lc_data path: {lc_path}")

#----------------- INPUTS FOR MAIN.PY ----------------------
EURO_CONFIG = "../config-files/eurotop_run_config.json"
OUTPUT_COL_ORDER = [
    "date", "storm_id", "lifecycle", "runup", "overtopping_rate",
    "overtopping_volume", "stage"
]
#-----------------------------------------------------------

def main():
    warnings.filterwarnings("ignore")
    print("\n=== EUROTOP PROCESSING STARTED ===")

    config = json.load(open(EURO_CONFIG, "r"))[0]

    file_to_process, outfol = resolve_input_paths(config)
    os.makedirs(outfol, exist_ok=True)

    pse_config = json.load(open(config["pse_geometry"], "r"))
    s_v_file = pd.read_csv(config["stage_vol_file"])

    print(f"Files to process: {len(file_to_process)}")
    print(f"Output folder: {outfol}")

    for lc_file in file_to_process:
        process_lc_file(lc_file, config, pse_config, s_v_file, outfol)

    print("\n=== ALL PROCESSING COMPLETE ===\n")


# ---------------------------------------------------------
# Compute storm metrics (q, R2p, Q, stage)
# ---------------------------------------------------------
def compute_storm_response(stm, args, pse_config, s_v_file):
    # Prepare forcing fields
    SWL  = stm["water_elevation"].to_numpy()
    Hm0  = stm["wave_height"].to_numpy()
    Tm10 = stm["wave_peak_period"].to_numpy()

    args["SWL"]  = SWL
    args["Hm0"]  = Hm0
    args["Tm10"] = Tm10

    # ---------------------------------------------------------
    # EARLY EXIT: If any forcing contains NaN → return NaN outputs
    # ---------------------------------------------------------
    if (
        np.isnan(SWL).any() or
        np.isnan(Hm0).any() or
        np.isnan(Tm10).any()
    ):
        storm_id = int(stm["storm_id"].iloc[0])
        return {
            "storm_id": storm_id,
            "overtopping_rate": np.nan,
            "runup": np.nan,
            "overtopping_volume": np.nan,
            "stage": np.nan,
            "lifecycle": stm["lifecycle"],
            "date": stm["date"].to_numpy()
        }

    # ---------------------------------------------------------
    # Run Eurotop
    # ---------------------------------------------------------
    A = runup_and_ot_eurotop_2018(args)
    A.structure_response()

    # ---------------------------------------------------------
    # Compute dt
    # ---------------------------------------------------------
    dates = stm["date"].to_numpy().astype("datetime64[s]")
    dt = np.unique(np.diff(dates).astype("timedelta64[s]").astype(int))[0]

    # ---------------------------------------------------------
    # Compute Q
    # ---------------------------------------------------------
    Q_val = np.sum(A.q) * dt * pse_config["protection_length"]

    # ---------------------------------------------------------
    # Compute Stage
    # ---------------------------------------------------------
    stage_val = np.interp(
        Q_val,
        s_v_file.iloc[:, 0].to_numpy(),
        s_v_file.iloc[:, 1].to_numpy()
    )

    # ---------------------------------------------------------
    # Extract storm_id
    # ---------------------------------------------------------
    storm_id = int(stm["storm_id"].iloc[0])

    return {
        "storm_id": storm_id,
        "overtopping_rate": A.q.copy(),
        "runup": A.R2p.copy(),
        "overtopping_volume": float(Q_val),
        "stage": float(stage_val),
        "lifecycle": stm["lifecycle"],
        "date": stm["date"].to_numpy()
    }

# ---------------------------------------------------------
# Process a single LC file (single storm or multi-storm)
# ---------------------------------------------------------
def process_lc_file(lc_file, config, pse_config, s_v_file, outfol):
    fname = os.path.basename(lc_file)
    print(f"\nREADING lc: {fname}")

    lc_data = pd.read_csv(lc_file)
    args = pse_config.copy()

    outname = os.path.join(
        outfol,
        fname.replace(".csv", "_responses.csv")
    )

    print("COMPUTING responses...")


    if config["single_file"]:
        stm_list = split_df_on_zero(lc_data, "hydro_tstp")
        results = [
            compute_storm_response(stm, args, pse_config, s_v_file)
            for stm in stm_list
        ]
        
        # Reorder columns
        results = [{k: res[k] for k in OUTPUT_COL_ORDER if k in res} for res in results]

        print(f"   {len(results)} storm segments processed")
        print("WRITING data...")
        write_dicts_to_csv(results, outname)

    else:
        results = compute_storm_response(lc_data, args, pse_config, s_v_file)
        
        # Reorder columns
        results = {k: results[k] for k in OUTPUT_COL_ORDER if k in results}

        print("WRITING data...")
        write_dict_to_csv(results, outname)

    print("PROCESSING FINISHED")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

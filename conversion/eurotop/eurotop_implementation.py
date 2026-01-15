import numpy as np
import json
import pandas as pd
import os
from datetime import datetime
import warnings
from HydroManipulator import HydroManipulator
from runup_and_ot_eurotop_2018_mod import runup_and_ot_eurotop_2018


# ---------------------------------------------------------
# Utility: Split DF into storm segments
# ---------------------------------------------------------
def split_df_on_zero(df, col):
    zero_idx = df.index[df[col] == 0].tolist()
    boundaries = zero_idx + [len(df)]
    return [df.iloc[zero_idx[i]:boundaries[i+1]] for i in range(len(zero_idx))]


# ---------------------------------------------------------
# Resolve input path (single file vs directory)
# ---------------------------------------------------------
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
def process_lc_file(lc_file, config, pse_config, s_v_file, hm, outfol):
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
        print(f"   {len(results)} storm segments processed")
        print("WRITING data...")
        hm.write_dicts_to_csv(results, outname)

    else:
        results = compute_storm_response(lc_data, args, pse_config, s_v_file)
        print("WRITING data...")
        hm.write_dict_to_csv(results, outname)

    print("PROCESSING FINISHED")

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    print("\n=== EUROTOP PROCESSING STARTED ===")

    euro_config = "eurotop_run_config.json"
    config = json.load(open(euro_config, "r"))[0]

    file_to_process, outfol = resolve_input_paths(config)
    os.makedirs(outfol, exist_ok=True)

    pse_config = json.load(open(config["pse_geometry"], "r"))
    s_v_file = pd.read_csv(config["stage_vol_file"])

    hm = HydroManipulator()

    print(f"Files to process: {len(file_to_process)}")
    print(f"Output folder: {outfol}")

    for lc_file in file_to_process:
        process_lc_file(lc_file, config, pse_config, s_v_file, hm, outfol)

    print("\n=== ALL PROCESSING COMPLETE ===\n")

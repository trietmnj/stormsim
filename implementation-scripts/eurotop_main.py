import numpy as np
import json
import pandas as pd
import os
import sys
import warnings
# Import StormSim Packages
from classes.eurotop.runup_and_ot_eurotop_2018 import runup_and_ot_eurotop_2018
from classes.utilities.csv_utils import split_df_on_zero, write_dict_to_csv, write_dicts_to_csv, merge_dicts
from classes.utilities.chs_utils import write_parquet

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
            if f.lower().endswith(".parquet")
        ]
        return files, outfol

    raise FileNotFoundError(f"Invalid lc_data path: {lc_path}")

#----------------- INPUTS FOR MAIN.PY ----------------------
EURO_CONFIG = "config-files/eurotop_run_config.json"
OUTPUT_COL_ORDER = [
    "location_id", "date", "storm_id", "lifecycle", "runup", "overtopping_rate",
    "overtopping_volume", "stage"
]
STAGE_OUTPUT_COL_ORDER = [
    "location_id", "date", "storm_id", "lifecycle", "stage"
]

#-----------------------------------------------------------

def main():
    warnings.filterwarnings("ignore")
    print("\n=== EUROTOP PROCESSING STARTED ===")

    config = json.load(open(EURO_CONFIG, "r"))[0]

    file_to_process, outfol = resolve_input_paths(config)
    

    pse_config = json.load(open(config["pse_geometry"], "r"))
    s_v_file = pd.read_csv(config["stage_vol_file"])

    print(f"Files to process: {len(file_to_process)}")
    print(f"Output folder: {outfol}")

    # Assuming 1 Savepoint Per Reach 
    # All transects will use the same forcing data for now 
    for lc_file in file_to_process:
        for pse_xsec in pse_config:
            # Make Sure Each Transect Has Its Own Folder 
            config["outpath"] = os.path.join(outfol, pse_xsec["name"]) 
            os.makedirs(config["outpath"], exist_ok=True)
            process_lc_file(lc_file, config, pse_xsec, s_v_file, config["outpath"])

    print("\n=== ALL PROCESSING COMPLETE ===\n")


# ---------------------------------------------------------
# Compute storm metrics (q, R2p, Q, stage)
# ---------------------------------------------------------
def compute_storm_response(stm, args, pse_config, s_v_file):
    # Prepare forcing fields
    SWL  = stm["water_elevation"].to_numpy()
    Hm0  = stm["wave_height"].to_numpy()
    Tm10 = stm["wave_peak_period"].to_numpy()
    # ------------ This is temporary 
    stm["location_id"] = 1
    #----------------
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
        #storm_id = int(stm["storm_id"].iloc[0])
        storm_id = stm["storm_id"].to_numpy()
        return {
            "location_id": stm["location_id"].to_numpy() if hasattr(stm, "to_numpy") else stm["location_id"],
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
    if pse_config["type"] == 0:
        # G2 Approach 
        # stage_val = swl + 0.7*Ks*np.min([1.12*Hm0, 0.55*ds])
        # 0.7*Hc = 1.12*Hm0
        # 0.7*Hb = 0.55*ds
        # Grab Ks Value 
        # Shielding From Rows Of Buildings 
        # Stage Scaling Factor For No PSE Option 
        # Ks = 1 for 0 - 1 rows 
        # Ks = 0.7 for 2 - 3 rows 
        # Ks = 0.5 for 4 - 5 rows 
        # Ks = 0.3 for >=6 rows 
        if "Ks" in pse_config.keys():
            Ks = pse_config["Ks"]
        else: # Default to Ks=1 if none provided
            Ks = 1
        # Compute Water Depth
        ds = args["SWL"] - pse_config["toe_elevation"]
        # Compute Stage 
        stage_val = args["SWL"] + 0.7*Ks*np.min([1.12*args["Hm0"], 0.55*ds])
        # Set Other Fields To Null 
        Q_val = np.zeros_like(stage_val)
        R2p = np.zeros_like(stage_val)
        #
        storm_id = stm["storm_id"].to_numpy()
        return {
                "location_id": stm["location_id"].to_numpy() if hasattr(stm, "to_numpy") else stm["location_id"],
                "storm_id": storm_id,
                "overtopping_rate": np.zeros_like(stage_val),
                "runup": np.zeros_like(stage_val),
                "overtopping_volume": np.zeros_like(stage_val),
                "stage": stage_val,
                "lifecycle": stm["lifecycle"],
                "date": stm["date"].to_numpy()
            }
    else:
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
        Q_val = np.cumsum(A.q) * dt * pse_config["protection_length"]

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
        #storm_id = int(stm["storm_id"].iloc[0])
        storm_id = stm["storm_id"].to_numpy()
        return {
            "location_id": stm["location_id"].to_numpy() if hasattr(stm, "to_numpy") else stm["location_id"],
            "storm_id": storm_id,
            "overtopping_rate": A.q.copy(),
            "runup": A.R2p.copy(),
            "overtopping_volume": Q_val,
            "stage": stage_val,
            "lifecycle": stm["lifecycle"],
            "date": stm["date"].to_numpy()
        }

# ---------------------------------------------------------
# Process a single LC file (single storm or multi-storm)
# ---------------------------------------------------------
def process_lc_file(lc_file, config, pse_config, s_v_file, outfol):
    fname = os.path.basename(lc_file)
    print(f"\nREADING lc: {fname}")

    #lc_data = pd.read_csv(lc_file)
    lc_data = pd.read_parquet(lc_file)
    args = pse_config.copy()

    base_outname = fname.replace(".parquet", "_responses.parquet").replace("EventDate_LC_", "")
    outname = os.path.join(outfol, base_outname)
    stage_outname = os.path.join(outfol, "stage_" + base_outname)

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

        aa = merge_dicts(results)
        df_out = pd.DataFrame(aa)

        for (loc_id, lc), group in df_out.groupby(["location_id", "lifecycle"]):
            group_dict = group.to_dict(orient="list")

            loc_base_outname = base_outname.replace(".parquet", f"_loc_{loc_id}_lc_{lc}.parquet")
            loc_outname = os.path.join(outfol, loc_base_outname)
            stage_loc_outname = os.path.join(outfol, "stage_" + loc_base_outname)

            write_parquet(loc_outname, group_dict)

            stage_results = {k: group_dict[k] for k in STAGE_OUTPUT_COL_ORDER if k in group_dict}
            write_parquet(stage_loc_outname, stage_results)

    else:
        results = compute_storm_response(lc_data, args, pse_config, s_v_file)

        # Reorder columns
        results = {k: results[k] for k in OUTPUT_COL_ORDER if k in results}

        print("WRITING data...")
        df_out = pd.DataFrame(results)

        for (loc_id, lc), group in df_out.groupby(["location_id", "lifecycle"]):
            group_dict = group.to_dict(orient="list")

            loc_base_outname = base_outname.replace(".parquet", f"_loc_{loc_id}_lc_{lc}.parquet")
            loc_outname = os.path.join(outfol, loc_base_outname)
            stage_loc_outname = os.path.join(outfol, "stage_" + loc_base_outname)

            write_parquet(loc_outname, group_dict)

            # Reorder columns
            stage_results = {k: group_dict[k] for k in STAGE_OUTPUT_COL_ORDER if k in group_dict}
            write_parquet(stage_loc_outname, stage_results)

    print("PROCESSING FINISHED")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

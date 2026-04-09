import json
import pandas as pd
import os
import sys
import warnings

# Import StormSim Packages
from stormsim.eurotop.processing import process_lc_file

#----------------- INPUTS FOR MAIN.PY ----------------------
EURO_CONFIG = "config-files/eurotop_run_config.json"

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
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
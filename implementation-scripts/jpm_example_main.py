import numpy as np
import os
import pandas as pd
import pyarrow as pa
from stormsim.hazard_curves import jpm
from stormsim.hydrograph_manipulator.HydroManipulator import HydroManipulator
from stormsim.utilities.chg_utils import get_aef, prep_frequency

# --------------------------
# DEFINE INPUTS
#---------------------------
# Output folder
out_folder = r"./data/outputs/jpm_demo"
input_folder = r"./data/jpm_demo/"

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------


def main():

    # Initialize HM Class
    hm=HydroManipulator()
    
    # --------------
    # Load data
    #---------------
    # Save Points To Process 
    study_grid = pd.read_parquet(os.path.join(input_folder,"savepoint_list.parquet"))
    
    # Grab Reduced Storm Suite Peak Responses
    Resp = pd.read_parquet(os.path.join(input_folder,"savepoints_tc_swl_peaks.parquet"))
    dsw = pd.read_parquet(os.path.join(input_folder,"tc_dsw.parquet"))["dsw"].to_numpy()
    # Create Dummy Storm IDs , Need to replcae with the actual values
    storm_ids = np.arange(1, Resp.shape[0]+1) # This is Dummy Value For Now 
    # Grab BenchMark HCs 
    bench_hc = pd.read_parquet(os.path.join(input_folder,"savepoints_tc_swl_hazards.parquet"))

# --------------------
# Process Savepoints (Call JPM)
# --------------------
    # Loop Through SPs
    for ii, sp in enumerate(study_grid["sp_id"].to_numpy().astype(int)):  
        print(f"Processing save point: {sp} ({ii+1}/{bench_hc.shape[1]})")
        # Create Output Directory
        out_dir = os.path.join(out_folder, f"sp{sp.astype(int)}")
        os.makedirs(out_dir, exist_ok=True)
        
        #----------------
        # Step 1: Prep Modeling Data
        # ------------  
        sp_col = f"sp_{sp}"

        # Apply Bias Correction
        sp_resp = hm.correct_bias(Resp[sp_col].to_numpy(),
            study_grid.loc[study_grid["sp_id"] == sp, "ba"].to_numpy(),
            study_grid.loc[study_grid["sp_id"] == sp, "br"].to_numpy()
                                )
        
        # Grab Benchmark HC
        sp_bench_hc = np.sort(bench_hc[sp_col].to_numpy())[::-1]

        #----------------
        # Step 2: Create JPM Input Parquet
        # ---------------
        # Headers: ['datetime', 'response_wo_tides', 'response_skew_tides', 'discrete_storm_weights']
        
        # -------- READ ME --------------
        # In This Example We Are Using A sub-set dataset for the input files. All datasets contain
        # 30 savepoints & 80 TCs. Savepoint ID file defines what savepoint each row represents on the other files
        # (peaks, hazards .csv). On real application files will contain data from full grid and we need to search 
        # for the row index of the requested savepoint by using the grid for the study.
        # --------------------------------
        
        # Define Dummy Datetime Data 
        dtime = np.zeros_like(sp_resp)
        # Define No Skew Tides 
        no_skew = np.zeros_like(sp_resp)
        # Build JPM Data Input 
        jpm_in = np.column_stack([np.zeros_like(sp_resp), sp_resp, np.zeros_like(sp_resp), dsw.flatten()])
        # Define Schema
        schema = [
            ("datetime", pa.float32()),
            ("response_wo_tides", pa.float32()),
            ("response_skew_tides", pa.float32()),
            ("discrete_storm_weights", pa.float32())]
        # Write Input Parquet 
        jpm.save_parquet(jpm_in, schema, os.path.join(out_dir, f"jpm_input.parquet"))

        # --------------------
        # Step 3: Define JPM Integration Options & Compute HC
        # -------------------
        # Integartion Methods: ITCS -> Use For Surge, Hm0, Tp | ATCS -> Use for other responses. You Need to supply the replicates (StormSim: PROS)
        # Define JPM Options
        opts = jpm.Options(
            flag_value=[],
            ua=study_grid.loc[study_grid["sp_id"] == sp, "ua"].iloc[0],
            ur=study_grid.loc[study_grid["sp_id"] == sp, "ur"].iloc[0],
            #    tide_std=0.1,
            integration_mode="ITCS",
            uncertainty_mode="combined",
            tide_mode="none",
            skewed=False,
            percentiles=[16, 84],
            output_path=out_dir,
            return_table=True,
            use_aep=False,
        )
        # Compute HC
        jpm.compute(os.path.join(out_dir, f"jpm_input.parquet"), 'response', opts, plt_opts=None)

        # --------------------
        # Step 4: Estimate TC Storm Suite AEF
        # -------------------
        # Create AEF Plot Vector (631 x 1) 
        plt_aef = prep_frequency()
        # Get Event Associated AEF
        ss_aef_map = get_aef(storm_ids,
            sp_resp,
            plt_aef,
            sp_bench_hc,
            dsw
            ) # stormID, aef, response
        # Define Schema For Parquet
        schema2 = [
        ("storm_id", pa.int32()),
        ("aef", pa.float32()),
        ("response", pa.float32())]
        # Write Out Peak Response To AEF Mapping
        jpm.save_parquet(np.column_stack(list(ss_aef_map.values())), schema2, os.path.join(out_dir, f"tc_storms_peak_aef.parquet"))



# ------------------------------------------------------------
# Script Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
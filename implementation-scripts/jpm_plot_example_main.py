import os 
import pandas as pd
from classes.hazard_curves import jpm, pst
from classes.utilities.chg_utils import plot_hc
import numpy as np
# ------------------
# Define Inputs
# ------------------
input_folder = r"./data/jpm_demo/"
out_folder = r"./data/outputs/jpm_demo"

def main():
    # --------------
    # 1. Load data
    #---------------
    # Save Points To Process 
    study_grid = pd.read_parquet(os.path.join(input_folder,"savepoint_list.parquet"))
    # Grab BenchMark HCs 
    bench_hc = pd.read_parquet(os.path.join(input_folder,"savepoints_tc_swl_hazards.parquet"))

    # Loop Through Each SP
    for ii, sp in enumerate(study_grid["sp_id"].to_numpy().astype(int)): # Will need to change this to mathcing SP position for full dataset
        print(f"Processing save point: {sp} ({ii+1}/{bench_hc.shape[1]})")
        # Define SP Path
        sp_col = f"sp_{sp}"
        out_dir = os.path.join(out_folder, f"sp{sp}")
        # ----------------
        # 2. Load In Peak Responses & Hazard Curves
        #---------------
        # Read In Reduce Set HC  
        reduced_hc =  pd.read_parquet(os.path.join(out_dir,"plot.parquet"))
        plt_aef = reduced_hc["aep"] # 631 x 1
        plt_be = reduced_hc["response"]
        # Get Response/AEF Mapping
        ss_aef_map =  pd.read_parquet(os.path.join(out_dir,"tc_storms_peak_aef.parquet"))
        # Get Benchmark HC
        sp_bench_hc = np.sort(bench_hc[sp_col].to_numpy())[::-1]
       
        # ----------------------
        # 3. Plot Reduced Storm Suite HC
        #---------------------
        # Plot Reduce Set  
        plt, ax , fig = plot_hc(np.column_stack([plt_aef, plt_be]),
            file_name = os.path.join(out_dir,"tc_swl_hc_comparison.png"),
            percentiles = None,
            ylabel = "Surge [m]",
            width = 8,
            height = 8,
            tick_fontsize = 13,
            label_fontsize = 14,
            legend_fontsize = 14,
            legend_location = "lower center",
            write_fig = False,
            dpi = 300)
        # ---------------------
        # 4. Add Benchmark Hazard Curve 
        # ---------------------
        ax.semilogx(plt_aef, sp_bench_hc, label=f"Benchmark", linestyle='--', color='black')
       
        #----------------------
        # 5. Plot Reduced Storm Suite (Peaks)
        #----------------
        plt.scatter(ss_aef_map["aef"], ss_aef_map['response'],s=10, 
            c="lime", 
            edgecolors="black", label="Selected Storms")
        
        #-------------
        # 6. Update Legend & Print Figure
        # ---------------
        plt.legend() # Update Legend
        handles, labels = ax.get_legend_handles_labels() # Grab Handles/Labels
        labels[0] = "Reduced SS" # Change Name For Mean
        ax.legend(handles, labels) # Updatge Legend With New Name
        # Print Figure 
        plt.savefig(os.path.join(out_dir,"tc_swl_hc_comparison.png"), dpi=300, bbox_inches="tight")
        plt.close()

# ------------------------------------------------------------
# Script Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
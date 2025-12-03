
# --------- Import Libraries
from runup_and_ot_eurotop_2018_mod import runup_and_ot_eurotop_2018
import numpy as np
import h5py
import os
import time
import pandas as pd


def main():
    print("RUNNING!")

# Missing pieces:
# Break Out Inputs To Be More Explicit (Vectors)
# Need to implement logic to set invalid responses to NaN instead of 0
# Stage Volume Relationship
# Compute Q For Each Storm
# Need To Add Rubble Mounds And Floodwalls
# Need to update slope logic and emp coefficients
# Need to Add Dates To Events In LC (Seasons: TC Season vs XC Season)
# Need to Bring In SRR's
    st_time = time.time()
# --------- User Inputs
# Define .mat To Import LCS Project Forcing .mat
    lcs_mat = '../data/raw/eurotop/Deer_Island_Alternative_A_Performance_LCS_project_forcing.mat'
# Define Stage Volume Relationship File
    s_v_file = '../data/raw/eurotop/dummy_stage_vol.csv'
# Define Protection Length
    protection_length = 1000 # m
# Define Storm Types
    st = 'CC'
# Define Data Type ('peaks' or 'timeseries')
    ds_type = 'timeseries'
# Define Eurotop Class Dictionary
# type -> 1-levee, 2-rubblemound, 3-floodwall
# seaward slope (Run/Rise) -> cot(alpha)
# type -> 1 - Design or Assesment Approach | 2 - Mean Value Approach
    args = {'type':1,
        'app_type':2,
        'crest_elevation':4.0,
        'toe_elevation':-1.0,
        'seaward_slope':8,
        'crest_width':3.5,
        'material':'grass', # Supported: 'grass', 'concrete', 'basalt' (Table 5.2)
        'SWL':np.array(5.5),
        'Hm0':np.array(1.65),
        'Tm10':np.array(4.5)
        }
# Define Output Directory
    out_dir = 'python_outputs'
# Create Directory
    if os.path.exists(out_dir):
        # Do Nothing
        pass
    else:
        os.mkdir(out_dir)
# Headers (Peaks)
# [ sim_year | stm_type | Order_In_Year | SSL | Hm0 | Tp | Wave_Direction | Storm ID ]
# Headers Timeseries
# [ Stm ID | Number of Timesteps | timestep (hr) | Timestamp (Modeled Date) | SWL | Hm0 | Tp | Wave Direction | dt | Simulation Year ]

# --------- Read In StormSim LCS Outputs
        # Define SS Dataset To Access
    if ds_type=='peaks':
            ds_name = '/Peaks/Maxima/LCNUM'
            cols_for_data = [3, 4, 5] # SWL, Hm0, Tp
    elif  ds_type=='timeseries':
            # Define SS Dataset To Access
            ds_name = '/Timeseries/LCNUM'
            cols_for_data = [4, 5, 6] # SWL, Hm0, Tp
    else:
        # Define SS Dataset To Access
        ds_name = '/Peaks/Maxima/LCNUM'
# Import .mat File
    ss_file = h5py.File(lcs_mat,'r')
# Get Storm Types In Data
    stm_type = list(ss_file["project_forcing"].keys())
# Get Number Of LC
    n_lc = max(ss_file['project_forcing/'+stm_type[0]+ds_name].shape)
# Import Stage Vol File
    df = pd.read_csv(s_v_file)

# --------- Loop Through Life Cycles
    for ii in range(n_lc):
        # Extract Life Cycle Data (Transpose To Match SS Format)
        lc_data = np.array(ss_file[ss_file['project_forcing/'+st+ds_name][0, ii]]).T
        # Get Number Of Rows
        lc_rows = lc_data.shape[0]
        # Intialize Response Storage Variable
        dummy_var = np.zeros((lc_rows, 2))
        # Define Eurotop Input Dictionary Event Info
        args["SWL"] = lc_data[:, cols_for_data[0]]
        args["Hm0"] = lc_data[:, cols_for_data[1]]
        args["Tm10"] = lc_data[:, cols_for_data[2]]
        # Feed Input Dictironary To Eurotop Class
        A=runup_and_ot_eurotop_2018(args)
        # Call Structure Response Method (R2% & q)
        A.structure_response()
        # Append Responses To Storage Rows
        dummy_var[:, 0] = A.R2p
        dummy_var[:, 1] = A.q
        q_vector = A.q
        # Compute Overtopping Discharge Volume (Q) For Each Storm Hydrograph
        if ds_type=='timeseries':
                # Find Number Of Events In LC
                stm_beg_indx = np.where(lc_data[:, 2] == 0)[0] # Grab Storm Initial Timestep
                stm_end_indx = stm_beg_indx + lc_data[stm_beg_indx, 1] - 1 # Find Row Index For Each Storm Hydrograph In LC
                stm_end_indx = stm_end_indx.astype(int)
                # Initialize Q With N Events (1 Entry Per Event)
                Q_per_event_in_LC = np.zeros((stm_end_indx.shape[0], 1))
                v_stage_per_lc = np.zeros((stm_end_indx.shape[0], 3))
                # Integrate q For Each Storm
                for ss in range(Q_per_event_in_LC.shape[0]):
                    Q_per_event_in_LC[ss, 0] = np.sum(dummy_var[stm_beg_indx[ss]:stm_end_indx[ss], 1])
                # Perform linear interpolation using numpy.interp
                interpolated_stages = np.interp(Q_per_event_in_LC[:]*protection_length, df[df.columns[0]].values, df[df.columns[1]].values)
                # Print Out LC Responses In CSV
                np.savetxt(os.path.join(out_dir,'lc_'+str(ii)+'_Eurotop_Q_response.csv'),
                           np.hstack([Q_per_event_in_LC, Q_per_event_in_LC[:]*protection_length, interpolated_stages]),
                             delimiter=',', fmt=['%.4e', '%.4e', '%.4e'], header='Q [m^3 per m], Q [m^3], Stage [m]' ) # Q [m^3 per m]


        # Print Out LC Responses In CSV
        np.savetxt(os.path.join(out_dir,'lc_'+str(ii)+'_Eurotop_responses.csv'), dummy_var, delimiter=',', fmt=['%.6f', '%.4e'], header='r2% [m],q [m^3/s per m]') # R2p | q [m] | [m^3/s per m]

    end_time = time.time()
    print(f"Total Elapsed time: {end_time - st_time:.2f} seconds")
    print(f"Elapsed time per LC: {(end_time - st_time)/n_lc:.2f} seconds")


if __name__ == "__main__":
    main()


%% FUNCTION INPUTS DOC
%{
SST Input Data Structures:

1. Input Data Specifications:

response_data.(XX), where XX respresents
    - data: N x 3 double data matrix, where each column represents:
        col 01: Event response MATLAB serial date (see datenum)
        col 02: Response data without tides
        col 03: Response data with tides (For POT Datatypes only, For Timeseries this is ignored)
    - flag_value: Flag value to remove from response data.  
    - lambda: mean annual rate of events (events/year). This is for Timeseries only. 
    - Nyrs: record length in years. This is for POT data types only.
    - SLC: magnitude of the sea level change implicit in the storm surge
    - DataType:'POT' or 'Timeseries'
    - gprMdl: Gaussian Process Regression model (GPR) trained with tidal data (See: https://www.mathworks.com/help/stats/fitrgp.html) 

2. Probabilistic Simulation Technique (PST) Specifications:

pst_options.(XX), where XX represents
    - tLag: inter-event time in hours. This is for Timeseries only and used for POT creation. 
    - GPD_TH_crit: indicator for specifying the GPD threshold option of the Mean Residual Life (MRL) selection process. 
                   Options are:
                        2) GPD_TH_crit = 1: to only evaluate the MRL threshold selected by the lambda criterion
                        3) GPD_TH_crit = 2: to only evaluate the MRL threshold selected by the minimum error criterion
    - ind_Skew: indicator for computing/adding skew tides to the storm surge (1-apply skew tides, 0-don't apply skew tides)
    - use_AEP: AEP vs AEF flag (1-Use AEP for HC frequencies, 0-Use AEF for HC frequencies)
    - prc: percentage values for computing the percentiles. Accepts a max of 4 values.
    - apply_GPD_to_SS: Force GPD Fit 
    - pst_options.stat_print: indicator to print script status (1-print steps, 0-don't print)
    
plot_options.(XX), where XX represents
    - create_plots: 
    - staID: Response variable name. 
    - yaxis_Label: Hazard curve y axis label
    - yaxis_Limits: Hazard curve y axis limits 
    - y_log: Hazard curve y axis scale switch (1-log, 0-linear)
    - path_out: Output path
%}

%% LOAD EXAMPLE DATA
% Add Dependencies
addpath('PST/');
% This is the use case for processing a Peaks Over Threshold Dataset
% Load CHS Timeseries Data
load('SSv1.0_Forced_Sta50_2195_CHS-NA_SP6021.mat');
% Define CHS Save Point Surge Absolute & Relative Uncertainty (Model Error)
Nyrs_XC = storm.XC.Nyrs_XC;
% Get Max Surge Value For Each Storm Event
surge_pot = cellfun(@(x) max(x(:, 1)), storm.XC.Timeseries.Default(:, 2)); % User Might Feed Dataset (N storms x M replicates)
% Compute Rows And Cols
[drows, dcols] = size(surge_pot);

%% CREATE INPUT DATA STRUCTURES
% PST
response_data = struct('data', [zeros(drows*dcols, 1) surge_pot(:) zeros(drows*dcols, 1)],...
    'flag_value', [], 'SLC', 0, ... %% config.swl_slr,...
    'lambda', [],'Nyrs', Nyrs_XC*dcols, 'gprMdl', [], 'DataType', 'POT');
% JPM Options
eva_options = struct('ind_Skew', 0, 'use_AEP', 0,...
    'prc', [16 84], 'stat_print', 0, 'tLag', 0, 'GPD_TH_crit', 2,...
    'apply_GPD_to_SS', 1, 'bootstrap_sims', 100);
% Plot Options
plot_options = struct('create_plots', 1,'staID', 'SSL', 'yaxis_Label', 'Surge [m]',...
    'yaxis_Limits', [], 'y_log', 0, 'path_out', '');

%% CREATE HAZARD CURVE
[PST_outputs] = StormSim_PST(response_data, eva_options, plot_options);

% Saving data for validation in Python
data = table2array(PST_outputs.MRL_output.Summary);
save("../tests/data/pst_summary.mat", '-v7', "data") 

% Don't need to check
%data = table2array(PST_outputs.MRL_output.Selection);
%save("../tests/data/pst_selection.mat", '-v7', "data")

data = PST_outputs.HC_plt_x;
save("../tests/data/pst_hc_plt_x.mat", '-v7', "data") 

data = PST_outputs.HC_plt;
save("../tests/data/pst_hc_plt.mat", '-v7', "data") 

data = table2array(PST_outputs.HC_emp);
save("../tests/data/pst_hc_emp.mat", '-v7', "data") 

data = PST_outputs.MRL_output.pd_k_wOut;
save("../tests/data/pst_pd_k_wOut.mat", '-v7', "data") 

data = PST_outputs.MRL_output.pd_k_mod;
save("../tests/data/pst_pd_k_mod.mat", '-v7', "data") 

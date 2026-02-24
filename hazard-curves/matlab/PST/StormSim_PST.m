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
    - response_data.DataType:'POT' or 'Timeseries'

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
function [SST_output] = StormSim_PST(response_data, pst_options, plot_options)
%% Other settings
if pst_options.stat_print == 1
    clc;
    disp(['***********************************************************' newline...
        '***         StormSim-SST Tool Alpha Version 0.5         ***' newline...
        '***                Release 1 - 20210809                 ***' newline...
        '***                 FOR  TESTING  ONLY                  ***' newline...
        '***********************************************************']);
    disp([newline '*** Step 1: Processing input arguments ']);
end

% Turn off all warnings
warning('off','all');

%% PARAMETER INITIALIZATION
% Error Handeling For Inputs
[response_data, pst_options, plot_options] = error_handeling(response_data, pst_options, plot_options);
% Define Output Path For PST
plot_options.('path_out') = fullfile(plot_options.('path_out'), 'PST_outputs');
% Check path to output folder
if ~exist(plot_options.('path_out'), 'dir') && plot_options.create_plots == 1
    mkdir(plot_options.('path_out'));
end
% Define Col Index To Include For Invalid Response Identification
if pst_options.ind_Skew == 1
    % include POT with Tides As Part Of QC
    col_indx = 3;
else
    % Ignore POT WIth Tides Col
    col_indx = 2;
end
% Pre-allocate output structure array
SST_output = struct('staID','','RL',double.empty,'POT',double.empty,'MRL_output',double.empty,...
    'HC_plt',double.empty,'HC_tbl',double.empty,'HC_tbl_rsp_x',double.empty,'HC_emp',double.empty,'Warning','','ME',cell(1));
if pst_options.stat_print == 1
    disp('*** Step 2: Verifying input datasets')
end

%% Data preprocessing: remove NaN, inf values; compute record length
% Grab Event Response Data
procData = response_data.data;

% Prep Processing Data
switch response_data.DataType
    case 'Timeseries'  %Timeseries
        % Remove Flag Values
        if ~isempty(response_data.('flag_value'))
            % Remove Flag Values
            procData(procData(:, 2) == response_data.('flag_value'), :) = [];
        end
        % Merge data and remove NaN, Inf values
        procData(isinf(procData(:,2)) | isnan(procData(:,2)), :) = [];
        % Compute record length: Effective duration method
        [dt(:,1),dt(:,2),dt(:,3)] = ymd(datetime(procData(:,1), 'ConvertFrom', 'datenum'));
        % Get Unique Rows
        dt = unique(dt,'rows');
        % Compute Number Of Years From Timeseries Data
        response_data.('Nyrs') = size(dt,1)/365.25; % number_timesteps/year_in_days
        % Ensure Timeseries Is Valid
        if isempty(procData(:, 2)) % This already covers isempty condition (length == 0)
            fail_flag = true;
        else
            fail_flag = false;
        end
    case 'POT' %POT
        % Remove Flag Values
        if ~isempty(response_data.('flag_value'))
            % Remove Flag Values
            procData(any(procData(:, 2:end) == response_data.('flag_value'), 2), :) = [];
        end
        % Merge data and remove NaN, Inf values
        procData(any(isinf(procData(:, 2:col_indx)) | isnan(procData(:, 2:col_indx)) | procData(:, 2:col_indx) <= 0, 2), :) = [];
        % Ensure POT Is Valid
        if length(unique(procData(:, 2), 'stable'))<=3 % This already covers isempty condition (length == 0)
            fail_flag = true;
        else
            fail_flag = false;
        end
end
% Abort PST Based On Data
if fail_flag
    % Abort PST Processing
    error('Error: Could not process dataset because invalid response removal yielded empty data structure.');
end

%% Perform SST
if pst_options.stat_print == 1
    disp(['*** Step 3: Performing SST for station ', plot_options.staID{1,1}]);
end

try
    % Defien POT Dataset
    switch response_data.DataType
        case 'Timeseries' %Timeseries
            % Execute StormSim-POT
            [POT_samp,~] = StormSim_POT(procData(:,1), procData(:,2), pst_options.tLag, response_data.lambda, response_data.Nyrs); % [ timestamp, event_peak, lower_bound, upper_bound ]
        case 'POT'
            POT_samp = procData; % [ timestamp, event_peak, event_peak_with_tide ]
    end
    %%% Add noise to duplicates in POT sample - LAA 2023/12/07
    [~, w]=unique(POT_samp(:,2),'stable');
    duplicate_indices=setdiff(1:numel(POT_samp(:,2)), w);
    POT_samp(duplicate_indices, 2) = POT_samp(duplicate_indices, 2) + 1e-6;
    %%%
    % Execute StormSim-SST-Fit
    [SST_output] = StormSim_PST_Fit(POT_samp(:, 2), POT_samp(:, 3), response_data.SLC, response_data.Nyrs, response_data.gprMdl, pst_options, plot_options);
    % Plot results
    if plot_options.create_plots == 1
        StormSim_PST_plot(SST_output, pst_options, plot_options);
    end
catch ME
    SST_output.staID = plot_options.staID;
    SST_output.ME = ME;
end

%% Save the output
if pst_options.stat_print == 1
    disp(['*** Step 4: Saving results here: ',path_out]);
end
% Save Output
if plot_options.create_plots == 1
    save(fullfile(plot_options.('path_out'), ['StormSim_' SST_output.staID '_SST_output.mat']), 'SST_output', '-v7.3');
end
if pst_options.stat_print == 1
    disp('*** Evaluation finished.' )
    disp(['****** Remember to check outputs Check_datasets and Removed_datasets.' newline])
    disp('*** StormSim-SST Tool terminated.')
end

%% ERROR HANDELING FUNCTION
    function [response_data, pst_options, plot_options] = error_handeling(response_data, pst_options, plot_options)
        % Define Boolean Fields To Inspect
        field_to_check = ["pst_options.use_AEP","plot_options.create_plots",...
            "plot_options.y_log", "pst_options.apply_GPD_to_SS",...
            "pst_options.stat_print", "pst_options.GPD_TH_crit"];
        % Define Error Message To Append
        error_msg = ["0 (AEF) or 1 (AEP)", "0 (no plots) or 1 (all plots)",...
            "0 (linear y-scale) or 1 (log y-scale)", "0 (use empirical for small sample) or 1 (force GPD fit)"...
            "0 (no code progress print) or 1 (print code progress)",...
            "1 (lambda sample intensity criterion) or  2 (WMSE criterion) for GPD threshold selection"];
        % Define Member List To Check Per Field
        member_list = [repmat([0, 1], 5, 1);[1, 2]];
        % Loop Across Fields To Check
        for kk = 1:length(field_to_check)
            % Build Error String
            error_str = "Error: " + field_to_check(kk) + " must be " + error_msg(kk) + ".";
            % Call Bool Check Function
            bool_check(eval(field_to_check(kk)), error_str, member_list(kk, :));
        end
        % Datatype Specific Errors
        switch response_data.DataType
            case 'POT'
                % Force Timeseries Fields To Empty
                pst_options.tLag = [];
                response_data.lambda = [];
                % Number Of Years
                if response_data.Nyrs<=0 || isempty(response_data.Nyrs)
                    error('When DataType is set to ''POT'': Input "Nyrs" cannot be empty and must have positive values only')
                end
                % Implicit SLC
                if length(response_data.SLC)~=1 || response_data.SLC < 0 || isnan(response_data.SLC) || isinf(response_data.SLC)
                    error('Input SLC must be a positive scalar')
                elseif isempty(response_data.('SLC'))
                    response_data.('SLC') = 0;
                end
                % Skew Tides
                if ~ismember(pst_options.ind_Skew, [0 1]) || isempty(pst_options.ind_Skew) || isnan(pst_options.ind_Skew) || isinf(pst_options.ind_Skew)
                    error('Input ind_Skew must be 0 or 1')
                end
                % Skew Tides Model
                if pst_options.ind_Skew==1
                    if isempty(response_data.gprMdl) || ~isobject(response_data.gprMdl)
                        error('When ind_Skew = 1: Input gprMdl cannot be an empty')
                    end
                end
            case 'Timeseries'
                % Force POT Fields To Empty
                response_data.data(:, 3) = zeros(size(response_data.data(:, 2)));
                response_data.Nyrs = [];
                response_data.SLC = 0;
                response_data.gprMdl = [];
                pst_options.ind_Skew = 0;
                % Inter-event Time Lag (hours)
                if pst_options.tLag<=0 || isempty(pst_options.tLag)
                    error('When DataType = ''Timeseries'': Input tLag cannot be an empty array and must have positive values only')
                end
                % Event Rate
                if response_data.lambda<=0 || isempty(response_data.lambda)
                    error('When DataType is set to ''Timeseries'': Input lambda cannot be an empty array and must have positive values only')
                end
            otherwise % Unrecognized Datatype
                error('Unrecognized value for DataType. Available options are ''Timeseries'' or ''POT'' ')
        end

        % ---- pst_options Fields -------
        % Bootstrap Simulations
        if ~isnumeric(pst_options.bootstrap_sims)
            pst_options.bootstrap_sims = 100;
        elseif pst_options.bootstrap_sims<100
            pst_options.bootstrap_sims = 100;
        end
        % Percentiles
        if length(pst_options.prc)>4 || all(isnan(pst_options.prc)) || all(isinf(pst_options.prc)) || any(pst_options.prc<0)
            error('Input prc can have 1 to 4 percentages in the interval [0,100].');
        elseif isempty(pst_options.('prc'))
            pst_options.('prc')=[2.28 15.87 84.13 97.72]';
        else
            pst_options.('prc') = sort(pst_options.('prc'),'ascend');
        end
        % ---- response_data Fields -------
        if isempty(response_data.data)|| size(response_data.data, 2) < 2
            error('Error: response_data.data cannot be empty. Must be a M x 2 or M x 3 data matrix.');
        end

        % ---- plot_options Fields -------
        % Response Label
        if isempty(plot_options.staID)
            plot_options.staID = 'resp';
        elseif ~ischar(plot_options.staID)
            error('Error: plot_options.staID must be a character array.')
        end
        % Y Axis Label
        if isempty(plot_options.yaxis_Label)
            plot_options.yaxis_Label = '';
        elseif ~ischar(plot_options.yaxis_Label)
            plot_options.yaxis_Limits = '';
        end
        % Y Axis Limit
        if ~isnumeric(plot_options.yaxis_Limits)
            plot_options.yaxis_Limits = [];
        end
        % Output Path
        if isempty(plot_options.path_out)
            plot_options.path_out = '';
        elseif ~ischar(plot_options.path_out)
            plot_options.path_out = '';
        end
    end
    function bool_check(data_field, error_msg, member_list)
        if isempty(data_field) || ~isscalar(data_field)
            error(error_msg);
        elseif ~isnumeric(data_field) || ~ismember(data_field, member_list)
            error(error_msg);
        end
    end
end
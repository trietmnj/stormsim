%% StormSim_JPM_Tool.m
%{
SST Input Data Structures:

1. Input Data Specifications:

response_data.(XX), where XX respresents
    - data: N x 4 double data matrix, where each column represents:
        col 01: Event response MATLAB serial date (see datenum)
        col 02: Response data without tides
        col 03: Skew tides.
        col 04: TC event Discrete Storm Weights (DSW) 
    - flag_value: Flag value to remove from response data.  
    - Ua: Event response absolute uncertainty 
    - Ur: Event response relative uncertainty 
    - SLC: magnitude of the sea level change implicit in the storm surge
    - tide_std: Uncertainty associated to tides.

2. Joint Probability Method (JPM) Specifications:

jpm_options.(XX), where XX represents
    - integration_method: 1 - PCHA ATCS, 2 - PCHA ITCS. Integration methodologies 
                          share the same integration equation but have unique ways of incorporating
                          the uncertainties. Current options are described as follows:
          *integrate_Method = 1 (PCHA ATCS):Refers to the Probabilistic Coastal Hazard Analysis (PCHA)
                                            with Augmented Tropical Cyclone Suite (ATCS) methodology. This approach is
                                            preferred when hazard curves with associated confidence limit (CL) curves
                                            are to be estimated using the synthetic storm suite augmented through Gaussian
                                            process metamodelling (GPM). The different uncertainties are incorporated into
                                            either the response or the percentiles, depending on the settings specified for
                                            tide_application and uncert_treatment. With the exception of when ind_skew = 1, the
                                            uncertainties are distributed randomly before application. This methodology
                                            has been applied in the following studies:
                                            a) South Atlantic Coast Study (SACS) - Phases 1 (PRUSVI), 2 (NCSFL) and 3 (SFLMS)
                                            b) Louisiana Coast Protection and Restoration (LACPR) Study
                                            c) Coastal Texas Study (CTXS) - Revision
          *integrate_Method = 2 (PCHA ITCS):Refers to the PCHA Standard methodology. This
                                            approach is preferred when hazards with CLs are to be estimated using the
                                            synthetic storm suite is used "as is" (not augmented). The absolute and
                                            relative uncertainties are initially partitioned. Then, the different
                                            uncertainties are incorporated into either the response or the percentiles,
                                            depending on the settings specified for tide_application and uncert_treatment. With the
                                            exception of when ind_skew = 1, the uncertainties are normally
                                            distributed using a discrete Gaussian before application. This methodology
                                            has been used in the following studies:
                                            a) North Atlantic Coast Comprehensive Study (NACCS)
                                            b) Coastal Texas Study (CTXS) - Initial study
    - uncertainty_treatment: Indicates the uncertainty treatment to use; specified as a character vector.
                             Determines how the absolute (U_a) and relative (U_r) uncertainties are applied.
                             Current options are:
            *uncert_treatment = 'absolute': only U_a is applied
            *uncert_treatment = 'relative': only U_r is applied
            *uncert_treatment = 'combined': both U_a and U_r are applied
    - tide_application: Indicates how the tool should apply the tide uncertainty.
                        This uncertainty will be applied differently depending on the selected
                        integration method (integrate_Method) and uncertainty treatment (uncert_treatment).
                        Available options are as follows:

          *tide_application = 0:The tide uncertainty is not applied.
          *tide_application = 1:The tide_std is combined with U_a, U_r or both, 
                                and then applied to the confidence limits.
          *tide_application = 2:Tide uncertainty is applied to the response before
                                any of the other uncertainties. The value of 
                                input ind_Skew determines how it is added.
                                When ind_Skew = 1: Skew tides (response_data.data(:, 3)) are
                                added to the response. When ind_Skew = 0: 'SD': the tide 
                                uncertainty is distributed and then added to the response.
                                The distribution is random when integrate_Method = 'PCHA ATCS'.
                                Otherwise, the uncertainty is distributed using a discrete Gaussian
                                distribution when integrate_Method = 'PCHA ITCS'.
    - ind_Skew: indicator for computing/adding skew tides to the storm surge (1-apply skew tides, 0-don't apply skew tides)
    - use_AEP: AEP vs AEF flag (1-Use AEP for HC frequencies, 0-Use AEF for HC frequencies)
    - prc: percentage values for computing the percentiles. Accepts a max of 4 values.
    - stat_print: indicator to print script status (1-print steps, 0-don't print)
    
plot_options.(XX), where XX represents
    - create_plots: 
    - staID: Response variable name. 
    - yaxis_Label: Hazard curve y axis label
    - yaxis_Limits: Hazard curve y axis limits 
    - y_log: Hazard curve y axis scale switch (1-log, 0-linear)
    - path_out: Output path
%}

%}
function [JPM_output] = StormSim_JPM(response_data, jpm_options, plot_options)
%% General settings
if jpm_options.stat_print == 1
    clc;
    disp(['***********************************************************' newline...
        '***         StormSim-JPM Tool Alpha Version 0.3         ***' newline...
        '***                Release 1 - 20210831                 ***' newline...
        '***                 FOR  TESTING  ONLY                  ***' newline...
        '***********************************************************']);

    disp([newline '*** Step 1: Processing input arguments ']);
end
% Turn off all warnings
warning('off','all');

%% PARAMETER INITIALIZATION
% Error Handeling For Inputs
[response_data, jpm_options, plot_options] = error_handeling(response_data, jpm_options, plot_options);
% Define Output Path For PST
plot_options.('path_out') = fullfile(plot_options.('path_out'), 'JPM_outputs');
% Check path to output folder
if ~exist(plot_options.('path_out'), 'dir') && plot_options.create_plots == 1
    mkdir(plot_options.('path_out'));
end

%% Data preprocessing: remove NaN, inf values; compute record length
if jpm_options.stat_print == 1
    disp('*** Step 2: Verifying input datasets')
end
% Remove Flag Values
if ~isempty(response_data.('flag_value'))
    % Remove Flag Values
    response_data.data(any(response_data.data(:, 2) == response_data.('flag_value'), 2), :) = [];
end
% Merge data and remove NaN, Inf values
response_data.data(any(isinf(response_data.data(:, 2)) | isnan(response_data.data(:, 2)) | response_data.data(:, 2) <= 0, 2), :) = [];
% Ensure Timeseries Is Valid
if isempty(response_data.data) % This already covers isempty condition (length == 0)
    fail_flag = true;
else
    fail_flag = false;
end
% Abort PST Based On Data
if fail_flag
    % Abort PST Processing
    error('Error: Could not process dataset because invalid response removal yielded empty data structure.');
end

%% Check number of virtual gauges and partition the inputs if necessary
if jpm_options.stat_print == 1
    % Perform integration
    disp('*** Step 3: Performing integration')
end
%
JPM_output = StormSim_JPM_integration(response_data, jpm_options, plot_options);
% Plot hazard curves
if plot_options.create_plots == 1
    if jpm_options.stat_print == 1
        disp('*** Step 3: Plotting hazard curves');
    end
    StormSim_JPM_plot(JPM_output, jpm_options, plot_options);
    % Store output
    if jpm_options.stat_print == 1
        disp(['*** Step 4: Saving results here: ',path_out]);
    end
    save([plot_options.('path_out'), 'StormSim_JPM_' plot_options.staID 'output.mat'],'JPM_output','-v7.3');
end


if jpm_options.stat_print == 1
    disp('*** Evaluation finished.');
    disp('*** StormSim-JPM Tool terminated.');
end

%% AUXIALIARY FUNCTIONS (ERROR HANDELING)
    function [response_data, jpm_options, plot_options] = error_handeling(response_data, jpm_options, plot_options)
        % Response Data Matrix
        if ~isnumeric(response_data.data) || size(response_data.data, 2) ~= 4 % [ time, response, skew_tides, dsw ]
            error('Error: response_data.data must be a N x 4 numerical matrix where columns represent: [ time, response, skew_tides, dsw ]')
        end
        % Implicit SLC
        if isempty(response_data.('SLC'))
            response_data.('SLC') = 0;
        elseif length(response_data.SLC)~=1 || response_data.SLC < 0 || isnan(response_data.SLC) || isinf(response_data.SLC)
            error('Error: response_data.SLC must be a positive scalar');
        end
        % Define Boolean Fields To Inspect
        field_to_check = ["jpm_options.use_AEP","plot_options.create_plots",...
            "plot_options.y_log", "jpm_options.stat_print",...
            "jpm_options.ind_Skew", "jpm_options.integration_method"];
        % Define Error Message To Append
        error_msg = ["0 (AEF) or 1 (AEP)", "0 (no plots) or 1 (all plots)",...
            "0 (linear y-scale) or 1 (log y-scale)", "0 (no code progress print) or 1 (print code progress)",...
            "0 (use tide std) or 1 (use skew tides)", "1 (PCHA ATCS) or 2 (PCHA ITCS)"];
        % Define Member List To Check Per Field
        member_list = [repmat([0, 1], 5, 1);[1, 2]];
        % Loop Across Fields To Check
        for kk = 1:length(field_to_check)
            % Build Error String
            error_str = "Error: " + field_to_check(kk) + " must be " + error_msg(kk) + ".";
            % Call Bool Check Function
            bool_check(eval(field_to_check(kk)), error_str, member_list(kk, :));
        end
        % Verify Tidal Application Case And Inputs
        switch jpm_options.tide_application
            case 0 % No tides
                % Force Tidal STD To Zero
                response_data.tide_std = 0;
                % Force Skew Tide Column To Zero
                response_data.data(:, 3) = 0;
                % Set Skew Tides Switch To 0
                jpm_options.ind_Skew = 0;
            case 1 % Tides Added as Uncertainty To Confidence Limits
                % Check Standard Deviation Value
                if ~isnumeric(response_data.tide_std) ||  ~isscalar(response_data.tide_std) || any(response_data.tide_std<=0)
                    error('Error: Tides standard deviation must be a positive scalar value.');
                end
                % Force Skew Tide Column To Zero
                response_data.data(:, 3) = 0;
                % Set Skew Tides Switch To 0
                jpm_options.ind_Skew = 0;
            case 2 % Tides Added To Response
                if jpm_options.ind_Skew == 1
                    % Check Skew Tides
                    if any(isinf(response_data.data(:, 3))) || any(isnan(response_data.data(:, 3)))
                        error('Error: response_data.data(:, 3) (Skew tides) must be non-inf or non-nan values.');
                    end
                    % Force Tidal STD To Zero
                    response_data.tide_std = 0;
                else
                    % Check Standard Deviation Value
                    if ~isnumeric(response_data.tide_std) ||  ~isscalar(response_data.tide_std) || any(response_data.tide_std<=0)
                        error('Error: response_data.tide_std must be a positive scalar value.');
                    end
                    % Force Skew Tide Column To Zero
                    response_data.data(:, 3) = 0;
                end
        end
        % Verify Uncertainty Treatment Method
        switch jpm_options.uncertainty_treatment
            case 'combined'
                % Pass
            case 'relative'
                % Set Absolute Component To Zero
                response_data.Ua = 0;
            case 'absolute'
                % Set Relative Component To Zero
                response_data.Ur = 0;
            otherwise
                error('Error: response_data.uncertainty_treatment must be: ''combined'', ''relative'', ''absolute''');
        end
        % Verify Uncertainty Values
        if ~isnumeric(response_data.Ur) || any(response_data.Ur<0) || ~isscalar(response_data.Ur)
            error('Error: response_data.Ur must be a positive scalar.');
        end
        if ~isnumeric(response_data.Ua) || any(response_data.Ua<0) || ~isscalar(response_data.Ua)
            error('Error: response_data.Ua must be a positive scalar.');
        end
        % Percentiles
        if length(jpm_options.prc)>4 || any(isnan(jpm_options.prc)) || any(isinf(jpm_options.prc)) || any(jpm_options.prc<0)
            error('Error: jpm_options.prc can have 1 to 4 percentages in the interval [0, 100].');
        elseif isempty(jpm_options.('prc'))
            jpm_options.('prc')=[2.28 15.87 84.13 97.72]';
        else
            jpm_options.('prc') = reshape(sort(jpm_options.('prc'),'ascend'), 1, []);
        end
        % ---- plot_options Fields -------
        % Response Label
        if isempty(plot_options.staID)
            plot_options.staID = 'resp';
        elseif ~ischar(plot_options.staID)
            error('Error: plot_options.staID be a character array.')
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
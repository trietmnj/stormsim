  %% FUNCTION INPUTS DOC
  %{
JPM Input Data Structures:

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
  
  %% LOAD EXAMPLE DATA 
  % Add Dependencies 
  addpath('JPM\');
  % This is the use case for processing a Peaks Over Threshold Dataset
  % Load CHS Timeseries Data
  load('SSv1.0_Forced_Sta50_2195_CHS-NA_SP6021.mat');
  % Define CHS Save Point Surge Absolute & Relative Uncertainty (Model Error)
  Ua = 0.3738;
  Ur = 0.5840;
  % Get Max Surge Value For Each Storm Event
  surge_pot = cellfun(@(x) max(x(:, 1)), storm.TC.Timeseries.Default(:, 2)); % User Might Feed Dataset (N storms x M replicates)
  % Compute Rows And Cols
  [drows, dcols] = size(surge_pot);
  % Adjust DSWs
  if dcols ~= 1 % Need To Scale DSW For Replicates
      tc_dsw = repmat(prob_mass.TC_Freq./dcols, 1, dcols);
  else
      tc_dsw = prob_mass.TC_Freq;
  end

  %% CREATE INPUT DATA STRUCTURES 
  % JPM
  response_data = struct('data', [zeros(drows*dcols, 1) surge_pot(:) zeros(drows*dcols, 1), tc_dsw(:)],...
      'flag_value', [],'Ua', Ua,'Ur', Ur, 'SLC', 0, 'tide_std', 0,...
      'DataType', 'POT');
  % JPM Options
  eva_options = struct('integration_method', 2,...
      'uncertainty_treatment', 'combined',...
      'tide_application', 0, 'ind_Skew', 0, 'use_AEP', 0,...
      'prc', [16, 84], 'stat_print', 0);
  % Plot Options
  plot_options = struct('create_plots', 1,'staID', 'SSL', 'yaxis_Label', 'Surge [m]',...
      'yaxis_Limits', [], 'y_log', 0, 'path_out', '');
  
  %% CREATE HAZARD CURVE 
  [JPM_outputs] = StormSim_JPM(response_data, eva_options, plot_options);

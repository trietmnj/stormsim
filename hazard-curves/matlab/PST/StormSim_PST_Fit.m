function [SST_output] = StormSim_PST_Fit(POT_no_tides, POT_with_tides, SLC, Nyrs, gprMdl, pst_options, plot_options)
%% INITIALIZE FIELDS
% Set up probabilities for HC summary
if pst_options.('use_AEP') %Select AEPs
    HC_tbl_x = 1./[2 5 10 20 50 100 200 500 1000 2000 5000 1e4 2e4 5e4 1e5 2e5 5e5 1e6]';
else %Select AEFs
    HC_tbl_x = 1./[0.1,0.2,0.5,1,2,5,10,20,50,100,200,500,1000,2000,5000,10000]';
end
% Set up responses for HC summary
HC_tbl_rsp_y =(0.01:0.01:20)';
% Set up AEFs for full HC; in log10 scale (for plotting), from 10^1 to 10^-6
d=1/90; v=10.^(1:-d:0)'; HC_plt_x=v; x=10;
for i=1:6
    HC_plt_x=[HC_plt_x; v(2:end)/x];
    x=x*10;
end
HC_plt_x=flipud(HC_plt_x);
% Sort POT sample in descending order
POT_no_tides = sort(POT_no_tides, 'descend');
HC_emp = POT_no_tides; % Response vector sorted in descending order; positive values only
% Pre-Allocate Output Fields
Resp_boot_plt = NaN(pst_options.bootstrap_sims, length(HC_plt_x)); % Nsims x Events
pd_k_wOut = NaN(pst_options.bootstrap_sims, 1); % Nsims x 1
pd_sigma = pd_k_wOut; % Nsims x 1
pd_TH_wOut = pd_k_wOut; % Nsims x 1
pd_k_mod = pd_k_wOut; % Nsims x 1


%% Develop empirical CDF (using output of POT function)
% Weibull Plotting Position, P = m/(n+1)
% where P = Exceedance probability
%       m = rank of descending response values, with largest equal to 1
%       n = number of response values
Nstrm_hist = length(HC_emp); % Weibull's "n"
HC_emp(:, 2) = (1:Nstrm_hist)'; %Rank of descending response values
HC_emp(:, 3) = HC_emp(:,2)/(Nstrm_hist+1); %Webull's "P"; NEEDS Lambda Correction

% Lambda Correction - Required for Partial Duration Series (PDS)
Lambda_hist = Nstrm_hist/Nyrs; % Lambda = sample intensity = events/year
HC_emp(:, 4) = HC_emp(:, 3)*Lambda_hist;

% Compute Annual Recurrence Interval (ARI)
HC_emp(:, 5) = 1./HC_emp(:, 4);
ecdf_y = HC_emp(:, 1);
% Convert To AEP
if pst_options.use_AEP %Convert to AEP
    HC_emp(:, 4) = aef2aep(HC_emp(:, 4));
    HC_plt_x = aef2aep(HC_plt_x);
end

%% Perform bootstrap
% Skew Tides Bootstrap
if  pst_options.ind_Skew && ~isempty(POT_with_tides) && isobject(gprMdl)
    % Substract Implicit SLC From Empirical Sample
    ecdf_y = ecdf_y - SLC;
    % Perform Bootstraping
    boot = ecdf_boot(ecdf_y, pst_options.bootstrap_sims)'; % N events x N sims
    % Compute and add skew tides to bootstrap sample or surge
    for i = 1:pst_options.bootstrap_sims
        % Predict Skew Tide With Provided Metamodel For Each Sim
        [skew_tide_mean, skew_tide_sd] = predict(gprMdl, boot(:, i));
        % Add Tide Uncertainty To Predicted Value
        skew_tide_pred = skew_tide_mean + randn(length(skew_tide_mean), 1).*skew_tide_sd;
        % Add Skew Tide To Surge
        boot(:, i) = boot(:, i) + skew_tide_pred; %this is water level
        % Rank Response
        boot(:, i) = sort(boot(:, i), 'descend');
    end
    % Add the SLC amount
    boot = boot + SLC;
    %Substitute the empirical dist with user supplied surge + tides + SLC (WL)
    ecdf_y = sort(POT_with_tides, 'descend'); %Sort POT sample in descending order
    % Reshape , Why ?
    szH = size(HC_emp, 1); szy = length(ecdf_y);
    if szH>szy
        HC_emp = HC_emp(1:szy, :);
    elseif szH<szy
        ecdf_y = ecdf_y(1:szH);
    end
    HC_emp(:, 1) = ecdf_y;
    boot = boot(1:length(ecdf_y), :);
else
    % Response Bootstrap
    boot = ecdf_boot(ecdf_y, pst_options.bootstrap_sims)';
end
% Dealing With Extreme Values, Remove <0 Values
boot(boot<0) = NaN;
% Verify For Applicability Of GPD Fitting
gpd_pass = (length(ecdf_y)>=20 && Nyrs>=20) || pst_options.apply_GPD_to_SS;

%% Apply the GPD when empirical POT sample size is >20 and RL >20 yrs. Otherwise, compute HC using empirical.
if gpd_pass %apply GPD
    %% Apply "Mean Residual Life" Automated Threshold Detection
    MRL_output = StormSim_MRL(pst_options.GPD_TH_crit, ecdf_y, Nyrs);

    %% MRL GPD Threshold condition
    mrl_th = MRL_output.Selection.Threshold;

    %% Take parameters and preallocate
    ecdf_x_adj=HC_emp(:,4);

    %% Perform SST
    % If the MRL didn't returned a threshold value, compute it from the
    % bootstrap samples. Then identify the peaks.
    if isnan(mrl_th)
        sz = size(boot,1); %total events above threshold per simulation
        idx = ones(sz, pst_options.bootstrap_sims)==1; %index of events above threshold per simulation
        idx2 = zeros(sz, pst_options.bootstrap_sims)==1; %index of events below threshold per simulation
        sz = repmat(sz,1, pst_options.bootstrap_sims);
        mrl_th = 0.99*min(boot,[],1,'omitnan');
        MRL_output.Selection.Threshold = mean(mrl_th,'omitnan');
        MRL_output.Selection.Criterion = {'Default'};
        eMsg = 'No threshold found by MRL method. Default criterion applied: GPD threshold set to 0.99 times the minimum value of the bootstrap sample.';
    else
        idx = boot>mrl_th; %index of events above threshold per simulation
        sz = sum(idx,1); %total events above threshold per simulation
        idx2 = boot<=mrl_th; %index of events below threshold per simulation
        mrl_th = repmat(mrl_th,1,pst_options.bootstrap_sims);
        eMsg ='';
    end
    Lambda_mrl = sz/Nyrs; %annual rate of events

    % GPD fitting
    for k = 1:pst_options.bootstrap_sims
        try
            PEAKS_rnd = boot(:,k);

            % Fit the GPD to a bootrap data sample
            u = PEAKS_rnd(idx(:,k));
            pd = fitdist(u,'GeneralizedPareto','theta',mrl_th(k));
            pd_TH_wOut(k,1) = pd.theta;
            pd_k_wOut(k,1) = pd.k;
            pd_sigma(k,1) = pd.sigma;
        catch
        end
    end

    % Correction of GPD shape parameter values. Limits determined by NCNC.
    pd_k_mod=pd_k_wOut;
    k_min=-0.5; k_max=0.3;
    pd_k_mod(pd_k_mod<k_min) = k_min;
    pd_k_mod(pd_k_mod>k_max) = k_max;
    eMsg = '';
else
    eMsg = 'GPD not fit: POT sample size <20 and RL <20 years.';
end

%% COMPUTE HC
for k = 1:pst_options.bootstrap_sims
    % Build HC With GPD If Conditions Met
    if gpd_pass
        try
            % Get POT Smaple From Bootsrap Simulations
            PEAKS_rnd = boot(:, k);
            % Compute the AEF from the GPD fit
            Resp_gpd = icdf('Generalized Pareto', 1-HC_plt_x/Lambda_mrl(k), pd_k_mod(k,1), pd_sigma(k,1), pd_TH_wOut(k,1));
            AEF_gpd = HC_plt_x(~isnan(Resp_gpd));
            Resp_gpd(isnan(Resp_gpd)) = [];
            % Compute the empirical AEF
            Resp_ecdf = PEAKS_rnd(idx2(:, k));
            AEF_ecdf = ecdf_x_adj(idx2(:, k));
            % Merge the AEFs (empirical + fitted GPD)
            y_comb = [Resp_gpd;Resp_ecdf];
            x_comb = [AEF_gpd;AEF_ecdf];
        catch
            % Skip bootstrap Sim
            continue;
        end
    else % Using Empirical Only
        y_comb = boot(:,k);
        x_comb = HC_emp(:,4);
    end
    % Convert To AEP
    if pst_options.use_AEP
        x_comb = aef2aep(x_comb);
    end

    % Delete duplicates
    [~, ia, ~] = unique(x_comb, 'stable');
    x_comb = x_comb(ia, :);
    y_comb = y_comb(ia, :);

    [~, ia, ~] = unique(y_comb, 'stable');
    y_comb = y_comb(ia, :);
    x_comb = x_comb(ia, :);

    % Interpolate AEF curve for table and plot
    Resp_boot_plt(k, :) = interp1(log(x_comb), y_comb, log(HC_plt_x));
end

%% PLOT BOOTSTRAPING
if gpd_pass && plot_options.create_plots
    % Initialize Figure
    fig=figure('Color',[1 1 1],'visible','off', 'Units', 'normalized','Position', [1 1 1 1]);
    %
    if plot_options.y_log == 1
        y_scale = 'log';
    else
        y_scale = 'linear';
    end
    % Initialize Axes
    ax = axes('xscale','log','YScale',y_scale,'XGrid','on','XMinorTick','on',...
        'YGrid','on','YMinorTick','on','XDir','reverse','FontSize',12);
    % hold Axes Properties
    hold(ax,'on');
    % Title
    title(ax, {'StormSim-SST '; [plot_options.staID ' Bootstrap Sample Plot']},'FontSize',12);
    % Define X Axis
    if pst_options.use_AEP == 1
        AEF_ecdf = aef2aep(AEF_ecdf);
        AEF_gpd = aef2aep(AEF_gpd);
        xlim(ax, [1e-4 1]);
        set(ax, 'XTick', [1e-4 1e-3 1e-2 1e-1 1])
        xlabel(ax, 'Annual Exceedance Probability','FontSize',12);
    else
        xlim([1e-4 10]);
        set(ax, 'XTick', [1e-4 1e-3 1e-2 1e-1 1 10]);
        xlabel(ax, 'Annual Exceedance Frequency (yr^{-1})', 'FontSize',12);
    end
    % Define Y Axis
    if ~isempty(plot_options.yaxis_Limits)
        ylim(plot_options.yaxis_Limits);
    end
    ylabel(plot_options.yaxis_Label,'FontSize',12);
    % Historical
    scatter(HC_emp(:,4), ecdf_y, 15, 'g', 'filled', 'MarkerEdgeColor', 'k');
    % Resampling (last bootstrap sample)
    scatter(HC_emp(:,4), PEAKS_rnd, 15, 'r', 'filled', 'MarkerEdgeColor', 'k');
    % Empirical
    plot(AEF_ecdf, Resp_ecdf, 'y-', 'LineWidth', 2);
    % MRL threshold
    th_x = interp1(y_comb, x_comb, pd_TH_wOut(k));
    scatter(th_x, pd_TH_wOut(k), 15, 'w', 'filled', 'MarkerEdgeColor', 'b');
    % GPD with MRL
    plot(AEF_gpd, Resp_gpd, 'b-', 'LineWidth', 2)
    % Legend
    legend({'Historical', 'Resampling', 'Empirical', 'MRL threshold', 'GPD'},...
        'Location', 'southoutside', 'Orientation', 'horizontal', 'NumColumns', 4, 'FontSize', 10);
    % Save Out Name
    fname = fullfile(plot_options.path_out, ['SST_HC_bootCheck_', plot_options.staID,'_TH_', MRL_output.Selection.Criterion{:},'.png']);
    % Save Figure
    saveas(fig, fname, 'png');
    % Close Figure
    close(fig);
end

%% Compute mean and percentiles
Boot_mean_plt = mean(Resp_boot_plt, 1, 'includenan');
Boot_plt = prctile(Resp_boot_plt, pst_options.prc, 1);

%For this application only: delete results if WL >= 1e3 meters
if pst_options.ind_Skew && max(Boot_mean_plt, [], 'omitnan')>=1e3
    error('Values above 10^3 found in mean hazard curve')
end

HC_plt = [Boot_mean_plt;Boot_plt]';

% Monotonic adjustment
for kk = 1:size(HC_plt,2)
    HC_plt(:, kk) = Monotonic_adjustment(HC_plt_x, HC_plt(:, kk));
end


%% Interpolation to create response hazard table
% preallocate
HC_tbl_rsp_x = NaN(length(HC_tbl_rsp_y), size(HC_plt, 2));
HC_tbl_y = NaN(length(HC_tbl_x), size(HC_plt, 2));
HCmn = NaN(1, size(HC_plt, 2));
for kk = 1:size(HC_plt, 2)

    % Delete duplicates
    [~,ia,~] = unique(HC_plt(:, kk),'stable');
    dm1 = HC_plt(ia, kk); dm2 = log(HC_plt_x(ia));

    % Delete NaN/Inf
    ia = isnan(dm1) | isinf(dm1); dm1(ia) = []; dm2(ia) = [];

    % Interpolate
    HC_tbl_rsp_x(:, kk) = exp(interp1(dm1, dm2, HC_tbl_rsp_y, 'linear', 'extrap'));
    HC_tbl_y(:, kk) = interp1(dm2, dm1, log(HC_tbl_x), 'linear', 'extrap');

    %interpol for 0.1 aep/aef
    HCmn(1, kk) = interp1(dm2, dm1, log(0.1), 'linear', 'extrap');
end
% Ensure No Duplicate Values
[~, ia, ~] = unique(log(HC_emp(:, 4)), 'stable');
% Compare if mean HC > 1.75* emp HC at 0.1 AEP/AEF,
HCep = interp1(log(HC_emp(ia, 4)), HC_emp(ia, 1), log(0.1), 'linear', 'extrap');
str1 = {''};
if HCmn(1) > 1.75*HCep
    str1 = {'Warning: At 0.1 AEP/AEF, best estimate HC value is greater than 1.75 times the empirical HC value. Manual verification is recommended.'};
end

% Change negatives to NaN
HC_tbl_y(HC_tbl_y<0) = NaN;
HC_tbl_rsp_x(HC_tbl_rsp_x<1e-4) = NaN;

%% Store parameters needed for manual GPD Shape parameter evaluation
MRL_output.pd_TH_wOut = pd_TH_wOut;
MRL_output.pd_k_wOut = pd_k_wOut;
MRL_output.pd_sigma = pd_sigma;
MRL_output.pd_k_mod = pd_k_mod;
MRL_output.Status = eMsg;
HC_emp = array2table(HC_emp,'VariableNames',{'Response','Rank','CCDF','Hazard','ARI'});
% Gather the output
SST_output.staID = plot_options.staID;
SST_output.RL = Nyrs;
SST_output.MRL_output = MRL_output;
SST_output.HC_plt = HC_plt;
SST_output.HC_tbl = HC_tbl_y;
SST_output.HC_tbl_rsp_x = HC_tbl_rsp_x;
SST_output.HC_emp = HC_emp;
SST_output.HC_tbl_rsp_y = HC_tbl_rsp_y;
SST_output.HC_plt_x = HC_plt_x;
SST_output.HC_tbl_x = HC_tbl_x;
end
function JPM_outputs = StormSim_JPM_integration(response_data, jpm_options, plot_options)
%% INITIALIZE RESPONSE FIELDS
% Get Input Dataset
Resp = response_data.data(:, 2); % Response Data
ProbMass = response_data.data(:, 4); % DSWs
U_tide = response_data.data(:, 3);
U_a = response_data.Ua;
U_r = response_data.Ur;
% Intialize Random Norm Variable
randomNorm = 0;
% Remove sea level change (without steric adjustment) from response data
Resp = Resp - response_data.SLC;

%% INTIALIZE HAZARD FREQUENCIES
% Set up probabilities for HC summary
if jpm_options.('use_AEP') %Select AEPs
    HC_tbl_x = 1./[2 5 10 20 50 100 200 500 1000 2000 5000 1e4 2e4 5e4 1e5 2e5 5e5 1e6]';
else %Select AEFs
    HC_tbl_x = 1./[0.1 0.2 0.5 1 2 5 10 20 50 100 200 500 1e3 2e3 5e3 1e4 2e4 5e4 1e5 2e5 5e5 1e6]';
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

%% PCHA STANDARD ONLY FIELDS
if jpm_options.integration_method == 2
    % Define Normal Distribution Discretization Z-Scores
%     dscrtGauss = [1.9982;1.5632;1.3064;1.1147;0.957;0.8202;0.6973;0.5841;0.478;0.377;0.2798;0.1852;0.0922;0;-0.0922;-0.1852;-0.2798;-0.377;-0.478;-0.5841;-0.6973;-0.8202;-0.957;-1.1147;-1.3064;-1.5632;-1.9982];
    dscrtGauss = readmatrix('discrete_norm_444.txt');
    % Define Number Of Replicates
    nReps = length(dscrtGauss);
    % Repeat Normal Replicates Per Number Of Storms
    dscrt = sort(repmat(dscrtGauss,  length(Resp), 1));
    % Scale DSW By Number Of Replicates
    ProbMass = repmat(ProbMass./length(dscrtGauss), nReps, 1);
    % Apply Normaly Distributed Replicates To Response
    Resp = repmat(Resp, nReps, 1);
    % Apply Normaly Distributed Replicates To Tides
    U_tide = repmat(U_tide, nReps, 1);
    % Partition Uncertainty
    p1_a = 0.1; %same units as response array
    if U_a^2 >= p1_a^2
        U_a = sqrt(U_a^2-p1_a^2);
    end
    %partition of the relative unc
    p1_r = .1; %dimensionless fraction
    if U_r^2 >= p1_r^2
        U_r = sqrt(U_r^2-p1_r^2);
    end
    % Application of first partition to response
    Resp = Resp + dscrt.*(p1_a + Resp.*p1_r)/2;
end

%% Tides
% Get Response Vector Size
resp_sz = length(Resp);
% Prep Skew Tides and Tides Uncertainty for Integration
switch jpm_options.tide_application
    case 0 % No Tides
        tide_cl = 0;%zeros(resp_sz, 1);
    case 1 % Apply Tides Through Confidence Limits
        tide_cl = response_data.tide_std;%.*ones(resp_sz, 1); % Define Tide Std
    case 2 % Add Tides To Response
        % No Tides On CLs
        tide_cl = 0;%zeros(resp_sz, 1);
        % Create Normal Random Numbers
        if jpm_options.ind_Skew == 0 % SD
            rng('default');
            % Define RandNorm According to Integration Method
            switch jpm_options.integration_method
                case 1 % PCHA ATCS
                    randomNorm = randn(resp_sz, 1);
                case 2 % PCHA ITCS
                    randomNorm = dscrt;
            end
            % Replace Skw Tide Vector With tide_std
            U_tide = response_data.tide_std;
        else
            randomNorm = 1;
        end
end
% Add uncertainty (or skews) and sea level change to responses
Resp = Resp + randomNorm.*U_tide + response_data.SLC;

%% DEFINE CONFIDENCE LIMITS FUNCTION
% compute Normal Z-scores
z=reshape(norminv(jpm_options.prc/100), 1, []);
% Define CL Function Handle
switch jpm_options.uncertainty_treatment
    case 'absolute'
        CL_unc =@(y,U_t) y + z.*sqrt(U_a.^2 + U_t.^2);%.*ones(length(y),1);
    case 'relative'
        CL_unc =@(y,U_t) y + z.*y.*sqrt((y.*U_r).^2 + U_t.^2);
    case 'combined'
        if tide_cl == 0
            CL_unc =@(y,U_t) y + z.*1./sqrt(1/U_a^2 + 1./(y.*U_r).^2);
        else
            CL_unc =@(y,U_t) y + z.*1./sqrt(1/U_a^2 + 1./(y.*U_r).^2 + 1./U_t.^2);
        end
end

%% PERFORM INTEGRATION
% Find Valid Entries
pass_indx = ~isnan(Resp) & Resp>0;
% Keep Valid
Resp = Resp(pass_indx, 1);
ProbMass = ProbMass(pass_indx, 1);
% Sort Response
[y, I] = sort(Resp, 'descend');%sort response for non-dry storms;
% y: Response, thresholds for defining hazard curve
x = cumsum(ProbMass(I, 1)); %HC_Prob: exceedance of threshold rates
x(x==0)=1e-16;
% Sort in ascending order
dm = sortrows([x y], 1, 'ascend');
x=log(dm(:,1));y=dm(:,2);
% remove duplicates from x values
[~,ia,~]=unique(x,'stable');y=y(ia);x=x(ia);
% remove duplicates from y values - LAA 2023/12/07
[~,iy,~]=unique(y,'stable');y=y(iy);x=x(iy);
% Compute percentiles
resp_perc = CL_unc(y, tide_cl);
% merge best estimate with percentiles
y = [y resp_perc];
% Interpolate AEF curve for plot
Lx=x;
y_plt = interp1(Lx,y,log(HC_plt_x));
% Interpolation to create hazard tables
n = size(y, 2);
HC_tbl_rsp_x = NaN(length(HC_tbl_rsp_y), n);
HC_tbl_y = interp1(Lx, y, log(HC_tbl_x), 'linear', 'extrap');
for NN=1:n
    [~, ia, ~] = unique(y(:, NN), 'stable');y2=y(ia,NN);Lx2=Lx(ia);
    HC_tbl_rsp_x(:, NN) = exp(interp1(y2, Lx2, HC_tbl_rsp_y, 'linear', 'extrap'));
end
%Change negatives to NaN
HC_tbl_y(HC_tbl_y<0)=NaN;
HC_tbl_rsp_x(HC_tbl_rsp_x<0)=NaN;
y_plt(y_plt<0)=NaN;
% Convert to AEP
if jpm_options.use_AEP
    HC_tbl_rsp_x=aef2aep(HC_tbl_rsp_x);
end

%% STORE OUTPUTS
% Gather the output
JPM_outputs.staID = plot_options.staID;
JPM_outputs.HC_plt = y_plt;
JPM_outputs.HC_tbl = HC_tbl_y;
JPM_outputs.HC_tbl_rsp_x = HC_tbl_rsp_x;
JPM_outputs.HC_tbl_rsp_y = HC_tbl_rsp_y;
JPM_outputs.HC_plt_x = HC_plt_x;
JPM_outputs.HC_tbl_x = HC_tbl_x;
end


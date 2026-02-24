%% StormSim_MRL.m
%{
SOFTWARE NAME:
    StormSim-SST-Fit (Statistics)

DESCRIPTION:
   This script applies the mean residual life (MRL) methodology to
   objectively select the parameters of the Generalized Pareto Distribution
function.

INPUT ARGUMENTS:
  - POT_samp: empirical distribution of the Peaks-Over-Threshold sample, as
      computed in StormSim_SST_Fit.m
  - Nyrs: record length in years of the input time series data set;
      specified as a positive scalar
     
AUTHORS:
    Norberto C. Nadal-Caraballo, PhD (NCNC)
    Efrain Ramos-Santiago (ERS)

HISTORY OF REVISIONS:
20200903-ERS: revised.
20201015-ERS: revised. Updated documentation.
20201215-ERS: added break in for loop to avoid evaluating thresholds
    returning excesses of same magnitude.
20210325-ERS: organized the threshold computation; the 3rd threshold not included
    in the output anymore; output organized into table arrays stored in a structure array.
20210406-ERS: identified error when input sample size <10. When this
    happens, an empty array is returned and the Default GPD threshold computed
    in the three fit scripts.
20210412-ERS: now selecting a minima when no inflexion point exists; avoiding the script to crash.
20210429-ERS: now removing noise from the min WMSE through kernel
    regression. Also corrected the minimum WMSE criterion based on Langousis. Removed patch
    applied on 20210412.
20210430-ERS: script will stop and return empty arrays when no minima is
    found by WRMS criterion.

***************  ALPHA  VERSION  **  FOR INTERNAL TESTING ONLY ************
%}
function [MRL_output] = StormSim_MRL(GPD_TH_crit, PEAKS, Nyrs)

%% Step 1: Use sorted POT dataset as initial values of threshold parameter.
th = sort(PEAKS, 'ascend'); %threshold parameter; sorted in ascending order
N = size(th,1);

% preallocate output
MRL_output.Summary=array2table(NaN(1,8),'VariableNames',...
    {'Threshold','MeanExcess','Weight','WMSE','GPD_Shape','GPD_Scale','Events','Rate'});

MRL_output.Selection = table({''}, NaN, NaN, NaN, NaN,...
    'VariableNames',...
    {'Criterion', 'Threshold', 'id_Summary', 'Events', 'Rate'});

TH_selected = table;

if N>20

    %% Step 2: Estimate mean values of excesses
    mrl=NaN(N-10,8); %pre-allocation for speed
    % col(01): thresholds, u
    % col(02): mean excesses, e(u)
    % col(03): weights
    % col(04): weighted mean square errors
    % col(05): GPD shape parameter
    % col(06): GPD scale parameter
    % col(07): Number of events above threshold
    % col(08): Sample intensity or annual rate of events

    % Note: Looping up to N-10 as max threshold ensures a min of 10 excesses
    %   e(u) to calculate the conditional mean e(u).

    for i = 1:N-10 %threshold loop
        mrl(i,1) = th(i);                %Store threshold
        u = PEAKS(PEAKS(:,1)>th(i),1);   %Take sample of values above threshold
        mrl(i,2) = mean(u-th(i),'omitnan');     %Compute mean excess: difference between sample and threshold
        mrl(i,3) = (N-i)/var(u-th(i),'omitnan');%Compute weights: difference in rank normalized by variance of e(u)
    end

    % Note: Weights are used to acount for the increase in the estimation
    %   variance of e(u) with increasing threshold u. Under the assumption of
    %   independence of e(u).

    id = isinf(mrl(:,3))|isnan(mrl(:,3));%|(mrl(:,3)<=0);
    %     mrl(id,:) = [];

    x = mrl(:,1); %threshold, u
    y = mrl(:,2); %mean excess, e(u)
    w = mrl(:,3); %weights

    %% Step 3: Fit a linear model to (u,e(u)) using the weighted least squares
    % method and compute parameters of interest

    % Note: Looping up to N-20 as max threshold ensures a min of 10 conditional
    %   means e(u) for the linear regression.

    for j = 1:N-20

        %Fit GPD and take shape/scale parameters
        u = PEAKS(PEAKS(:,1)>th(j),1);

        try
            %Do linear regression
            mdl = fitlm(x(j:end),y(j:end),'Weights',w(j:end),'Exclude',id(j:end));
            %Note: if an error arises with the lack of data, enable the 'Exclude' option.

            %Compute weighted mean square error (WMSR) using fit residuals
            mrl(j,4) = mean(w(j:end).*(mdl.Residuals.Raw).^2,'omitnan');

            %Fit GPD and take parameters
            pd = fitdist(u,'gp','theta',th(j));
            mrl(j,5) = pd.k; %shape
            mrl(j,6) = pd.sigma;%scale
        catch
        end
    end

    %Estimate sample intensity for each threshold considered
    for k = 1:size(mrl,1)
        mrl(k,7) = sum(mrl(:,1)>mrl(k,1)); %no. of events
    end
    mrl(:,8)=mrl(:,7)./Nyrs; %lambda


    %% Step 4: Threshold selection: Minimum weighted MSE criterion
    mrl(isinf(mrl(:,4))|isnan(mrl(:,4))|mrl(:,4)==0,:)=[]; %delete values with WMSR=0

    % remove noise
    [~,~,H] = ksdensity(mrl(:,1)); H=H/7; %no difference found for values < 6
    [~,mrl(:,4)] = KernReg_LocalMean(mrl(:,1),mrl(:,4),H);

    %Identify local minima
    TH_id = islocalmin(mrl(:,4),'FlatSelection','first');

    % If no min found, return empty arrays
    if sum(TH_id)==0
        %Check: When no inflexion point exists, select the minimum available value
        % [~,TH_id] = min(mrl(:,4),[],'omitnan');
        return;
    end
    TH_id = find(TH_id);
    mrl2=mrl(TH_id,:); %take data of minima

    [~,I]=min(mrl2(:,1),[],'omitnan'); %select minimum threshold

    % Take results
    TH_selected = table;
    TH_selected.Criterion = {'CritWMSE'};
    TH_selected.Threshold = mrl2(I,1);
    TH_selected.id_Summary = TH_id(I);
    TH_selected.Events = mrl2(I,7);
    TH_selected.Rate = mrl2(I,8);


    %% Step 5: Threshold selection: Sample intensity (lambda) criterion

    % Select the minimum with nearly 2 events/year
    aux = mrl2(:,8)-2;
    aux(aux<-1) = NaN;
    [C,I] = min(abs(aux),[],'omitnan');

    if isempty(I)||isnan(C)||isempty(C)
        [~,I] = max(mrl2(:,8),[],'omitnan');
    end

    % Take results
    TH_selected.Criterion(2) = {'CritSI'};
    TH_selected.Threshold(2) = mrl2(I,1);
    TH_selected.id_Summary(2) = TH_id(I);
    TH_selected.Events(2) = mrl2(I,7);
    TH_selected.Rate(2) = mrl2(I,8);

    %% Step 6: Keep Requested Method
    switch GPD_TH_crit
        case 1 % Sample Intensity
            TH_selected = TH_selected(2, :);
        case 2 % WMSE Method
            TH_selected = TH_selected(1, :);
    end

    %% Store MRL output
    mrl = array2table(mrl,'VariableNames',{'Threshold','MeanExcess','Weight',...
        'WMSE','GPD_Shape','GPD_Scale','Events','Rate'});

    MRL_output.Summary=mrl;
    MRL_output.Selection=TH_selected;
end
end
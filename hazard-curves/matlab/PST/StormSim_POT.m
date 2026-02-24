%% StormSim_POT.m
%{
LICENSING:
    This code is part of StormSim software suite developed by the U.S. Army
    Engineer Research and Development Center Coastal and Hydraulics
    Laboratory (hereinafter “ERDC-CHL”). This material is distributed in
    accordance with DoD Instruction 5230.24. Recipient agrees to abide by
    all notices, and distribution and license markings. The controlling DOD
    office is the U.S. Army Engineer Research and Development Center
    (hereinafter, "ERDC"). This material shall be handled and maintained in
    accordance with For Official Use Only, Export Control, and AR 380-19
    requirements. ERDC-CHL retains all right, title and interest in
    StormSim and any portion thereof and in all copies, modifications and
    derivative works of StormSim and any portions thereof including,
    without limitation, all rights to patent, copyright, trade secret,
    trademark and other proprietary or intellectual property rights.
    Recipient has no rights, by license or otherwise, to use, disclose or
    disseminate StormSim, in whole or in part.

DISCLAIMER:
    STORMSIM IS PROVIDED “AS IS” BY ERDC-CHL AND THE RESPECTIVE COPYRIGHT
    HOLDERS. ERDC-CHL MAKES NO OTHER WARRANTIES WHATSOEVER EITHER EXPRESS
    OR IMPLIED WITH RESPECT TO STORMSIM OR ANYTHING PROVIDED BY ERDC-CHL,
    AND EXPRESSLY DISCLAIMS ALL WARRANTIES OF ANY KIND, EITHER EXPRESSED OR
    IMPLIED, INCLUDING WITHOUT LIMITATION, WARRANTIES OF MERCHANTABILITY,
    NON-INFRINGEMENT, FITNESS FOR A PARTICULAR PURPOSE, FREEDOM FROM BUGS,
    CORRECTNESS, ACCURACY, RELIABILITY, AND RESULTS, AND REGARDING THE USE
    AND RESULTS OF THE USE, AND THAT THE ASSOCIATED SOFTWARE’S USE WILL BE
    UNINTERRUPTED. ERDC-CHL DISCLAIMS ALL WARRANTIES AND LIABILITIES
    REGARDING THIRD PARTY SOFTWARE, IF PRESENT IN STORMSIM, AND DISTRIBUTES
    IT “AS IS.” RECIPIENT AGREES TO WAIVE ANY AND ALL CLAIMS AGAINST
    ERDC-CHL, THE UNITED STATES GOVERNMENT AND ITS CONTRACTORS AND
    SUBCONTRACTORS, AND SHALL INDEMNIFY AND HOLD HARMLESS ERDC-CHL, THE
    UNITED STATES GOVERNMENT AND ITS CONTRACTORS AND SUBCONTRACTORS FOR ANY
    LIABILITIES, DEMANDS, DAMAGES.

SOFTWARE NAME:
    StormSim-POT (Statistics)

DESCRIPTION:
   This script generates the Peaks-Over-Threshold (POT) sample from a raw
   time series data set.

INPUT ARGUMENTS:
    dt = timestamps of response data; as a datenum vector
    Resp = response data; specified as a vector. Cannot be a PDS/POT sample.
    tLag = inter-event time in hours; specified as a scalar
    lambda = mean annual rate of events; specified as a scalar
    Nyrs = record length in years; specified as a scalar

OUTPUT ARGUMENTS:
   POTout = response POT sample; as a matrix with format:
     col(01): timestamps of POT values
     col(02): POT values
     col(03): data time range used for selection of POT value: lower bound
     col(04): data time range used for selection of POT value: upper bound
   Threshold = selected threshold for identification of excesses.

AUTHORS:
    Norberto C. Nadal-Caraballo, PhD (NCNC)
    Efrain Ramos-Santiago (ERS)

CONTRIBUTORS:
    ERDC-CHL Coastal Hazards Group

HISTORY OF REVISIONS:
20200903-ERS: revised.
20200914-ERS: revised.
20231207-LAA: Revised to add noice to duplicate values in POT sample.

***************  ALPHA  VERSION  ***************  FOR TESTING  ************
%}
function [POTout,Threshold] = StormSim_POT(dt,Resp,tLag,lambda,Nyrs)
%% A few check points

% Required input
if nargin<5
    error('Missing input arguments: Received less than 5 input arguments.')
elseif nargin>5
    error('Too many input arguments: Function only requires 5 input arguments.')
end

% Reformat some inputs
if isrow(dt),dt=dt';end
if isrow(Resp),Resp=Resp';end

%% Set default and compute additional parameters
thMult = 1; %Default = 1; If threshold multiplier is set too low (e.g., ~0)
% an almost continuous time series will be created in Resp(index), with
% dLag <=48 hr and very few peaks will be identified

Nstm = 100000;
Resp_avg = mean(Resp); %arithmetic mean of response
Resp_std = std(Resp); %standard deviation of response
tLag = tLag/24;  %Convert inter-event time from hours to days

%% Determine the threshold that yields a required amount of peak response events
while Nstm > (Nyrs*lambda)
    
    % Compute threshold and identify response values above it
    Threshold = Resp_avg + Resp_std*thMult;
    index = find(Resp >= Threshold);
    
    % Take corresponding time values
    dt2 = dt(index);
    
    % Compute sample inter-event times
    dt2 = [1;diff(dt2)<=tLag;0];
    
    % Identify inter-event times longer than tLag
    id = find(dt2==0);
    
    % Compute amount of resulting events and increase the multiplier
    Nstm = length(id);
    thMult = thMult + 0.01;
end

%% Classify the response values

% NOTE:
%   stm_col has data indices; Resp_peak has response values; each column
%   has response events inside a time segment defined by the inter-event
%   time

stm_col = NaN(length(dt2),length(id));
stm_col(1:id(1)-1,1) = index(1:id(1)-1);
Resp_peak = NaN(length(dt2),length(id));
Resp_peak(1:id(1)-1,1) = Resp(index(1:id(1)-1));

id
for k = 2:length(id)
    id2 = id(k-1):id(k)-1
    stm_col(id2-(id(k-1)-1),k) = index(id2);
    Resp_peak(id2-(id(k-1)-1),k) = Resp(index(id2));
end

%% Extract peak response value for each event
[Pk_val,I] = max(Resp_peak,[],1,'omitnan');

%% Locate events inside arrays
ParINDEX = NaN(length(I),3);
for i=1:Nstm
    ParINDEX(i,1) = stm_col(I(i),i);
end
ParINDEX(:,2) = min(stm_col,[],1,'omitnan')';
ParINDEX(:,3) = max(stm_col,[],1,'omitnan')';

%% Extract timestamps of peak events and store results for output
POTout = dt(ParINDEX(:,1),1); %timestamp of peak event
POTout(:,2) = Pk_val'; %peak event

% Data time range used for selection of POT value:
POTout(:,3) = dt(ParINDEX(:,2),1); %lower bound
POTout(:,4) = dt(ParINDEX(:,3),1); %upper bound

%% Remove NaN / Inf / negative values
POTout(isnan(POTout(:,2))|isinf(POTout(:,2))|POTout(:,2)<=0,:)=[];

%% Add noise to duplicates in POT sample - LAA 2023/12/07
[~,w]=unique(POTout,'stable');
duplicate_indices=setdiff(1:numel(POTout),w);
POTout(duplicate_indices)=POTout(duplicate_indices)+1e-6;
%%

end
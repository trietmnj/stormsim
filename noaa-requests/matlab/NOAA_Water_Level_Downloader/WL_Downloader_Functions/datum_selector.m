%{
This function checks station offered vertical datums for data download and
selects the most appropiate based on preference order.
%}
function [datum,datum_p,flag2] = datum_selector(dStruct,requested_datum)
% Get Station Measured Products Datum List
dummy = {dStruct.datums.name}';
% Get Station Prediction Products Datum List
try
    dummyp = {dStruct.datums_predictions.name}';
    dummyp = 0;
catch
    dummyp = strcmp(dStruct.datums_predictions(1),'Great Lakes Gauge. No Tidal Predictions') | ...
        strcmp(dStruct.datums_predictions,'Not Found') ;
    if dummyp == 0
        dummyp = strcmp(dStruct.datums_predictions,'No Tidal Predictions');
    end
end
% Check Initial Datum Selection
if contains(requested_datum,'NAVD')
    prefered_datum = {'GL_LWD','NAVD88','MSL','MLLW'}; % Need to make exception for great lakes
else
    prefered_datum = {'GL_LWD','MSL','MLLW','NAVD88'}; % Need to make exception for great lakes
end
% Compute Logical Matrix (Columns Correspond To Cases In want)
logical_matrix = cell2mat(cellfun(@(c)strcmp(c,dummy),prefered_datum,'UniformOutput',false));% Compute Logical Matrix (Columns Correspond To Cases In want)
% Check if Station Is From Great Lakes
if sum(logical_matrix(:,1))==1 || dummyp == 1% If Station is Great Lakes
    datum = 'IGLD'; % Great Lakes Datum (IGLD or LWD)
    flag2 = 1; % Great Lakes Flag
else % Station is Not From Great Lakes
    flag2 = 0; % Great Lakes Flag
    for jj = 2:4 % Pick Prefered Datum
        if sum(logical_matrix(:,jj))==1
            datum = prefered_datum{jj};
            break;
        end
    end
end
% Case where measured datums where not found (STND)
if exist('datum','var')==0
    datum = 'STND';
end
% Check Tidal Predictions Datum
if flag2 == 1
    datum_p = 'No Tidal Predictions';
else
    if contains(requested_datum,'NAVD')
        dummy = {'NAVD88','MSL','MLLW'};
    else
        dummy = {'MSL','MLLW','NAVD88'};
    end
    % Compute Logical Matrix (Columns Correspond To Cases In want)
    logical_matrix = cell2mat(cellfun(@(c)strcmp(c,datum),dummy,'UniformOutput',false));% Compute Logical Matrix (Columns Correspond To Cases In want)
    % Pick Prefered Datum
    for jj = 1:3
        if sum(logical_matrix(:,jj))==1
            datum_p = dummy{jj};
            break;
        elseif sum(logical_matrix(:,jj))==0
            datum_p = 'Prefered Datums Not Found';
        end
    end
end
end
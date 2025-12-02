function [StationList] = StationList_updater_function(station_IDs)
%{
This function is used to update the date ranges available for the tide gauges as
NOAA CO-OPS changes Preliminary measurements to verified measurements.
%}

%% URL
% Station Inventory Page (in use)
inv_url = 'https://tidesandcurrents.noaa.gov/inventory.html?id=';
% Expand URL - Expand station metadata details (in use)
exp_url = 'https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/';
% Water Level Predictions Station Home Page
pred_url = 'https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=';
% Tidal Prediction Station Inventory
pred_inv = 'https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=tidepredictions';
%
mes_url = 'https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=waterlevels';

% Update historical and active label
options = weboptions('Timeout',300); % 5 minute timeout time suggested. Any less could result in error.
% Get Tidal Prediction Stations
tide_inventory = webread(pred_inv, options);
% Get Active Station Inventory
active_inventory = webread(mes_url, options);

%% Initialize Output Data Structure
StationList = struct('id',station_IDs,'name',station_IDs,'lon',station_IDs,...
    'lat',station_IDs,'state',station_IDs,...
    'datums',station_IDs,'datums_predictions',station_IDs,...
    'predictions_products',station_IDs,'WL_products',station_IDs,...
    'startDate',station_IDs,'endDate',station_IDs,...
    'active_indx',station_IDs);
% Initialize Timing
timing.t1 = datetime('now');

%% GET STATION DETAILS - WORKING WITH HTML SCRIPT
for ii = 1:length(StationList)
    disp(['Percent completion: ',num2str(round(ii/length(StationList),2)*100),' (',num2str(ii),'/',num2str(length(StationList)),')']);

    %% WATER LEVEL PRODUCTS
    % Datums
    [StationList] = water_level_datums(exp_url, options, StationList, ii);
    if iscell(StationList(ii).datums)
        StationList(ii).WL_products = {'Not Found'};
        StationList(ii).startDate = {'Not Found'};
        StationList(ii).endDate = {'Not Found'};
        StationList(ii).record_length = {'Not Found'};
    else
        % Products (Preliminary & Verified)
        [StationList] = water_level_products(StationList, inv_url,  options, ii);
        % Record Lengths
        [StationList] = record_length(StationList,ii);
    end
    % Water Level Predictions
    [StationList] = tidal_predictions_products_and_datums(StationList, station_IDs, tide_inventory, ii);
    % Inspect Station Status
    if any(strcmp(station_IDs(ii), {active_inventory.stations.id}))
        StationList(ii).active_indx = 1;
    else
        StationList(ii).active_indx = 0;
    end
end
timing.t2 = datetime('now');
timing.dt = timing.t2-timing.t1;
timing.runtime = char(timing.t2-timing.t1);
end
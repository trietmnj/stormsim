function [StationList] = tidal_predictions_products_and_datums(StationList, station_IDs, tide_inventory, ii)
if StationList(ii).greatlakes ==  1
    % Great Lakes Don't Have Tidal Predictions
    StationList(ii).datums_predictions = 'Great Lakes Gauge. No Tidal Predictions';
    StationList(ii).predictions_products = 'Great Lakes Gauge. No Tidal Predictions';
else
    % Find Tidal Prediction ID
    tIndx = strcmp(station_IDs(ii, :), {tide_inventory.stations.id});
    % If Station Is Found
    if any(tIndx)
        % Define Tidal Prediction Datums
        StationList(ii).datums_predictions = StationList(ii).datums;
        % Define Intervals According To Tidal Prediction Type
        if strcmp(tide_inventory.stations(tIndx).type, 'S') % Subordinate Stations
            StationList(ii).predictions_products = struct('value',...
                {'hilo';'hi';'lo'},...
                'description',...
                {'High/Low';'High Only';'Low Only'});
        elseif strcmp(tide_inventory.stations(tIndx).type, 'R') % Harmonic
            StationList(ii).predictions_products = struct('value',...
                {'1';'6';'15';'30';'h';'hilo';'hi';'lo'},...
                'description',...
                {'1 min';'6 min';'15 min';'30 min';'1 hour';'High/Low';'High Only';'Low Only'});
        end
    else
        StationList(ii).datums_predictions = {'Not Found'};
        StationList(ii).predictions_products = {'Not Found'};
    end
end
end
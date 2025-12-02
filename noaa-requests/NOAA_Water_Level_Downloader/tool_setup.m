function [Station_inventory] = tool_setup(config)

%% LOAD NOAA STATION INVENTORY (Historical + Active)
% Load Station Inventory
% Historical stations - includes historical + active (in use)
hist_url = 'https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=historicwl';
options = weboptions('Timeout',300); % 5 minute timeout time suggested. Any less could result in error.
Station_inventory = webread(hist_url,options); % This includes historical and active stations
Station_inventory = Station_inventory.stations;
% Active Stations
mes_url = 'https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=waterlevels';
% Get Active Station Inventory
active_inventory = webread(mes_url, options);
active_inventory = active_inventory.stations;
% Verify If Any Active Stations Aren't Present On Historical Record
missing_indx = ~contains({active_inventory.id}, {Station_inventory.id});
% Append Missing Stations
if any(missing_indx)
    Station_inventory = [Station_inventory; active_inventory(missing_indx)];
end
% Define Active Index
active_indx = contains({Station_inventory.id}, {active_inventory.id});
active_str = repmat({'historical'}, size(active_indx));
active_str(active_indx) = {'active'};
% Add Active Index To Station Inventory
for kk = 1:length(Station_inventory)
    Station_inventory(kk).active_indx = active_str(kk);
end

%% SELECT DESIRED STATIONS
switch config.selectionType
    case 0
        id = 1:length(Station_inventory);
    case 1 % By station Id
        % Filter By Station ID
        id = cell2mat(cellfun(@(x) find(strcmp(x,{Station_inventory.id}')==1),config.stationIDs,'UniformOutput',false));
    case 2 % By State
        % Filter By Station ID
        id = cell2mat(cellfun(@(x) find(strcmp(x,{Station_inventory.state}')==1),config.state,'UniformOutput',false));
    case 3 % Inside Polygon (CSV)
        % Import File With X Y Coords
        dummy = readmatrix(config.csvPoly.FileName);
        xv = dummy(:,1);
        yv = dummy(:,2);
        % Define Polygon
        pgon = polyshape(xv,yv,'Simplify',false);
        % Get Longitude Query Points
        xq = cell2mat({Station_inventory.lng}');
        % Get Latiitude Query Points
        yq = cell2mat({Station_inventory.lat}');
        % Find Sations Inside Specified Domain
        in = inpolygon(xq,yq,xv,yv);
        % Get Indexes
        id = find(in==1);
    case 4 % Inside Polygon (Write In)
        % Longitude Values
        xv = config.xPoly;
        % Latitude Values
        yv = config.yPoly;
        % Define Polygon
        pgon = polyshape(xv,yv,'Simplify',false);
        % Get Longitude Query Points
        xq = cell2mat({Station_inventory.lng}');
        % Get Latiitude Query Points
        yq = cell2mat({Station_inventory.lat}');
        % Find Sations Inside Specified Domain
        in = inpolygon(xq,yq,xv,yv);
        % Get Indexes
        id = find(in==1);
end

%% EXTRACT STATIONS BY FILTERING
Station_inventory = Station_inventory(id);

%% FILTER Historicals Out
if config.hist_stations==0
    Station_inventory = Station_inventory(strcmp([Station_inventory.active_indx],'active'));
end

%% PLOT
if config.plot == 1
    ax = geoaxes('Basemap','satellite');
    hold on;
    geoscatter(ax,[Station_inventory.lat],[Station_inventory.lng],20,1:length([Station_inventory.lng]),'filled');
    geoplot(ax,yv,xv,'-r','LineWidth',2);
end
end
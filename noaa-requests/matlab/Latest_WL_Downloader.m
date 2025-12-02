clc;clear all;

%% USER INPUTS
% Define Station Selection Type
config.selectionType = 3;% 1 - By Station ID, 2 - By State, 3 - Inside Polygon (CSV), 4 - Inside Polygon (Write In)
% Define Station IDs (Only Fill If selectionType == 1)
config.stationIDs = {}; % {'8534720','8531680','8467150'}
% Define State Of Interest (Only Fill If selectionType == 2)
config.state = {}; % {'TX'}
% Define (X,Y) CSV File Containing Polygon Coordinates [deg] (Only Fill If selectionType == 3)
config.csvPoly.FileName = fullfile('Ian_Bounding_Box.csv');%  'Lake_Ontario_Polyshape.csv' (Full Path To CSV File Containing Polygon Shape @ WGS84)
config.csvPoly.hasHeaders = 0; % Logical Value (1 - config.csvPoly.FileName has headers, 0 - No headers)
config.csvPoly.LonColID = 1; % Column ID For Horizontal Cordinate In config.csvPoly.FileName (Longitude [deg])
config.csvPoly.LatColID = 2; % Column ID For Vertical Cordinate In config.csvPoly.FileName (Latitude [deg])
% Define Polygon X Coordinates [Deg] (Only Fill If selectionType == 4)
config.xPoly = [];% [-92.62865073 -95.21460616 -96.4885695 -98.98054196	-98.46606484 -96.79516928 -94.8074547 -92.45348807 -92.62865073]
% Define Polygon Y Coordinates [Deg] (Only Fill If selectionType == 4)
config.yPoly = [];% [28.8704919 27.42873312	24.81703777	25.07095063	27.27673696	29.02263057	30.2874184	30.92015438	28.8704919]
% Include Historical
config.hist_stations = 0;
% Plot Selected Stations
config.plot = 0;
% Desired product {'Verified Hourly Height Water Level','Verified 6-Minute Water Level','Verified Monthly Mean Water Level','Preliminary 6-Minute Water Level'};
config.prod = {'Preliminary 6-Minute Water Level'};
% Operational Mode
config.opMode = 2;% (1 - Full Record, 2 - Specific Date
% Dates of interest (Only if opMode == 2)
config.dBeg = datenum(2022,9,11,0,0,0);
config.dEnd = datenum(2022,9,26,23,0,0);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%------------------------------- NO CHANGES BEYOND THIS POINT --------------------------------
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% ADD DEPENDENCIES
addpath(genpath('Functions'));

%% RUN TOOL SETUP
[StationList] = tool_setup(config);

%% UPDATE STATION DATA INVENTORY
% Scans Station Data Inventory HTML Code To Update Data Availability
[StationList] = StationList_updater_function(StationList);

% ax = geoaxes('Basemap','satellite');
% hold on;
% geoscatter(ax,[StationList.lat],[StationList.lon],20,1:length([StationList.lon]),'filled');
% geoplot(ax,yv,xv,'-r','LineWidth',2);

%% DOWNLOAD/LOAD DATA FOR STATIONS
% Download Specified Product @ Specified Datum (Only supports MSL or NAVD88)
[Sdata,notFound] = WL_downloader_V2({StationList.id},StationList,'MSL',config.prod,config.opMode,config.dBeg,config.dEnd);

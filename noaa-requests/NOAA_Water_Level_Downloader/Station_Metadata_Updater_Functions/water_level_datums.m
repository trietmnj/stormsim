function [StationList] = water_level_datums(exp_url,options,StationList,ii)
% Read Station Metadata
[dummy] = station_metadata_reader(StationList, exp_url, options, ii);
%
if ~isempty(dummy)
    % Reformat Metadata Structure
    dummy = dummy.stations;
    % Assign station details
    StationList(ii).datums = dummy.datums.datums; % Station available datums
    StationList(ii).greatlakes = dummy.greatlakes; % Station available datums
    StationList(ii).name = dummy.name; % Station available datums
    StationList(ii).lon = dummy.lng; % Station available datums
    StationList(ii).lat = dummy.lat; % Station available datums
    StationList(ii).state = dummy.state; % Station available datums
    % For loop for converting datum values from ft to m
    for jj = 1:length(StationList(ii).datums)
        StationList(ii).datums(jj).value = StationList(ii).datums(jj).value/3.28084; % 1 m = 3.28084 ft
    end
    % Check if station measured datums are empty
    dummy = isempty(StationList(ii).datums);
    % If it is empty fill out empty structure row with Station datum
    if dummy == 1
        StationList(ii).datums.name = 'STND'; % datum name
        StationList(ii).datums.description = 'Station Datum'; % datum description
        StationList(ii).datums.value = 0; % Datum value (vertical offset)
    end
else
    StationList(ii).datums = {'Not Found'};
    StationList(ii).greatlakes = 0;
    StationList(ii).name = {'Not Found'};
    StationList(ii).lon = {'Not Found'};
    StationList(ii).lat = {'Not Found'};
    StationList(ii).state = {'Not Found'};
end
end
%{
This function reads the metadata for the specified station.
%}
function [metadata] = station_metadata_reader(inventory,exp_url,options,ii)
% Get station ID
station = inventory(ii).id;
% Generate station url
url = [exp_url station '.json?expand=details,products,datums&units=metric'];
ctr2=1; % While loop trigger
while ctr2<=8
    try
        % Read URL
        metadata = webread(url,options);
        ctr2=9; % URL was read successfuly exit while loop
    catch % if URL could not be read try again
        ctr2=ctr2+1; % increment the try counter
        pause(5); % This pause is to prevent timeout errors due to heavy traffic in NOAA CO-OPS server
        if ctr2==8 % If maximum amount of tries is reached URL could not be found, throw and error
            % if you want this script to just skip the invalid station and
            % not throw an error uncomment the following line
            % continue;
            metadata = [];
            %             error(['Webread timeout, check connection status or station inventory homepage. ' newline ...
            %                 'Error on function: stationlist_product_filter at index: ',num2str(ii),'.' newline 'station id: ',station,''])
        end
    end
end
end
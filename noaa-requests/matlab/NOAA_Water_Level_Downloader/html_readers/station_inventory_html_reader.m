
function [html_code,flag] = station_inventory_html_reader(StationList,inv_url,options,ii)
indx=[];
% Get station id
station = StationList(ii).id;
% Build station data inventory URL
url = [inv_url station];
% Read HTML script
ctr=1;flag=0;
while isempty(indx)==1 % SOMETIMES HTML CODE GETS CUT SHORT SO JUST KEEP ITERATING UNTIL IT FINDS THE STR- DONT KNOW WHY
   % Using try to componsate for timeout error due to connection instability
   try
        html_code = webread(url,options);
        % Find index of dates available
        indx = strfind(html_code,'data.push({''start''');
    catch ME
        % Host URL is unreacheable or does not exist
        if strcmp(ME.identifier,'MATLAB:webservices:UnknownHost')==1
            flag=1;
            return;
        end
        indx =[];% Define indx as empty value to stay within while loop
        ctr=ctr+1;% Try counter
        pause(10)
        if ctr>8
            flag = 1; % Station inventory home page was not found. This station will be eliminated.
            return;
            %            error(['Webread timeout, check connection status or station inventory homepage. ' newline ...
            %                'Error on function: station_inventory_html_reader at index: ',num2str(ii),'.' newline 'station id: ',station,''])
        end
    end
    ctr=ctr+1;% Try counter
    if ctr>8
        flag = 1; % Station inventory home page was not found. This station will be eliminated.
        return;
    end
end
% Eliminate everything above
html_code = html_code(indx(1):end);
% Find the end of line containing dates info
indx = strfind(html_code,'var station_name');
% Elminate everything below
html_code = html_code(1:indx(1)-1);
end
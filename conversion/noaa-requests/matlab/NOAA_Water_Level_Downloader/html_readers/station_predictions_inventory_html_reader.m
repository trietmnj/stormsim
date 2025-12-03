function [html_code] = station_predictions_inventory_html_reader(StationList,pred_url,options,ii)
%{
This function reads html code from NOAA CO-OPS tidal predictions webpage and
cuts any characters above datum lsiting.
%}

%% DEFINE AUXILIARY VARIABLES 
% Get station id 
station = StationList(ii).id;
% Initialize vars & counters 
indx=[];ctr=1;

%% LOOK FOR STRING PATTERNS 
while isempty(indx)==1 % SOMETIMES HTML CODE GETS CUT SHORT SO JUST KEEP ITERATING UNTIL IT FINDS THE STR- DONT KNOW WHY
    try % Using try to compensate for timeout error due to connection instability 
        % read webpage
        html_code = webread([pred_url station],options);
        % Find index of datums available
        indx = strfind(html_code,'<select name="datum" style');
    catch
        indx =[];% Define indx as empty value to stay within while loop
        ctr=ctr+1;% Try counter 
        pause(10);% This pause is to prevent timeout errors due to heavy traffic in NOAA CO-OPS server
        if ctr>4
           error(['Webread timeout, check connection status or station inventory homepage. ' newline ...
               'Error on function: station_predictions_inventory_html_reader at index: ',num2str(ii),'.' newline 'station id: ',station,''])    
        end
    end
end
% Clear everything above 
html_code = html_code(indx:end);
end
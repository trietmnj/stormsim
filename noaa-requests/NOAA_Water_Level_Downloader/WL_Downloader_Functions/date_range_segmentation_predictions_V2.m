%{
This function is responsible for segmenting the available data . 
The reason for this is that NOAA CO-OPS stablishes certain limits to the amount
of data that can be pulled at once depending on the product. For tidal
predictions the products offered can be: hourly, 30 min, 15 min, 6 min, 1 min,
High/Low, High only, Low only. All products are subject to a 31 days limit for
data download.
%}
function [stDates,endDates] = date_range_segmentation_predictions_V2(dStruct,indx)
% Define dt Based On Product Available
dt_s = datenum(0,0,30,0,0,0); % Suggested dt 
% Get Station Start & End Date
stDates = dStruct.startDate(indx(1));
endDates = dStruct.endDate(indx(end));
jj=1;
% Check If Suggested dt (dt_s) Is Appropiate
     % Create Download Time Vector With Suggested dt
    dummy = datenum(stDates{jj}(1:end-4),'yyyy-mm-dd HH:MM:SS'):dt_s:datenum(endDates{jj}(1:end-4),'yyyy-mm-dd HH:MM:SS');
    % Check If Final Date Coincides With Station End Date
    logical = dummy(end) == datenum(endDates{jj}(1:end-4),'yyyy-mm-dd HH:MM:SS');
    % If End Dates Dont Coincide Fix The Issue
    if logical == 0
        dt_c = datenum(endDates{jj}(1:end-4),'yyyy-mm-dd HH:MM:SS')-dummy(end); % Corrected dt
        dummy(end+1) = dummy(end)+dt_c; % Add Missing Date
    end
    % Assign To Corresponding Vars
    dummy2 = cellstr(datestr(dummy(1:end-1),'yyyymmdd HH:MM'));
    dummy3 = cellstr(datestr(dummy(2:end),'yyyymmdd HH:MM'));

% Rename Vars
stDates{jj} = dummy2; % Download Date Range Start (yyyymmdd HH:MM)
endDates{jj} = dummy3; % Download Date Range End (yyyymmdd HH:MM)

end
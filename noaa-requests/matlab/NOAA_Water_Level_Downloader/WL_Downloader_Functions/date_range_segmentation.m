%{
This function is responsible for segmenting the available data into segments. 
The reason for this is that NOAA CO-OPS stablishes certain limits to the amount
of data that can be pulled at once depending on the product.
%}
function [stDates,endDates] = date_range_segmentation(dStruct,flag1,indx)
% Define dt Based On Product Available
if strcmp(flag1,'6')==1 || strcmp(flag1,'6p')==1 % 6 min measurements can be downloaded 30 days at a time
    dt_s = datenum(0,0,30,0,0,0); % Suggested dt
else % hourly measurements can be downloaded 364 days at a time (HiLo works the same)
    dt_s =  datenum(0,0,364,0,0,0); % Suggested dt
end
% Get Station Start & End Date
stDates = dStruct.startDate(indx);
endDates = dStruct.endDate(indx);
% Check If Suggested dt (dt_s) Is Appropiate
for jj = 1:length(stDates)
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
end
function [stDates,endDates,stDatesp,endDatesp] = download_segmentation(dStruct,flag1,indx)    
%% DIVIDE DATE RANGE IN ALLOWED SEGMENTS
    if strcmp(flag1,'m')==0
        % Water Level measurements segmentation
        [stDates,endDates] = date_range_segmentation(dStruct,flag1,indx);
    else
        % Monthly data does not have a data download limit hence date segmentation
        % is not necessary
        % Get date ranges
        stDates = dStruct.startDate(indx);
        endDates = dStruct.endDate(indx);
        % Cut date strings
        stDates = cellfun(@(x) x(1:19), stDates, 'un', 0);
        endDates = cellfun(@(x) x(1:19), endDates, 'un', 0);
        % Reformat date ranges for API
        stDates = datestr(datenum(stDates,'yyyy-mm-dd HH:MM:SS'),'yyyymmdd HH:MM');
        endDates = datestr(datenum(endDates,'yyyy-mm-dd HH:MM:SS'),'yyyymmdd HH:MM');
    end
    
    % Tidal predictions segmentation
    [stDatesp,endDatesp] = date_range_segmentation_predictions_V2(dStruct,indx);
    %         [stDatesp,endDatesp] = date_range_segmentation_predictions(dStruct,indx);
end

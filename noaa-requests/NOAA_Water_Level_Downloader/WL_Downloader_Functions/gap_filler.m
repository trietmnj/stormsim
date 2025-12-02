function [data] = gap_filler(data,stDates,endDates,flag1,jj)
if jj > 1
    if strcmp(flag1,'m')==0
        % Get Final Time Stamp of Previous Segmentation
        uBound = datenum(endDates{jj-1}(end,:),'yyyymmdd HH:MM');
        % Get Initial Time Stamp of Actual Segmentation
        lBound = datenum(stDates{jj}(1,:),'yyyymmdd HH:MM');
    else
        % Assuming monthly products allways start the first of the month
        % Get Final Time Stamp of Previous Segmentation
        uBound = data.DateTime(end);
        % Get Initial Time Stamp of Actual Segmentation
        lBound = datetime(stDates(jj,:),'InputFormat','yyyyMMdd HH:mm','Format','yyyy-MM-dd HH:mm');
    end
    % Compute missing data points
    if strcmp(flag1,'1')==1 || strcmp(flag1,'hilo')==1 % Hourly
        % Define timestep
        dt = datenum(0,0,0,1,0,0);
        % Create datetime vector
        DateTime = datetime(datestr([uBound:dt:lBound]','yyyy-mm-dd HH:MM'),...
            'InputFormat','yyyy-MM-dd HH:mm','Format','yyyy-MM-dd HH:mm');
        % Eliminate uBound value
        DateTime = DateTime(2:end);
        % Create NaN vector
        WaterLevel = NaN(size(DateTime));
        % Create fill table
        gap_mat = table(DateTime,WaterLevel);
    elseif strcmp(flag1,'6')==1 || strcmp(flag1,'6p')==1 % 6 minutes
        % Define timestep
        dt = datenum(0,0,0,0,6,0);
        % Create datetime vector
        DateTime = datetime(datestr([uBound:dt:lBound]','yyyy-mm-dd HH:MM'),...
            'InputFormat','yyyy-MM-dd HH:mm','Format','yyyy-MM-dd HH:mm');
        % Eliminate uBound value
        DateTime = DateTime(2:end);
        % Create NaN vector
        WaterLevel = NaN(size(DateTime));
        % Create fill table
        gap_mat = table(DateTime,WaterLevel);
    elseif strcmp(flag1,'m')==1 % Monthly
        % Define timestep
        dt = calmonths(1);
        % Create datetime vector
        DateTime = [uBound:dt:lBound]';
        % Eliminate uBound value
        DateTime = DateTime(2:end);
        % Create NaN vector
        WaterLevel = NaN(size(DateTime));
        % Create fill table
        gap_mat = table(DateTime,WaterLevel);
    end
    % Cat NaN table with data table
    data = [data;gap_mat];
end
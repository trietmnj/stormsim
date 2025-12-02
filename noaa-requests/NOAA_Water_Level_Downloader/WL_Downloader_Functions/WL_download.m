%{
This function is responsible for downloading WL mwasurements from NOAA CO-OPS
server.
%}
%% BUILD URL & DOWNLOAD MEASURED DATA
function [Sdata] = WL_download(ii,Sdata,datum,station,timezone,units,format,stDates,endDates,gen_url,options,flag1)
data=[];
% For Loop length (Monthly product code does not work with cell arrays)
 if strcmp(flag1,'m')==0
     Lend = length(stDates);
 else 
     Lend = length(stDates(:,1));
 end

for jj = 1:Lend
    %% NAN GAP FILLER
    [data] = gap_filler(data,stDates,endDates,flag1,jj);
    
    %% DATA DOWNLOAD
    if strcmp(flag1,'m')==0
        %% hourly and 6 minutes data
        for kk = 1:length(stDates{jj})
            if strcmp(flag1,'6')==1 || strcmp(flag1,'6p')==1 
                % 6 Minute WL Measurements API
%                 wl6mn_api = ['/api/datagetter?product=water_level&application=NOS.COOPS.TAC.WL&begin_date=',stDates{jj}{kk},...
%                     '&end_date=',endDates{jj}{kk},'&datum=',datum,'&station=',station,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
                wl6mn_api = ['/api/prod/datagetter?product=water_level&application=NOS.COOPS.TAC.WL&begin_date=',stDates{jj}{kk},...
                    '&end_date=',endDates{jj}{kk},'&datum=',datum,'&station=',station,'&time_zone=',timezone,'&units=',units,'&format=',format,''];

                % Cat URL
                URL = [gen_url wl6mn_api];
                % Donwload data
                try
                    wltable = webread(URL,options);                        
                catch
                    wexit = 0;
                    while wexit==0
                        pause(3);
                        try
                            dmmy=0;
                            wltable = webread(URL,options);
                        catch
                            dmmy = 1;
                        end
                        if dmmy==0
                            wexit = 1;
                        end
                    end
                end
            elseif strcmp(flag1,'1')==1
                % 1 Hour WL Measurements API
                wl1hr_api = ['/api/prod/datagetter?product=hourly_height&application=NOS.COOPS.TAC.WL&begin_date=',stDates{jj}{kk},...
                    '&end_date=',endDates{jj}{kk},'&datum=',datum,'&station=',station,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
                % Cat URL
                URL = [gen_url wl1hr_api];
                % Download data
                wltable = webread(URL,options);
            elseif strcmp(flag1,'hilo')==1
                              % 1 Hour WL Measurements API
                wl1hr_api = ['/api/prod/datagetter?product=high_low&application=NOS.COOPS.TAC.WL&begin_date=',stDates{jj}{kk},...
                    '&end_date=',endDates{jj}{kk},'&datum=',datum,'&station=',station,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
                % Cat URL
                URL = [gen_url wl1hr_api];
                % Download data
                wltable = webread(URL,options);  
            end
            % Temporary failsafe - got empty table when there is data in
            % record 
             if isempty(wltable)==1 || width(wltable)>5
                 uBound = datenum(stDates{jj}{kk},'yyyymmdd HH:MM');
                 % Get Initial Time Stamp of Actual Segmentation
                 lBound = datenum(endDates{jj}{kk},'yyyymmdd HH:MM');
                 % Define timestep
                 if contains(flag1,'6')==1
                     dt = datenum(0,0,0,0,6,0);
                 else
                     dt = datenum(0,0,0,1,0,0);
                 end
                 % Create datetime vector
                 DateTime = datetime(datestr([uBound:dt:lBound]','yyyy-mm-dd HH:MM'),...
                     'InputFormat','yyyy-MM-dd HH:mm','Format','yyyy-MM-dd HH:mm');
                 % Eliminate uBound value
                 DateTime = DateTime(2:end);
                 % Create NaN vector
                 WaterLevel = NaN(size(DateTime));
                 % Create fill table
                 wltable = table(DateTime,WaterLevel);
             end
             ['Station: ',station,' WL Measurements: ',num2str(jj),'/',num2str(Lend),' Segmentation: ',num2str(kk),'/',num2str(length(stDates{jj})),'']
            % Cat downloaded data chunk
            data = [data;wltable(:,1:2)];
        end
    else
        %% Monthly data only
        % Monthly WL Measurements API
        wlm_api = ['/api/prod/datagetter?product=monthly_mean&application=NOS.COOPS.TAC.WL&begin_date=',stDates(jj,:),...
            '&end_date=',endDates(jj,:),'&datum=',datum,'&station=',station,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
        % Cat URL
        URL = [gen_url wlm_api];
        % Download data
        wltable = webread(URL,options);
        %% MONTHLY DATE VECTOR FORMATER
        % Counters and triggers
        dd=0;ctr=1;ctr2=1;
        % Clear vars
        clearvars('DateTime','WaterLevel');
        % Conversion while loop
        if height(wltable)==1
                    % Date assignment and formating
                DateTime(1,1) = datetime(wltable.Year(1),wltable.Month(1),1,'Format','yyyy-MM-dd HH:mm');
                % Water level assignment
                WaterLevel(1,1) = wltable.MSL(1);
        else
        while dd==0
            % Define if triggers
            chk = wltable.Month(ctr2);
            chk2 = wltable.Month(ctr2+1);
            % If data is continous assign date to new vector
            if chk2-chk==1 || chk2-chk==-11
                % Date assignment and formating
                DateTime(ctr,1) = datetime(wltable.Year(ctr2),wltable.Month(ctr2),1,'Format','yyyy-MM-dd HH:mm');
                % Water level assignment
                WaterLevel(ctr,1) = wltable.MSL(ctr2);
                % Counter increments
                ctr2=ctr2+1;
                ctr=ctr+1;
            else
                % If data is not continous add missing dates
                % Assing last date before finding gap
                DateTime(ctr,1) = datetime(wltable.Year(ctr2),wltable.Month(ctr2),1,'Format','yyyy-MM-dd HH:mm');
                WaterLevel(ctr,1) = wltable.MSL(ctr2);
                ctr=ctr+1;
                % Compute how many months need to be filled in
                dc = split(between(datetime(wltable.Year(ctr2),wltable.Month(ctr2),1),...
                    datetime(wltable.Year(ctr2+1),wltable.Month(ctr2+1),1)),'months');
                % Loop corrector
                for ll = 1:dc-1
                    DateTime(ctr,1) = datetime(wltable.Year(ctr2),wltable.Month(ctr2)+ll,1,'Format','yyyy-MM-dd HH:mm');
                    WaterLevel(ctr,1) = NaN(1,1);
                    ctr=ctr+1;
                end
                % Increment counter
                ctr2=ctr2+1;
            end
            % While exit condition
            if ctr2==height(wltable)
                % Define exit trigger
                dd=1;
                % Assign lasta data point
                DateTime(ctr,1) = datetime(wltable.Year(ctr2),wltable.Month(ctr2),1,'Format','yyyy-MM-dd HH:mm');
                WaterLevel(ctr,1) = wltable.MSL(ctr2);
            end
        end
        end
        % Cat downloaded data chunk
        data = [data;table(DateTime,WaterLevel)];
    end
end

%% REMOVE DUPLICATE POINTS (MEASUREMENTS)
Sdata(ii).WL = data;
[~,uIndx] = unique(Sdata(ii).WL(:,1),'last');
Sdata(ii).WL = Sdata(ii).WL(uIndx,:);
end
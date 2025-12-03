%{
Data download script

IMPORTANT: IF STATION IS NOT PRESENT ON DATA STRUCTURE StationList

Prodcut download limit per request
Predictions:
31 days (no matter the interval of the product)
Water Level Measurements:
31 days (6-minute product)
365 days (hourly product)
none (monthly or peaks data)

Flag Legend:
flag1 - defines the WL product that is selected ( hourly - '1', 6 min - '6', monthly - 'm' )
flag2 - indicates if station is in the great lakes hence there are no tidal predictions.
 (1 - station is on great lakes, 0 - stations is not on great lakes)
flag3 - indicates if tidal predictions product is high/low (bad) or not (0 -
prefered data interval was found)
-----------------------------------------------------------------------------------------------
EDIT HISTORY:
User        Date        Description
FGM      25/09/2019     Fixed filtering issues discarding tidal stations
FGM      26/10/2019     Added the functionality of donwloading monthly products
FGM       3/10/2019     Fixed filtering issues discarding tidal stations
FGM       5/10/2019     Added record length calculator for downloaded product and NaN gap filler
FGM       7/10/2019     Added the capacity of downloading multiple products at once
FGM       9/10/2019     Tested and vaidated new functionalities
FGM       16/10/2019    Added try/catch statement to datum_selector.m (Great Lakes case)
FGM       16/10/2019    Added if statement to prediction_interval_selector.m (Great Lakes case)
FGM       16/10/2019    Added if statement for vector length check
FGM       20/10/2019    Added failsafe to WL_measurements_product_selector_V2. (flag4)
%}
function [Sdata,notFound] = WL_downloader_V2(idList,StationList,requested_datum,prod,opMode,dBeg,dEnd) %% ADD PATHS
    if ~ismember(opMode,1:2)
        error('Please use a valid operational mode (1 - full record, 2 - Specific Date)');
    end
    %% START TIMER
    timing2(1).t1 = datetime('now');
    
    
    %% ADD PATHS
    addpath(genpath('NOAA_Download_Functions/'));
    
    %% DEFINE INITIAL VARIABLES
    % Prefered Datum for Data Download
    datum = 'MSL';
    % Prefered Time Zone for Data Download
    timezone = 'GMT';
    % Prefered Units for Data Download
    units = 'metric';
    % Download Data Format
    format = 'csv';
    % NOAA CO-OPS URL
    gen_url = 'https://api.tidesandcurrents.noaa.gov';
    % 5 minute timeout for webread
    options = weboptions('Timeout',800);
    
    %% Check if stations are in inventory
    % Compute Logical Matrix (Columns Correspond To Cases In want)
    logical_matrix = cell2mat(cellfun(@(c)strcmp(c,{StationList.id}'),idList,'UniformOutput',false));
    % Find Matching Stations
    [mx,mindx] = max(logical_matrix,[],1);
    % Single out stations that were not found in StationList
    notFound = idList(mx==0);
    % Create valid station id list
    idList =  {StationList(mindx(mx==1)).id};
    
    %% INITIALIZE COUNTER
    ctr=1;
    
    %% DOWNLOAD DATA FOR EACH STATION
    for ii = 1:length(idList)
        ['------------------ ',num2str(ii),' / ',num2str(length(idList)),' ---------------------']
        for pp = 1:length(prod)
            %% EXTRACT STATION FROM DATA STRUCTURE
            % Get Station ID
            station = idList{ii};
            % Get All Fields for Station
            dStruct = StationList(strcmp(station,{StationList.id}')==1);
            % Assign relevant data to new data structure
            Sdata(ctr).id = station;
            Sdata(ctr).name = dStruct.name;
            Sdata(ctr).lon = dStruct.lon;
            Sdata(ctr).lat = dStruct.lat;
            Sdata(ctr).state = dStruct.state;
            
            %% CHECK WL MEASUREMENTS PRODUCTS AVAILABLE
            [flag4,flag1,indx] = WL_measurements_product_selector_V2(dStruct,prod(pp));
            %     [flag1,indx] = WL_measurements_product_selector(dStruct);
            if flag4==1
                Sdata(ctr).WL_datum = 'Not found';
                Sdata(ctr).TP_datum = 'Not found';
                Sdata(ctr).WL_downloaded_product = 'Not found';
                Sdata(ctr).TP_downloaded_product = 'Not found';
                Sdata(ctr).record_length = 'Not found';
                Sdata(ctr).WL = 'Not found';
                Sdata(ctr).TP = 'Not found';
                ctr=ctr+1;
            else
                %% CHECK IF DATE RANGE OF INTEREST IS AVAILABLE
                if opMode == 2
                    [indx, dEnd, dBeg, dummy3] = date_search(dStruct,dBeg,dEnd,indx);
                    if isempty(dummy3)
                        dStruct.startDate(indx) = {[datestr(dBeg,'yyyy-mm-dd HH:MM:SS'),' GMT']};
                        dStruct.endDate(indx) = {[datestr(dEnd,'yyyy-mm-dd HH:MM:SS'),' GMT']};
                    else
                        Sdata(ctr).WL_datum = 'Not found';
                        Sdata(ctr).TP_datum = 'Not found';
                        Sdata(ctr).WL_downloaded_product = 'Not found';
                        Sdata(ctr).TP_downloaded_product = 'Not found';
                        Sdata(ctr).record_length = 'Not found';
                        Sdata(ctr).WL = 'Not found';
                        Sdata(ctr).TP = 'Not found';
                        ctr=ctr+1;
                        continue;
                    end
                end
                %% DIVIDE DATE RANGE IN ALLOWED SEGMENTS
                [stDates,endDates,stDatesp,endDatesp] = download_segmentation(dStruct,flag1,indx);
                
                %% CHECK DATUM AVAILABILITY
                [datum, datum_p] = datum_selector(dStruct,requested_datum);
                
                %% CHECK TIDAL PREDICTIONS INTERVALS
                [interval,flag3] = prediction_interval_selector(dStruct,flag1, dStruct.greatlakes);
                
                %% ASSIGN INFO TO Sdata
                % Selected Datum For Measurements
                Sdata(ctr).WL_datum = datum;
                % Selected Datum For Predictions
                Sdata(ctr).TP_datum = datum_p;
                % Selected Product For Measurement
                if strcmp(flag1,'6')==1
                    Sdata(ctr).WL_downloaded_product = '6 minutes';
                elseif  strcmp(flag1,'1')==1
                    Sdata(ctr).WL_downloaded_product = 'hourly';
                elseif strcmp(flag1,'6p')==1
                    Sdata(ctr).WL_downloaded_product = '6 minutes preliminary';
                elseif strcmp(flag1,'hilo')==1
                    Sdata(ctr).WL_downloaded_product = 'High/Low';
                else
                    Sdata(ctr).WL_downloaded_product = 'monthly';
                end
                % Slected Product For Predictions
                Sdata(ctr).TP_downloaded_product = interval;
                % record Length
                Sdata(ctr).record_length = dStruct.record_length(indx);
                
                %% NAVD88 ADJUSTMENT
                if strcmp(datum,'NAVD88')
                    datum = 'NAVD';
                end
                if strcmp(datum_p,'NAVD88')
                    datum_p = 'NAVD';
                end
                
                %% BUILD URL & DOWNLOAD MEASURED DATA
                [Sdata] = WL_download(ctr,Sdata,datum,station,timezone,units,format,stDates,endDates,gen_url,options,flag1);
                
                %% DOWNLOAD TIDAL PREDICTIONS
                [Sdata] = tidal_predictions_downloader(ctr,Sdata,datum_p,station,timezone,units,format,interval,stDatesp,endDatesp,gen_url,options,dStruct.greatlakes,flag1,dStruct);
                
                %% MAKE SURE TIME VECTORS ARE THE SAME LENGTH
                if dStruct.greatlakes == 0
                    [Sdata] = vector_length_check(ctr,Sdata,flag1,dStruct.greatlakes);
                end
                %% COMPUTE TOTAL RECORD LENGTH (Non NaN Data)
                [Sdata] = record_length_calc(ctr,Sdata,flag1);
                
                %% ADD DateRange
                Sdata(ctr).Beg = datestr(Sdata(ctr).WL.DateTime(1),'yyyy-mm-dd HH:MM');
                Sdata(ctr).End = datestr(Sdata(ctr).WL.DateTime(end),'yyyy-mm-dd HH:MM');
                
                %% INCREMENT COUNTER FOR PRODUCT LOOP
                ctr = ctr + 1;
            end
        end
    end
    
    %% SAVE DATA
    % save('NOAA_Tidal_Gauge_Data.mat','Sdata');
    
    %% END TIMER
    timing2(1).t2 = datetime('now');
    timing2(1).dt = timing2(1).t2-timing2(1).t1;
    timing2(1).runtime = char(timing2(1).t2-timing2(1).t1);
end


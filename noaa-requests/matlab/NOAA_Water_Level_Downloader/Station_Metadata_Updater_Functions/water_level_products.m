function [StationList] = water_level_products(StationList, inv_url,  options, ii)
% Read In Station Inventory Webpage
[html_code, flag] = station_inventory_html_reader(StationList,inv_url,options,ii);
% If Inventory Webpage Exist
if flag ~= 1 % Page Was Found
    %% FIND WATER LEVEL PRODUCTS
    % Find Products of interest (Water Levels)
    products=cellstr(char(extractBetween(string(html_code),'''content'': ''',''', ''group'': ')));% Isolate product name
    % Find Products of interest (water levels: verified 6 minute & hourly wl)
    % The availability of water level predictions was already addressed at 1st
    % stage filtering (see stationlist_product_filter.m)
    % Var List To Extract
    want = {'Verified 6-Minute Water Level','Verified Hourly Height Water Level','Verified Monthly Mean Water Level','Verified High/Low Water Level','Preliminary 6-Minute Water Level'};
    % Compute Logical Matrix (Columns Correspond To Cases In want)
    logical_matrix = cell2mat(cellfun(@(c)strcmp(c,products),want,'UniformOutput',false));
    % Get Indexes of WL Products Of Interest
    [indx,~] = find(logical_matrix==1);
    % Store selected products in data structure
    if sum(indx) > 0
        WL_products = products(indx);
        StationList(ii).WL_products = WL_products;
    else % if measured products are not found station only has predictions and/or monthly WL and/or preliminary data
        StationList(ii).WL_products = {'Not Found'};
    end

    %% FIND WATER LEVEL DATE RANGES
    % Find initial dates index
    st_indx = strfind(html_code,'popstart');
    st_indx = st_indx' + 11;
    % Find end dates index
    end_indx = strfind(html_code,'popend');
    end_indx = end_indx' + 9;
    % Build datestring array
    for jj = 1:length(st_indx)
        st_dates(jj,:) = {html_code(st_indx(jj):st_indx(jj)+22)}; % Inital date string
        end_dates(jj,:) = {html_code(end_indx(jj):end_indx(jj)+22)}; % End date string
    end
    if ~isempty(st_indx)
        % Assign datestring array to corresponding station in data structure
        StationList(ii).startDate = st_dates(indx);
        StationList(ii).endDate = end_dates(indx);
    else
        % If stardate & endate are empty fields station only has predictions
        % Fill empty cell with 'Prediction' for uniformity (also station probably
        % has monthly and/or preliminary water level measurements)
        StationList(ii).startDate = {'Not Found'};
        StationList(ii).endDate = {'Not Found'};
    end

    %% INVENTORY PAGE NOT FOUND
else
    StationList(ii).WL_products = {'Not Found'};
    StationList(ii).startDate = {'Not Found'};
    StationList(ii).endDate = {'Not Found'};
end
end
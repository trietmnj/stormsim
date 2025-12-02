   function [flag2,flag1,indx] = WL_measurements_product_selector_V2(dStruct,prod)
    % Products List
    given = dStruct.WL_products;
    % Cases to Match
    want = {'Verified Monthly Mean Water Level','Verified Hourly Height Water Level','Verified 6-Minute Water Level',...
        'Preliminary 6-Minute Water Level','Verified High/Low Water Level'};
    % Compute Logical Matrix (Columns Correspond To Cases In want)
    logical_matrix = cell2mat(cellfun(@(c)strcmp(c,given),want,'UniformOutput',false));% Compute Logical Matrix (Columns Correspond To Cases In want)
    %
    tgr = strcmp(prod,want);
    if tgr(1)==1
        flag1 = 'm';
        col=1;
    elseif tgr(2)==1
        flag1 = '1';
        col=2;
    elseif tgr(3)==1
        flag1 = '6';
        col=3;
    elseif tgr(4)==1
        flag1 = '6p';
        col=4;
    elseif tgr(5)==1
                flag1 = 'hilo';
        col=5;
    end
    
    % Get Matching Indexes
    [indx] = find(logical_matrix(:,col)==1); % Look for monthly product
    
    if isempty(indx)==1
      flag2 = 1; % flag2=1 product is not present in this station
      % Need to implement a routine that selects the closest available
      % product to what is desired talk to victor & norberto 
    else
        flag2=0;
    end
    end
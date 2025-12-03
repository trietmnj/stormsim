%{
This function computes the record length of downloaded WL data by removing NaN
values from time series and counting the amount of valid timesteps in data.
Record length might differ from product to product.
%}
function [Sdata] = record_length_calc(ii,Sdata,flag1)
 date_vectors = datevec(Sdata(ii).record_length);
    date_vectors(:,2) = date_vectors(:,2)./12;
    date_vectors(:,3) = date_vectors(:,3)./365.25;
    date_vectors(:,4) = date_vectors(:,4)./(24*365.25);
    date_vectors(:,5) = date_vectors(:,5)./(24*60*365.25);
    date_vectors(:,6) = date_vectors(:,6)./(24*3600*365.25);
    dt = sum(date_vectors,'all');
    Sdata(ii).record_length = dt;
%     %% FILTER OUT NANS & COUNT VALID DATA POINTS
%     % Create logical vector of valid data points
%     dummy = isnan(table2array(Sdata(ii).WL(:,2)))==0;
%     % Sum non NaN instances
%     dummy = sum(dummy);
%    
% 
%     
% if strcmp(flag1,'1')==1
%     %% COMPUTE RECORD LENGTH (HOURLY)
%     % Get first timestamp
%     t1 = table2array(Sdata(ii).WL(1,1));
%     % Sum valid data points to initial timestamp
%     t2 = t1 + datenum(0,0,0,dummy,0,0);
%     % Determine the record length
%     dt = between(t1,t2);
%     % Compute Record Length (Norberto's Format)
%     [dt2(:,1),dt2(:,2),dt2(:,3)]=ymd(table2array(Sdata(ii).WL(:,1)));
%     dt=unique(dt,'rows'); Nyrs =size(dt,1)/365.25;
%     % Assing record length to data structure
%     Sdata(ii).record_length = dt2;
% elseif strcmp(flag1,'6')==1
%     %% COMPUTE RECORD LENGTH (6 MIN)
%     % Get first timestamp
%     t1 = table2array(Sdata(ii).WL(1,1));
%     % Sum valid data points to initial timestamp
%     t2 = t1 + datenum(0,0,0,0,dummy*6,0);
%     % Determine the record length
%     dt = between(t1,t2);
%     % Assing record length to data structure
%     Sdata(ii).record_length = dt;
%     
% else
%     %% COMPUTE RECORD LENGTH (MONTHLY)
%     % Get first timestamp
%     t1 = table2array(Sdata(ii).WL(1,1));
%     % Sum valid data points to initial timestamp
%     t2 = t1 + calmonths(dummy);
%     % Determine the record length
%     dt = between(t1,t2);
%     % Assing record length to data structure
%     Sdata(ii).record_length = dt;
%     
% end
end
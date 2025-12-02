function [indx, dEnd, dBeg, invalid_flag] = date_search(dStruct,dBeg,dEnd,indx)
% Flag
invalid_flag = [];
% Get Date Ranges
RangeStart = dStruct.startDate(indx);% Start
RangeEnd = dStruct.endDate(indx);% End
% Cut Date Strings
RangeStart = cellfun(@(x) datenum(x(1:end-4),'yyyy-mm-dd HH:MM:SS'),RangeStart,'UniformOutput',false);
RangeEnd = cellfun(@(x) datenum(x(1:end-4),'yyyy-mm-dd HH:MM:SS'),RangeEnd,'UniformOutput',false);
% Check If Query Dates Are Within Product Date Ranges (A<x<B, where x->query dates)
%     uBound_chk_dummy = cell2mat(cellfun(@(x) cell2mat(RangeStart)<=x & x<=cell2mat(RangeEnd),{dBeg},'UniformOutput',false));
uBound_chk_dummy = cell2mat(cellfun(@(x) x>=cell2mat(RangeStart) & x<cell2mat(RangeEnd),{dBeg},'UniformOutput',false));
lBound_chk_dummy = cell2mat(cellfun(@(x) x>cell2mat(RangeStart) & x<=cell2mat(RangeEnd),{dEnd},'UniformOutput',false));
% Logical Vector (A<x<B, where x->query dates)
dummy_indx = uBound_chk_dummy+lBound_chk_dummy;
if all(dummy_indx==0) % Requested Date Range Is Outside Data Availability
    % % Find Nearest Entry To Requested End Date
    % [~, indx2] = min(abs(cell2mat(RangeEnd)-dEnd));
    % % Overwrite Requested Date Range With Best Option
    % dEnd = RangeEnd{indx2}; % Start
    % dBeg = RangeStart{indx2}; % End
    % % Get Row index
    % indx = indx(indx2);
    invalid_flag = 1;
elseif any(dummy_indx == 2) % Requested Date Range Is Withing Data Prodcuts Availability
    indx = indx(dummy_indx == 2);
elseif any(dummy_indx == 1) % Requested Date Range Needs Adjustment On One Of the Extremes
    % Determine Anchor
    if all(uBound_chk_dummy == 0) % Requested Start Date Is Within Range
        % Find Nearest Entry To Requested End Date
        [~, indx2] = min(abs(cell2mat(RangeStart)-dBeg));
        % Find Corresponding End Date
        dBeg = RangeStart{indx2};
        % Get Row index
        indx = indx(indx2);
    elseif all(lBound_chk_dummy == 0)
        % Find Nearest Entry To Requested End Date
        [~, indx2] = min(abs(cell2mat(RangeEnd)-dEnd));
        % Find Corresponding End Date
        dEnd = RangeEnd{indx2};
        % Get Row index
        indx = indx(indx2);
    end
else
    invalid_flag = 1;
end
end

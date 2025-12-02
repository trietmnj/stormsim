%{
This function selects the appropiate data interval for tidal predictions
download based on preference list.
%}
function [interval,flag] = prediction_interval_selector(dStruct,flag1,flag2)
chk1 = ~iscell(dStruct.datums_predictions);
% If Station does not reside in great lakes
if flag2 == 0 && chk1==1
    % Get available tidal prediction products for station
    dummy = {dStruct.predictions_products.value}';
    % Product preference order
    if strcmp(flag1,'1')==1 || strcmp(flag1,'m')==1
        dummy2 = {'h','30','15','6','1'};
    else
        dummy2 = {'6','1','15','30','h'};
    end
    % Compute logical matrix
    chk2 = cell2mat(cellfun(@(c)strcmp(c,dummy),dummy2,'UniformOutput',false));
    % Transform to logical vector
    chk2 = sum(chk2);
    % Cycle through preference list until one matches
    for jj = 1:length(chk2)
        if chk2(jj)==1
            interval = dummy2{jj};
            flag =0;
            break;
        elseif chk2(jj)==0 && jj==length(chk2)
            % If all othe products do not match, download peaks
            interval = 'hilo';
            flag = ['Station ',dStruct.id, ' is using hilo interval'];
        end
    end
else % Else stattion resides in great lakes
    interval = 'No Tidal Predictions';
    flag ='No Tidal Predictions';
end
end
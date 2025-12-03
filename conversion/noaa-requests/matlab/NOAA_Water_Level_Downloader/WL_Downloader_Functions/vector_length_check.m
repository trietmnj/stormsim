function [Sdata] = vector_length_check(ii,Sdata,flag1,flag2)
    %% MAKE SURE TIME VECTORS ARE THE SAME LENGTH
    % Get date vectors
    tWL = Sdata(ii).WL(:,1);
    tTP = Sdata(ii).TP(:,1);
    try
        if height(tWL)>height(tTP) && flag2==0
            error('CHECK THIS SECTION CAREFULLY. It is unusual to have more measurements than predictions.');
        end
        
        %     % If lengths are not the same fill with NaNs
        %     if strcmp(flag1,'m')==0 && flag2==0
        %         % What dates are missing from measured WL
        %         %         missing  = find(ismember(tTP,tWL)==0);
        %         % Extract missing dates from tidal predictions time vector
        %         DateTime = tTP.DateTime(ismember(tTP,tWL));
        %         % Create NaN Vector
        %         WaterLevel = Sdata(ii).TP(ismember(tTP,tWL),2);
        %         WaterLevel = WaterLevel.("Prediction");
        % %         % Cat NaN's with data table
        % %         gap_mat = table(DateTime,WaterLevel);
        % %         gap_mat = [Sdata(ii).WL;gap_mat];
        % %         % Sort cat table
        % %         [gap_mat] = sortrows(gap_mat,1);
        %         % Assing new table to data structure
        %         Sdata(ii).TP = table(DateTime,WaterLevel);
        %     end
        if height(tWL)~=height(tTP) && strcmp(flag1,'m')==0 && flag2==0
            % What dates are missing from measured WL
            %         missing  = find(ismember(tTP,tWL)==0);
            % Extract missing dates from tidal predictions time vector
            DateTime = tTP.DateTime(ismember(tTP,tWL)==0);
            % Create NaN Vector
            WaterLevel = NaN(size(DateTime));
            % Cat NaN's with data table
            gap_mat = table(DateTime,WaterLevel);
            gap_mat = [Sdata(ii).WL;gap_mat];
            % Sort cat table
            [gap_mat] = sortrows(gap_mat,1);
            % Assing new table to data structure
            Sdata(ii).WL = gap_mat;
        end
    catch
        Sdata(ii).TP = 'No Tidal Predictions';
    end
end
    
    
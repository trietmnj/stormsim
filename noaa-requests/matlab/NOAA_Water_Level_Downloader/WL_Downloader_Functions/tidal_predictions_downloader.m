function [Sdata] = tidal_predictions_downloader(ii,Sdata,datum_p,station,timezone,units,format,interval,stDatesp,endDatesp,gen_url,options,flag2,flag1,dStruct)
%% DOWNLOAD TIDAL PREDICTIONS
% Intialize Variables
datap=[];
% Tidal Predictions
if flag2 == 0 && (~iscell(dStruct.datums_predictions) && ~iscell(Sdata(ii).TP_datum))
    for jj = 1:length(stDatesp)
        for kk =1:length(stDatesp{jj})
            % Tidal Predictions API
            % Default reqeust is for 6 min. For some reason using the
            % default option is quicker
            %             if contains(flag1,'6')==1
            pred_api = ['/api/prod/datagetter?begin_date=',stDatesp{jj}{kk},'&end_date=',endDatesp{jj}{kk},...
                '&station=',station,'&product=predictions&datum=',datum_p,'&time_zone=',timezone,'&units=',units,'&format=',format,''];
            %             else
            %                 pred_api = ['/api/datagetter?product=predictions&application=NOS.COOPS.TAC.WL&begin_date=',stDatesp{jj}{kk},...
            %                     '&end_date=',endDatesp{jj}{kk},'&datum=',datum_p,'&station=',station,'&time_zone=',timezone,'&units=',units,'&interval=',interval,'&format=',format,''];
            %             end
            % Cat URL
            URL = [gen_url pred_api];
            % Initialize Try Counter
            chk = 1;
            % Try Pulling Data
            while chk<=5
                try
                    % Pull Data
                    predtable = webread(URL,options);
                    % Exit While Loop
                    chk = 6;
                catch % If Fail
                    % Sum 1 Try 
                    chk = chk+1;
                    % Make Table NaNs
                    predtable = table(NaN(),NaN(),'VariableNames',{'DateTime','Prediction'});
                    % Wait To Retry Connection
                    pause(5);
                end
            end
            % Cat Data 
            if iscell(predtable.DateTime(1))==0
                % Add Data 
                datap = [datap;predtable(:,1:2)];
                % Print Status 
                ['Station: ',station,' WL Preds: ',num2str(jj),'/',num2str(length(stDatesp)),' Segmentation: ',num2str(kk),'/',num2str(length(stDatesp{jj})),'']
            end
        end
    end
    % If Empty
    if height(predtable)==1
        Sdata(ii).TP = {'Great Lakes Station'};
        
    else
        % Missing do unique
        Sdata(ii).TP = datap;
        % Get Unique Data
        [~,uIndx] = unique(Sdata(ii).TP(:,1),'last');
        % Store Unique Data
        Sdata(ii).TP = Sdata(ii).TP(uIndx,:);
    end
else
    % No Tidal Prediction 
    Sdata(ii).TP = {'Not Found'};
end

% Create a monthly signal from predictions
if flag2 == 0
    try
        % Define Measured and Prediction data vectors
        tWL = Sdata(ii).WL(:,1);
        tTP = Sdata(ii).TP(:,1);
        % Match datetimes in measurements with predictions
        found  = find(ismember(tTP,tWL)==1);
        % Extract matched datetimes form predictions
        DateTime = tTP.DateTime(found);
        % Extract matched WL form predictions
        Prediction = table2array(Sdata(ii).TP(:,2));
        Prediction = Prediction(found);
        % Assign new monthly tidal predictions table
        Sdata(ii).TP = table(DateTime,Prediction);
    catch
        % Assign new monthly tidal predictions table
        Sdata(ii).TP = {'Not Found'};
    end    
end
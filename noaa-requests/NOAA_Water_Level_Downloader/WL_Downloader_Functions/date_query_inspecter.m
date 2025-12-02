function [uBound_chk,lBound_chk] = date_query_inspecter(uBound_chk,lBound_chk,dBeg,dEnd,RangeStart,RangeEnd)
if uBound_chk==1 && lBound_chk==1 % Query Dates Are Within Range
    % Evrything is FIne
else
    % Case 1: Check If Query Date Start Is Before or After RangeStart
    uBound_chk = cell2mat(cellfun(@(x) x<cell2mat(RangeEnd),{dBeg},'UniformOutput',false));
   % Check if End Range Coincides With Start Query Date
   
   [y,m,d,~,~,~] =  datevec(dBeg);
   [y2,m2,d2,~,~,~] = datevec(RangeEnd{:});
   chk = sum([y-y2,m-m2,d-d2])==0;
   if uBound_chk==0 || chk% Query Date Is Older Than Range End
       % Discard This Station
       uBound_chk = 0;
       lBound_chk = 0;
   else % Query Date Is Younger Than Range End
       % Make Sure Query Start Date Does Not Need Adjustment
       uBound_chk = cell2mat(cellfun(@(x) x<cell2mat(RangeStart),{dBeg},'UniformOutput',false));
       if uBound_chk == 1 % Make Adjustment
           dBeg = cell2mat(RangeStart);
       else % Everything is Fine
           uBound_chk = 1;
       end
       % Case 2: Check If Query Date End Is Before or After RangeStart
       lBound_chk = cell2mat(cellfun(@(x) x>cell2mat(RangeStart),{dEnd},'UniformOutput',false));
       if lBound_chk == 0
           lBound_chk = 0;
       else
           % Case 2: Check If Query Date End Is Before or After RangeEnd
           lBound_chk = cell2mat(cellfun(@(x) x<=cell2mat(RangeEnd),{dEnd},'UniformOutput',false));
           if lBound_chk == 0 % Make ADjustment
               dEnd = cell2mat(RangeEnd);lBound_chk =1;
           else % Everything Is Fine
               lBound_chk = 1;
           end
       end
   end
end
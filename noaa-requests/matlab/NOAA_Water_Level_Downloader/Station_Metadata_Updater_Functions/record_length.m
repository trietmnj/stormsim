function [StationList] = record_length(StationList,ii)
    %{
    Record Length Computation:
        tf - ti
    %}
for jj = 1:length(StationList(ii).startDate)
    if  strcmp('Not Found',StationList(ii).startDate)~=1 % if measured WL exist 
        t1 = datetime(StationList(ii).startDate{jj,1}(1:19),'format','yyyy-MM-dd HH:mm:ss');
        t2 = datetime(StationList(ii).endDate{jj,1}(1:19),'format','yyyy-MM-dd HH:mm:ss');
        dt = between(t1,t2);
        [y,m,d,t] = split(dt,{'years','months','days','time'});
        StationList(ii).record_length(jj,1) = dt;
        StationList(ii).record_length_vector(jj).years = y;
        StationList(ii).record_length_vector(jj).months = m;
        StationList(ii).record_length_vector(jj).days = d;
        StationList(ii).record_length_vector(jj).time = t;

    else % if measured WL products do not exist (predictions only)
        StationList(ii).record_length = {'Not Found'};
        StationList(ii).record_length_vector = {'Not Found'};
    end
end
end
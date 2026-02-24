%% Monotonic_adjustment.m
%{
By: E. Ramos-Santiago
Description: Script to adjust the trend of hazard curves with jumps. The
  StormSim-SST tool can produce non-monotonic curves when the GPD threshold
  parameter returned by the MRL selection method is too low. This causes
  incomplete random samples and the potential to have jumps in the mean
  curve and CLs.
History of revisions:
20210310-ERS: created function to patch the SST tool.
%}
function [y_in] = Monotonic_adjustment(x_in,y_in)

% Change inputs to column vector
y_in=y_in(:);x_in=log(x_in(:));

% Take numbers
idx3=~isnan(y_in);y=y_in(idx3);x=x_in(idx3);

% Compute slope
dx=diff(x);dy=diff(y);s=dy./dx;

% Identify positive slopes
id_pos=find(s>0);

% Adjust y values with positive slopes
if ~isempty(id_pos)
    for i=1:length(id_pos)
        y(id_pos(i)+1)=mean(s(id_pos(i)-2:id_pos(i)-1))*dx(id_pos(i))+y(id_pos(i));
    end
    
    % Return values to original position
    y_in(idx3)=y;
end
y_in=y_in';
end
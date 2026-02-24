function StormSim_JPM_plot(JPM_output, jpm_options, plot_options)
%
% Colors for percentiles plots
cs={'r-.','b--','b--','r-.'};
prc=round(jpm_options.prc);

% Initialize Figures
fig=figure('Color',[1 1 1],'visible','off');
% Intialize Axes
ax = axes('xscale','log','XGrid','on','XMinorTick','on',...
    'YGrid','on','YMinorTick','on',...
    'XDir', 'reverse', 'FontSize', 12);
% Hold Properties
hold(ax, 'on');
% Title
title({'StormSim-JPM '; ['Station: ',JPM_output.staID]}, 'FontSize',12);
% Format X Axis
if jpm_options.use_AEP == 1
    xlim(ax, [1e-4 1]);
    XTick=[1e-4 1e-3 1e-2 1e-1 1];
    xlabel('Annual Exceedance Probability','FontSize',12);
else
    xlim(ax, [1e-4 10]);
    XTick=[1e-4 1e-3 1e-2 1e-1 1 10];
    xlabel('Annual Exceedance Frequency (yr^{-1})','FontSize',12);
end
set(ax, 'XTick', XTick);
% Format Y Axis
if ~isempty(plot_options.yaxis_Limits)
    ylim(plot_options.yaxis_Limits);
end
ylabel(plot_options.yaxis_Label, 'FontSize', 12);
% Process the percentiles
pObj=struct('o',[],'n',[],'L','');
for i=2:length(prc)+1 % First Row Is Mean
    pObj(i-1).o = plot(ax, JPM_output.HC_plt_x, JPM_output.HC_plt(:, i), cs{i-1}, 'LineWidth', 2);
    pObj(i-1).n = prc(i-1);
    pObj(i-1).L = {['CL',int2str(prc(i-1)),'%']};
end
pObj_t = struct2table(pObj);
pObj_t = sortrows(pObj_t,'n','descend'); % sort the table by 'n'

% Take percentiles
t1 = pObj_t(pObj_t.n>50,:); t1 = table2struct(t1); %above the mean
t2 = pObj_t(pObj_t.n<50,:); t2 = table2struct(t2); %below the mean

% Mean and Empirical
h1 = plot(ax, JPM_output.HC_plt_x, JPM_output.HC_plt(:, 1), 'k-', 'LineWidth', 2); % Mean
% Legend
legend([[t1.o],h1,[t2.o]],{t1.L,'Mean',t2.L},...
    'Location','southoutside','Orientation','horizontal','NumColumns',5,'FontSize',10);
%
switch jpm_options.integration_method
    case 1
        int_str = 'PCHA_ATCS';
    case 2
        int_str = 'PCHA_ITCS';
end
% Filename
fname = fullfile(plot_options.path_out,...
    ['JPM_','HC_',JPM_output.staID,'_' int_str '.png']);
% Save figure
saveas(fig,fname);
close(fig);
end
function StormSim_PST_plot(SST_output, pst_options, plot_options)
% Colors for percentiles plots
cs={'r-.','b--','b--','r-.'};
prc=round(pst_options.prc);

%% PLOT MEAN RESIDUAL LIFE RESULTS
% plot these only when the GPD fit occurred
if ~strcmp(SST_output.MRL_output.Selection.Criterion{:},'None')
    % Define Inputs
    MRL_output = SST_output.MRL_output; % Grab MRL Data Structure
    mrl = MRL_output.Summary; % MRL Results Summary
    TH = MRL_output.Selection.Threshold; % Threshold Selected
    crit = MRL_output.Selection.Criterion; % Specified Criterion
    % Define Subplot Properties
    line_colors = {'-g','-m','-k','-b','-r'}; % Line Colors
    field_to_plot = {'Rate', 'WMSE', 'MeanExcess', 'GPD_Shape', 'GPD_Scale'}; % MRL Fields
    y_labels = [{'Events';'per year'}, {'Weighted';'MSE'}, {'Mean';'Excess'}, ...
        {'Shape';'Parameter'}, {'Scale';'Parameter'}]; % Subplot Y Labels
    % Plot MRL Parameters If Available
    if strcmp(MRL_output.Status,'')
        % Intialize Figure
        fig=figure('units','inches','Position',[1 1 6 6],'Color',[1 1 1],'visible','off');
        % Title
        title({'StormSim-SST - Mean Residual Life';['Station: ',SST_output.staID]},'FontSize',12);
        % Set Base Axes Properties
        axes('XGrid','on','XMinorTick','on','YGrid','on','YMinorTick','on','FontSize',12);
        % Plot Each Axis
        for ii = 1:5
            % Define Subplot Axis (Threshold)
            ax1 = subplot(5,1,ii);
            % Hold Properties
            hold(ax1, 'on');
            % Format Y Axis
            ylim(ax1, [round(min(mrl.(field_to_plot{ii}))-0.01,2) round(max(mrl.(field_to_plot{ii}))+0.01,2)]);
            ylabel(ax1, y_labels(ii), 'FontSize', 12);
            % Plot MRL Rate Curve
            plot(mrl.Threshold, mrl.(field_to_plot{ii}), line_colors{ii}, 'LineWidth', 2);
            % Plot Resulting Threshold
            if ~isempty(TH)
                h = xline(ax1, TH, 'k:', 'LineWidth', 2);
                if ii == 1
                    legend(h, crit, 'Location', 'NorthEast');
                end
            end
            % Turn Off Hold On Properties
            hold(ax1, "off");
        end
        % Save Out Figure
        fname = fullfile(plot_options.path_out, ['SST_','MRL_',SST_output.staID,'.png']);
        saveas(gcf, fname);
        close(fig);
    end

    %% PLOT GPD PARAMETERS FOR BOOTSTRAPING
    % Get Mean GPD Parameters
    mn_k = mean(MRL_output.pd_k_wOut,1,'omitnan');
    mn_k2 = mean(MRL_output.pd_k_mod,1,'omitnan');
    % Define Threshold Criterion String
    switch SST_output.MRL_output.Selection.Criterion{:}
        case 'CritWMSE'
            str = 'WMSE Criterion';
        case 'CritSI'
            str = 'Sample Intensity Criterion';
        case 'Default'
            str = 'Default';
        otherwise
            str = 'None';
    end
    % Intialize Figure
    fig=figure('Color','w','visible','off');
    % Initialize & Format Axes
    ax = gca;
    xlabel(ax, ['GPD Shape Parameter - MRL Threshold - ' str], 'FontSize', 12);
    ylabel(ax, 'Count', 'FontSize', 12);
    % Hold Properties
    hold(ax, "on");
    % Plot Distirbution
    h1 = histogram(ax, MRL_output.pd_k_wOut,'BinWidth',.05,'FaceColor','b'); %original
    h2 = histogram(ax, MRL_output.pd_k_mod,'BinWidth',.05,'FaceColor','r'); %w/outliers filled
    % Plot Mean
    m1 = xline(ax, mn_k, 'b-', 'LineWidth', 2);
    m2 = xline(ax, mn_k2, 'r-', 'LineWidth', 2);
    % Add Legend
    legend([h1, h2, m1, m2],{'hist w/outliers','hist w/o outliers','mean w/outliers',...
        'mean w/o outliers'}, 'Location', 'northwest', 'FontSize', 8);
    % Save Out Figure
    fname = fullfile(plot_options.path_out, ['SST_CompareGPDShape_',SST_output.staID,'.png']);
    saveas(gcf, fname)
    close(fig);
end

%% PLOT HAZARD CURVES
% Initialize Figures
fig=figure('Color',[1 1 1],'visible','off');
% Intialize Axes
ax = axes('xscale','log','XGrid','on','XMinorTick','on',...
    'YGrid','on','YMinorTick','on',...
    'XDir', 'reverse', 'FontSize', 12);
% Hold Properties
hold(ax, 'on');
% Title
title({'StormSim-SST '; ['Station: ',SST_output.staID]}, 'FontSize',12);
% Format X Axis
if pst_options.use_AEP == 1
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
    pObj(i-1).o = plot(ax, SST_output.HC_plt_x, SST_output.HC_plt(i, :), cs{i-1}, 'LineWidth', 2);
    pObj(i-1).n = prc(i-1);
    pObj(i-1).L = {['CL',int2str(prc(i-1)),'%']};
end
pObj_t = struct2table(pObj);
pObj_t = sortrows(pObj_t,'n','descend'); % sort the table by 'n'

% Take percentiles
t1 = pObj_t(pObj_t.n>50,:); t1 = table2struct(t1); %above the mean
t2 = pObj_t(pObj_t.n<50,:); t2 = table2struct(t2); %below the mean

% Mean and Empirical
h1 = plot(ax, SST_output.HC_plt_x, SST_output.HC_plt(1, :), 'k-', 'LineWidth', 2); % Mean
h2 = scatter(ax, SST_output.HC_emp.Hazard, SST_output.HC_emp.Response, 10, 'g','filled','MarkerEdgeColor','k'); % Historical
% Legend
legend([[t1.o],h1,[t2.o],h2],{t1.L,'Mean',t2.L,'Empirical'},...
    'Location','southoutside','Orientation','horizontal','NumColumns',5,'FontSize',10);
% Filename
fname = fullfile(plot_options.path_out,...
    ['SST_','HC_',SST_output.staID,'_TH_' SST_output.MRL_output.Selection.Criterion{:} '.png']);
% Save figure
saveas(fig,fname)
close(fig);
end
# Import Packages
from src import noaa_py
from src import sea_level_rise as slr
import pandas as pd

# --------------- Define Inputs
# Define NOAA Station And Date Range To Pull Monthly Mean Measurements For
station_id = 8570283
wl_stdate = "20000101"
wl_endate = "20260101"
wl_datum = 'MSL' # MUST BE MSL , NOAA ONLY PROVIDES LINEAR TREND (ALPHA) AT MSL [mm/yr]
# Define SLR Curve Start/End Year
start_year = 2000
end_year = 2150
# Define SLR Projections To Use
projections = 'usace_2019' # noaa_2012 or carswg_2016
# Define figure output path (None == Make Figure Visible)
out_path = r'data\outputs\slr_demo'

# ----------- Main
def main():
    # Define NOAA Data Request Dcitionary
    nooa_request = {
            "station": f"{station_id}",
            "start_date": wl_stdate,
            "end_date": wl_endate,
            "datum": wl_datum,
        }

    # Pull NOAA Monthly Water Level
    wl_ds = pd.DataFrame(noaa_py.tides.get_monthly_mean(nooa_request)) #noaa_py returns dictionary
    # Keep Datum Of Interest
    wl_ds = wl_ds[['year', wl_datum]]

    # Get Beta Values For Requested Projection
    beta_table = slr.beta_scenarios.print_beta_table(projections)
    # Get Beta Value Col
    beta = beta_table.iloc[:, 1].to_numpy()

    # Returns Station ID Entry On Linear Trend Entry For Station
    # alpha value is on mm/yr
    _, alpha = slr.linear_trend_api.get_noaa_linear_trend(int(nooa_request["station"]))

    # Generate the DataFrame with all porjection curves
    slr_scenarios_df = slr.sea_level_rise.generate_slr_curves(alpha, beta, start_year, end_year)

    # Plot Curves
    slr.plot_slr.plot_slr_curves(slr_scenarios_df, beta, wl_ds,
                                title=f"Sea Level Rise {projections.upper()} Projections ({start_year}-{end_year}) ({wl_datum})",
                                line_names=beta_table.iloc[:, 2].to_list(),
                                output_folder=out_path)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

import requests
import numpy as np
import pandas as pd
import io


def get_noaa_linear_trend(station_id):

    # URL of the data file
    url = "https://tidesandcurrents.noaa.gov/sltrends/data/USStationsLinearSeaLevelTrends.txt"
    try:
        # Fetch the data from the URL
        response = requests.get(url)
        # Raise an exception for bad status codes (like 404 or 500)
        response.raise_for_status()

        # The first 5 rows are metadata, so we skip them.
        # The data is whitespace-delimited.
        data = pd.read_csv(io.StringIO(response.text), sep=r'\s+', skiprows=1,header=None)

        data.columns = ['Station ID','Station Name','First Year','Last Year','Year Range',
                        '% Complete','MSL Trends (mm/yr)','+/- 95% CI (mm/yr)',
                        'MSL Trend (ft/century)','+/- 95% CI (ft/century)','Latitude','Longitude']
        
        # The value -9999.000 is used for missing data. Let's replace it with NaN.
        data.replace(-9999.000, np.nan, inplace=True)

        data_out = data[data['Station ID'] == station_id]
        alpha = data_out['MSL Trends (mm/yr)'].to_numpy()
        # Display the first few rows of the parsed data
        print("Fetching NOAA linear trends from national table.")

        return data_out, alpha

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to fetch the data: {e}")

        return np.nan, np.nan
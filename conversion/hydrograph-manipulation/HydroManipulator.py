import pandas as pd
import requests
from io import StringIO

class HydroManipulator:
    def __init__(self):
        self.data = None

    def get_tidal_prediction(self, staID, startDate, endDate, datum):
        api_url = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=' \
            + startDate + '&end_date=' + endDate + '&station=' + staID + '&product=predictions&datum=' \
                                + datum + '&time_zone=gmt&interval=h&units=metric&format=csv'
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.text  # or response.text for raw output
            df = pd.read_csv(StringIO(data), sep=",", skipinitialspace=True)
            return(df)
        else:
            print(f"Error: {response.status_code}")

    def add_tides(self, data_in, adjustment):
        """
        Apply tidal adjustment to input data.
        """
        return data_in + adjustment

    def add_slr(self, data_in, adjustment):
        """
        Apply sea level rise adjustment to input data.
        """
        return data_in + adjustment
    
    def get_slr_curve(self):
        """
        Define method to create SLR curve
        """

    def add_depth_limitation(self, data_in, adjustment):
        """
        Apply depth limitation by subtracting adjustment from input data.
        """
        return [max(0, value - adjustment) for value in data_in]

    def parse_lc(self, filepath, table_headers):
        """
        Parse a NxM text file into a pandas DataFrame using provided headers.
        """
        try:
            self.data = pd.read_csv(
                filepath,
                sep=',',
                header=None,
                skip_blank_lines=True
             )
            self.data.columns = table_headers
            return self.data
        except Exception as e:
            print(f"Error parsing file: {e}")
            return None
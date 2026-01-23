import requests
import time
import json
from datetime import datetime
import csv
import io

class noaa_api:
    def __init__(self, config_path=None):
        # Headers to mimic a browser (prevents some server-side blocks)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.config = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path):
        """
        Load configuration from JSON file.
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)[0]  # assuming single dict in list

    def _fetch_url(self, url, is_json=False, retries=8, pause_time=5):
        """
        Replaces the repetitive try/catch/pause logic in your MATLAB scripts.
        """
        attempt = 0
        while attempt < retries:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                if is_json:
                    return response.json()
                return response.text
            except requests.RequestException as e:
                attempt += 1
                time.sleep(pause_time)
                if attempt == retries:
                    print(f"Failed to fetch {url}: {e}")
                    return None
        return None

    def get_all_prediction_stations(self):
            """
            Fetches prediction stations directly from the NOAA MDAPI JSON endpoint.
            URL: https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=tidepredictions

            Returns a dictionary keyed by Station ID containing:
            state, name, station_id, lat, lon, prediction_type, AND data_intervals
            """
            url = "https://tidesandcurrents.noaa.gov/mdapi/latest/webapi/stations.json?type=tidepredictions"

            print(f"Fetching prediction stations from API: {url}")
            data = self._fetch_url(url, is_json=True)

            all_stations = {}

            if not data or 'stations' not in data:
                print("Error: No station data found in API response.")
                return all_stations

            print(f"Found {len(data['stations'])} stations. Processing...")

            for item in data['stations']:
                # The JSON structure typically looks like:
                # {"id": "8720030", "name": "Fernandina Beach", "state": "FL", "lat": 30.6717, "lng": -81.4656, "type": "R", ...}

                st_id = item.get('id')

                if st_id:
                    # Map 'R'/'S' to full names if you prefer, or keep as codes.
                    # R = Reference (Harmonic), S = Subordinate
                    p_type = item.get('type')

                    if p_type == 'R':
                        p_type_desc = 'Harmonic'
                    elif p_type == 'S':
                        p_type_desc = 'Subordinate'
                    else:
                        p_type_desc = p_type

                    # --- NEW: Populate data_intervals using the helper method ---
                    intervals = self.get_station_intervals(p_type)
                    all_stations[st_id] = {
                        "state": item.get('state', 'Unknown'),
                        "name": item.get('name', 'Unknown'),
                        "station_id": st_id,
                        "lat": item.get('lat'),
                        "lon": item.get('lng'),
                        "prediction_type": p_type_desc,
                        "type_code": p_type,
                        "data_intervals": intervals
                    }

            return all_stations

    def get_station_intervals(self, station_type):
        """
        Determines available prediction intervals based on Station Type.
        Reflects logic from original 'tidal_predictions_products_and_datums.m'

        Args:
            station_type (str): The type code ('R', 'S', etc.) or description.

        Returns:
            dict: containing 'values' (codes) and 'descriptions' (readable names).
        """
        # Default (No predictions)
        result = {
            "values": [],
            "descriptions": []
        }

        # Normalize input (handle cases where we might pass "Harmonic" or "R")
        st_type = str(station_type).upper().strip()

        # LOGIC 1: Subordinate Stations ('S')
        # These only support High/Low predictions
        if st_type == 'S' or st_type == 'SUBORDINATE':
            result['values'] = ['hilo', 'hi', 'lo']
            result['descriptions'] = ['High/Low', 'High Only', 'Low Only']

        # LOGIC 2: Reference/Harmonic Stations ('R')
        # These support time series (1min - hourly) AND High/Low
        elif st_type == 'R' or st_type == 'HARMONIC':
            result['values'] = ['1', '6', '15', '30', 'h', 'hilo', 'hi', 'lo']
            result['descriptions'] = [
                '1 Minute', '6 Minute', '15 Minute', '30 Minute',
                'Hourly', 'High/Low', 'High Only', 'Low Only'
            ]

        return result

    def get_station_datums(self, station_id):
        """
        Fetches vertical datum information for a specific station.
        """
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}/datums.json?units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status() # Check for HTTP errors
            data = response.json()
            return data.get('datums', []) # Safe access, returns empty list if missing
        except requests.RequestException as e:
            print(f"Error fetching datums for {station_id}: {e}")
            return None

    def get_tidal_prediction(self, station=None, start_date=None, end_date=None, interval='h', datum='MSL'):
        """
        Fetches tidal prediction data.

        Accepts inputs in two ways:
        1. Explicit Arguments: get_tidal_prediction("8557380", "20260118", ...)
        2. JSON/Dictionary:    get_tidal_prediction({"station": "8557380", "start_date": "20260118", ...})
        """

        # --- INPUT HANDLING LOGIC ---
        # If the first argument is a dictionary, we treat it as the 'json' input
        if isinstance(station, dict):
            config = station
            # extract values from the dict, falling back to the defaults defined in signature if missing
            station = config.get('station')
            start_date = config.get('start_date')
            end_date = config.get('end_date')
            interval = config.get('interval', interval)
            datum = config.get('datum', datum)

        # Basic Validation to ensure we have the minimums
        if not station or not start_date or not end_date:
            print("Error: Missing required parameters (station, start_date, end_date).")
            return None

        # --- API LOGIC (Same as before) ---
        base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

        params = {
            "product": "predictions",
            "application": "NOS.COOPS.TAC.WL",
            "begin_date": start_date,
            "end_date": end_date,
            "station": station,
            "datum": datum,
            "interval": interval,
            "time_zone": "gmt",
            "units": "metric",
            "format": "json"
        }

        # Build URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{base_url}?{query_string}"

        print(f"Fetching predictions for {station}...")

        data = self._fetch_url(full_url, is_json=True)

        if data and 'predictions' in data:
            formatted_data = {
                # Convert string "2034-09-19 00:00" -> datetime object
                "time": [datetime.strptime(item['t'], "%Y-%m-%d %H:%M") for item in data['predictions']],

                # Convert string "-0.331" -> float
                "value": [float(item['v']) for item in data['predictions']]
            }
            return formatted_data
        elif data and 'error' in data:
            print(f"API Error: {data['error'].get('message')}")
            return None
        else:
            print(f"Error: No prediction data found for {station}")
            return None

    def get_seasonal_trend(self, station_id):
        """
        Fetches the Average Seasonal Cycle data for a specific station.
        URL: https://tidesandcurrents.noaa.gov/sltrends/data/{station_id}_seasonal.csv

        The file contains 12 rows (one for each month) with columns:
        Month, Water Level, Upper95%, Lower95%

        Returns:
            dict: Dictionary with lists for 'month', 'level', 'upper_ci', 'lower_ci'
        """
        # Construct the URL
        url = f"https://tidesandcurrents.noaa.gov/sltrends/data/{station_id}_seasonal.csv"
        print(f"Fetching seasonal cycle for {station_id}...")

        # --- FETCHING ---
        # Using requests directly to ensure we get text, as this is a CSV file
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                return None
            csv_text = response.text
        except Exception as e:
            print(f"Fetch Error: {e}")
            return None

        # --- PARSING ---
        # Initialize output dictionary
        result = {
            "month": [],
            "level": [],     # The average water level
            "upper_ci": [],  # Upper 95% Confidence Interval
            "lower_ci": []   # Lower 95% Confidence Interval
        }

        # Use StringIO to treat the string like a file
        f = io.StringIO(csv_text)
        reader = csv.reader(f)

        # LOGIC: Skip metadata lines until we find the header "Month"
        header_found = False

        for row in reader:
            # 1. Search for the Header Line
            if not header_found:
                # Check if the first column is "Month" (handling potential BOM or whitespace)
                if row and "Month" in row[0]:
                    header_found = True
                continue # Skip this loop iteration (we don't process the header itself)

            # 2. Process Data Lines (after header is found)
            if row and len(row) >= 4:
                try:
                    # Column 0: Month (1-12)
                    result['month'].append(int(row[0]))

                    # Column 1: Water Level (Float)
                    result['level'].append(float(row[1]))

                    # Column 2: Upper 95% (Float)
                    result['upper_ci'].append(float(row[2]))

                    # Column 3: Lower 95% (Float)
                    result['lower_ci'].append(float(row[3]))

                except ValueError:
                    continue # Skip empty lines or bad data

        print(f"Parsed {len(result['month'])} seasonal data points.")
        return result

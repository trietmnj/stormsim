# Import Packages
import requests
from datetime import datetime, timedelta
import time
from collections import defaultdict
import pandas as pd

# NOAA serves predictions in bounded windows. For sub-hourly intervals it
# accepts far more than this (180 days observed for interval='1'), but past its
# real ceiling it answers HTTP 200 with an EMPTY prediction list rather than an
# error -- so an over-long window disables tides silently instead of failing.
# 30 days stays well inside the documented limit; the win comes from asking for
# fewer windows, not bigger ones. See TidalPredictionCache.
PREDICTION_CHUNK_DAYS = 30

# Define Methods
def _fetch_url(url, is_json=False, retries=8, pause_time=5):
    """
    Replaces the repetitive try/catch/pause logic in your MATLAB scripts.
    """
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers, timeout=10)
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


def _prediction_params(station, start_date, end_date, interval, datum):
    return {
        "product": "predictions",
        "application": "NOS.COOPS.TAC.WL",
        "begin_date": start_date,
        "end_date": end_date,
        "station": station,
        "datum": datum,
        "interval": interval,
        "time_zone": "gmt",
        "units": "metric",
        "format": "json",
    }


def _fetch_prediction_chunk(station, st_date, ed_date, interval, datum):
    """
    Fetch one prediction window and return its raw prediction records.

    Raises rather than returning empty. NOAA answers an over-long window with
    HTTP 200 and no predictions, and _fetch_url returns None once its retries
    are exhausted; both used to surface as a TypeError deep in the caller or,
    worse, as tides quietly missing from the run.
    """
    params = _prediction_params(station, st_date, ed_date, interval, datum)
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?{query_string}"

    data = _fetch_url(full_url, is_json=True)
    if data is None:
        raise RuntimeError(
            f"NOAA predictions request failed for station {station} "
            f"({st_date}-{ed_date}) after retries"
        )
    if "error" in data:
        raise RuntimeError(
            f"NOAA predictions error for station {station} "
            f"({st_date}-{ed_date}): {data['error'].get('message')}"
        )
    predictions = data.get("predictions") or []
    if not predictions:
        raise RuntimeError(
            f"NOAA returned no predictions for station {station} "
            f"({st_date}-{ed_date}, interval={interval}). A window longer than "
            f"the product limit returns empty rather than erroring."
        )
    return predictions


def _format_predictions(predictions):
    return {
        "time": [datetime.strptime(item["t"], "%Y-%m-%d %H:%M") for item in predictions],
        "value": [float(item["v"]) for item in predictions],
    }


class TidalPredictionCache:
    """
    Fetches NOAA tidal predictions on demand, one bounded chunk at a time, and
    keeps each chunk for reuse.

    The hydrograph manipulator only ever reads tides inside a storm's own date
    window, but used to pre-fetch every day between the first and last year of
    the lifecycle. Storms are sparse, so nearly all of that was downloaded and
    discarded -- a 10 year lifecycle at 1-minute resolution is ~122 sequential
    requests, which is what pushes a single reach past the Lambda timeout.

    Chunks are aligned to a fixed grid anchored at the configured start date, so
    storms that fall in the same window share one request instead of issuing
    overlapping ones.
    """

    def __init__(self, config, chunk_days=PREDICTION_CHUNK_DAYS):
        self.station = config.get("station")
        self.interval = config.get("interval", "h")
        self.datum = config.get("datum", "MSL")
        self.chunk_days = chunk_days
        self.anchor = datetime.strptime(config["start_date"], "%Y%m%d")
        self._chunks = {}
        self.request_count = 0

    def _chunk_index(self, moment):
        return (moment - self.anchor).days // self.chunk_days

    def _chunk_bounds(self, index):
        start = self.anchor + timedelta(days=index * self.chunk_days)
        # Inclusive end: NOAA treats end_date as the last day in the window.
        return start, start + timedelta(days=self.chunk_days - 1)

    def _load_chunk(self, index):
        if index not in self._chunks:
            start, end = self._chunk_bounds(index)
            predictions = _fetch_prediction_chunk(
                self.station,
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                self.interval,
                self.datum,
            )
            self.request_count += 1
            self._chunks[index] = _format_predictions(predictions)
        return self._chunks[index]

    def get_window(self, start_date, end_date):
        """
        Return predictions covering the calendar days spanning start..end.

        Widened to whole days because filter_tide_data compares against
        midnight and 23:59:59 of the requested bounds.
        """
        first = self._chunk_index(start_date.replace(hour=0, minute=0, second=0, microsecond=0))
        last = self._chunk_index(end_date.replace(hour=0, minute=0, second=0, microsecond=0))

        merged = {"time": [], "value": []}
        for index in range(first, last + 1):
            chunk = self._load_chunk(index)
            merged["time"].extend(chunk["time"])
            merged["value"].extend(chunk["value"])
        return merged


def get_tidal_prediction(station=None, start_date=None, end_date=None, interval='h', datum='MSL'):
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

    # Create Date Segments (Predictions -> 30 days Limit)
    s_list, e_list = generate_date_chunks(PREDICTION_CHUNK_DAYS, start_date, end_date, date_fmt="%Y%m%d")

    # Fetches the whole span up front. Prefer TidalPredictionCache when only
    # scattered windows are actually read -- see its docstring.
    predictions = []
    for ii, (st_date, ed_date) in enumerate(zip(s_list, e_list)):
        print(f"Fetching predictions for {station} ({ii+1}/{len(s_list)}): {st_date} - {ed_date}...")
        try:
            predictions.extend(
                _fetch_prediction_chunk(station, st_date, ed_date, interval, datum)
            )
        except RuntimeError as e:
            print(f"Error: {e}")
            return None

    if not predictions:
        print(f"Error: No prediction data found for {station}")
        return None

    return _format_predictions(predictions)

def get_monthly_mean(station=None, start_date=None, end_date=None, datum='MSL'):
    """
    Fetches tidal prediction data.

    Accepts inputs in two ways:
    1. Explicit Arguments: get_monthly_mean("8557380", "20260118", ...)
    2. JSON/Dictionary:    get_monthly_mean({"station": "8557380", "start_date": "20260118", ...})
    """

    # --- INPUT HANDLING LOGIC ---
    # If the first argument is a dictionary, we treat it as the 'json' input
    if isinstance(station, dict):
        config = station
        # extract values from the dict, falling back to the defaults defined in signature if missing
        station = config.get('station')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        datum = config.get('datum', datum)

    # Basic Validation to ensure we have the minimums
    if not station or not start_date or not end_date:
        print("Error: Missing required parameters (station, start_date, end_date).")
        return None

    # Create Date Segments (Monthly Product -> 200 years limit)
    s_list, e_list = generate_date_chunks(199*365, start_date, end_date, date_fmt="%Y%m%d")
    
    # --- API LOGIC (Same as before) ---
    base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    params = {
        "product": "monthly_mean",
        "application": "NOS.COOPS.TAC.WL",
        "begin_date": start_date,
        "end_date": end_date,
        "station": station,
        "datum": datum,
        "time_zone": "gmt",
        "units": "metric",
        "format": "json"
    }

    for ii, (st_date, ed_date) in enumerate(zip(s_list, e_list)):  
        # Grab Date Range
        params["begin_date"] = st_date
        params["end_date"] = ed_date
        # Build URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{base_url}?{query_string}"

        print(f"Fetching monthly mean water level for {station} ({ii+1}/{len(s_list)}): {st_date} - {ed_date}...")
        if ii == 0:
            data = _fetch_url(full_url, is_json=True)
        else:
            # Fetch Data
            dummy = _fetch_url(full_url, is_json=True)
            # Append To Existing List
            data['data'].extend(dummy['data'])
            
    if data and 'data' in data:         
        # Create a dictionary where every default value is an empty list
        formatted_data = defaultdict(list)

        # Populate the dictionary
        for row in data['data']:
            for key, value in row.items():
                formatted_data[key].append(pd.to_numeric(value))

        # Convert back to a standard dictionary (optional, but cleaner)
        formatted_data = dict(formatted_data)

        return formatted_data
    elif data and 'error' in data:
        print(f"API Error: {data['error'].get('message')}")
        return None
    else:
        print(f"Error: No prediction data found for {station}")
        return None

def generate_date_chunks(dt: int, start_input: str | datetime, end_input: str | datetime, date_fmt=None):
    """
    Generates start/end date pairs in 30-day chunks (or less).
    
    Args:
        start_input (str or datetime): The starting date.
        end_input (str or datetime): The ending date.
        date_fmt (str): Required if inputs are strings (e.g., "%Y-%m-%d").
                        Used to parse the input strings.
    """

    # --- BLOCK 1: Input Standardization ---
    # Handle Start Date
    if isinstance(start_input, str):
        if date_fmt is None:
            raise ValueError("date_fmt must be provided when input dates are strings.")
        current_date = datetime.strptime(start_input, date_fmt)
    else:
        current_date = start_input

    # Handle End Date
    if isinstance(end_input, str):
        if date_fmt is None:
            raise ValueError("date_fmt must be provided when input dates are strings.")
        final_date = datetime.strptime(end_input, date_fmt)
    else:
        final_date = end_input

    # --- BLOCK 2: Chunk Generation ---
    out_start = []
    out_end = []

    # Loop until the current pointer passes the final date
    while current_date <= final_date:
        
        # Calculate the tentative end of the window (30 days)
        # We subtract 1 second or adjust logic if you need exact 30-day spans, 
        # but here we follow your logic: Start + 30 days.
        window_end = current_date + timedelta(days=dt)
        
        # Clip the window if it exceeds the user's requested end date
        if window_end > final_date:
            window_end = final_date
            
        # Format for API/Output (Keeping original %Y%m%d format)
        out_start.append(current_date.strftime('%Y%m%d'))
        out_end.append(window_end.strftime('%Y%m%d'))
        
        # Move start pointer to the NEXT day to ensure continuity
        current_date = window_end + timedelta(days=1)
        
    return out_start, out_end
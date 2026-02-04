# Import Packages 
import requests
from datetime import datetime, timedelta
import time

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

    # Create Date Segments
    s_list, e_list = generate_date_chunks(start_date, end_date, date_fmt="%Y%m%d")
    
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

    for ii, (st_date, ed_date) in enumerate(zip(s_list, e_list)):  
        # Grab Date Range
        params["begin_date"] = st_date
        params["end_date"] = ed_date
        # Build URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{base_url}?{query_string}"

        print(f"Fetching predictions for {station} ({ii+1}/{len(s_list)}): {st_date} - {ed_date}...")
        if ii == 0:
            data = _fetch_url(full_url, is_json=True)
        else:
            # Fetch Data
            dummy = _fetch_url(full_url, is_json=True)
            # Append To Existing List
            data['predictions'].extend(dummy['predictions'])
            
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

def generate_date_chunks(start_input: str | datetime, end_input: str | datetime, date_fmt=None):
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
        window_end = current_date + timedelta(days=30)
        
        # Clip the window if it exceeds the user's requested end date
        if window_end > final_date:
            window_end = final_date
            
        # Format for API/Output (Keeping original %Y%m%d format)
        out_start.append(current_date.strftime('%Y%m%d'))
        out_end.append(window_end.strftime('%Y%m%d'))
        
        # Move start pointer to the NEXT day to ensure continuity
        current_date = window_end + timedelta(days=1)
        
    return out_start, out_end
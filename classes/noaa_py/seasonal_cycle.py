# Import Packages 
import requests
import io
import csv

def get_station_seasonal_trend(station_id: str):
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

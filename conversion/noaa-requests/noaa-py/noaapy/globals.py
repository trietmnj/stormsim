# noaa-requests/noaa-py/noaapy/globals.py
BASE_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod"  # NOAA CO-OPS URL
DEFAULT_DATUM = "MSL"  # Preferred Datum for Data Download
DEFAULT_TIMEZONE = "GMT"  # Preferred Time Zone for Data Download
DEFAULT_UNITS = "metric"  # Preferred Units for Data Download
DEFAULT_DATA_FORMAT = "csv"  # Download Data Format
DEFAULT_TIMEOUT = 800

PRODUCT_FLAGS = {
    "Verified Monthly Mean Water Level": "m",
    "Verified Hourly Height Water Level": "1",
    "Verified 6-Minute Water Level": "6",
    "Preliminary 6-Minute Water Level": "6p",
    "Verified High/Low Water Level": "hilo",
}

PRODUCT_LABELS = {
    "6": "6 minutes",
    "1": "hourly",
    "6p": "6 minutes preliminary",
    "hilo": "High/Low",
    "m": "monthly",
}

PRODUCT_PARAM = {
    "6": "water_level",
    "6p": "water_level",
    "1": "hourly_height",
    "hilo": "high_low",
}

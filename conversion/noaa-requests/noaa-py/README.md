# noaa-py

NOAA data download converted to python

## Usage

The intended workflow is 3 fold:

1. Download the seasonal annual cycle data for steric adjustments

```bash
uv run noaa-requests/noaa-py/seasonal_cycle.py
```

2. Identify the relevant stations

```bash
uv run noaa-requests/noaa-py/station.py
```

3. Download the tidal timeseries data

```bash
uv run noaa-requests/noaa-py/timeseries.py
```

**Notes: Everything should be run from the base dir `conversion/` with `pyproject.toml` **

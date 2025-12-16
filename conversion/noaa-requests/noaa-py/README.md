# noaa-py

NOAA data download converted to python

## Usage

The intended workflow is split into 2 steps:

1. Download the seasonal annual cycle data for steric adjustments

```bash
uv run noaa-requests/noaa-py/seasonal_cycle.py
```

2. Download the tidal prediction timeseries data

```bash
uv run noaa-requests/noaa-py/tides.py
```

**Notes: Everything should be run from the base dir `conversion/` with `pyproject.toml` **

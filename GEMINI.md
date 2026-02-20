# StormSim Project Context

## Project Overview
StormSim is a coastal storm simulation workflow designed to model storm events and their impacts on coastal structures. The system follows a modular architecture consisting of three primary stages:

1.  **Lifecycle Generation (`lcgen`):** Simulates synthetic timelines of storm events based on historical data and statistical models (Poisson recurrence).
2.  **Hydrograph Manipulation (`HydroManipulator`):** Constructs detailed time-series hydrographs (surge, water elevation, wave characteristics) for each simulated storm event.
3.  **Structure Response (`eurotop`):** Calculates wave runup and overtopping rates for coastal structures using Eurotop 2018 empirical formulas.

## Architecture & Data Flow
The workflow follows a linear pipeline:
`Lifecycle Generator` -> `Hydrograph Manipulator` -> `Eurotop`

### Key Components
- **`classes/`**: Core logic and package implementation.
    - `lcgen/`: Lifecycle generation logic (sampling, loading, validation).
    - `hydrograph_manipulator/`: Hydrograph processing logic.
    - `eurotop/`: Eurotop 2018 response models.
    - `noaa_py/`: Utilities for NOAA data queries and tidal analysis.
    - `utilities/`: General-purpose utilities (CSV, time, CHS).
- **`implementation-scripts/`**: Entry points for running different stages of the workflow.
- **`config-files/`**: JSON configuration files for parameterizing simulations.
- **`data/`**: Input data (CHS master tracks, probability bins) and output directories.

## Development Status
- Currently refactoring `lcgen` to support:
    - S3/MinIO storage for inputs and outputs.
    - DuckDB for abstracted data ingestion.
    - JSON-based configuration management.

## Building and Running
The project uses a standard Python environment.

### Installation
```bash
uv sync
```

### Dependencies
- `numpy`, `pandas`, `h5py`, `scipy`, `tqdm` (Core Simulation)
- `duckdb` (Data Ingestion & Abstraction)
- `boto3`, `s3fs` (S3/MinIO Storage)
- `python-dotenv` (Environment Management)

### Running Lifecycle Generation
The lifecycle generator now supports JSON-based configuration and can target either local storage or an S3/MinIO bucket.

**Local Execution (Default):**
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_local.json
```

**S3/MinIO Execution:**
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_s3.json
```

### Configuration Options (`data/lcgen/*.json`)
- `inputs`:
    - `use_duckdb`: (bool) Enable DuckDB for fast CSV ingestion.
    - `use_s3`: (bool) If true, DuckDB will read input files from S3 using `s3_config`.
- `outputs`:
    - `storage_type`: `"local"` or `"s3"`.
    - `s3_bucket`: Destination bucket name.
    - `s3_prefix`: Directory prefix within the bucket.
- `s3_config`: Credentials and endpoint for MinIO/S3.

## Development Conventions
- **Configuration**: Store stage-specific configs in their respective data directories (e.g., `data/lcgen/config_*.json`).
- **Data Abstraction**: Use DuckDB for reading tabular data to allow seamless switching between local files and S3.
- **Environment**: Use `uv` for environment management and `uv run` for execution.

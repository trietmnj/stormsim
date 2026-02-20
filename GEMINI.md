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
pip install -r requirements.txt
```

### Running Lifecycle Generation
```bash
python implementation-scripts/lc_generator_main.py
```

### Dependencies
- `numpy`, `pandas`, `h5py`, `scipy`, `tqdm` (Core)
- Planned: `duckdb`, `boto3`, `s3fs` (Storage & Data Abstraction)

## Development Conventions
- **Configuration**: Prefer JSON configuration files in `config-files/`.
- **Data Paths**: Use the `@data/lcgen/**` structure for lifecycle-related data to separate data from code.
- **Modularity**: Logic should reside in `classes/`, with `implementation-scripts/` acting as thin drivers.

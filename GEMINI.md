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
- **`lambda/lcgen/`**: AWS Lambda deployment package for `lcgen`.
- **`config-files/`**: JSON configuration files for parameterizing simulations.
- **`data/`**: Input data (CHS master tracks, probability bins) and output directories.

## Development Status
- **Lifecycle Generation (`lcgen`)**:
    - Refactored to support S3/MinIO storage for inputs and outputs.
    - Integrated DuckDB for abstracted, high-performance data ingestion.
    - Implemented AWS Lambda support using a containerized environment.
- **Hazard Curves**:
    - Porting MATLAB JPM/PST logic to Python (see `hazard-curves/` directory).

## AWS Lambda Deployment (`lcgen`)
The Lifecycle Generator can be deployed as a containerized AWS Lambda function.
- **Base Image**: `public.ecr.aws/lambda/python:3.12` (Amazon Linux 2023).
- **Toolchain**: Uses AL2023 to provide GCC 11.3, which is required for building modern scientific Python packages (e.g., NumPy, h5py).
- **Dependency Management**: Uses a dedicated `lambda/lcgen/requirements.txt` with pinned versions (`numpy < 2.0.0`) to ensure stability in the Lambda environment.

## Building and Running
The project uses a standard Python environment managed by `uv`.

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
The lifecycle generator supports JSON-based configuration and can target either local storage or an S3/MinIO bucket.

**Local Execution:**
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_local.json
```

**S3/MinIO Execution:**
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_s3.json
```

### Docker Build (Lambda)
```bash
docker build -t stormsim-lcg-lambda -f lambda/lcgen/Dockerfile .
```

## Development Conventions
- **Configuration**: Store stage-specific configs in their respective data directories (e.g., `data/lcgen/config_*.json`).
- **Data Abstraction**: Use DuckDB for reading tabular data to allow seamless switching between local files and S3.
- **Environment**: Use `uv` for environment management and `uv run` for execution.
- **Dependency Pinning**: Maintain Lambda-specific requirements in `lambda/lcgen/requirements.txt` to account for specific architectural or toolchain constraints (e.g., AL2 vs AL2023).

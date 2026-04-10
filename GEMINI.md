# StormSim Project Context

## Project Overview
StormSim is a coastal storm simulation workflow designed to model storm events and their impacts on coastal structures. The system follows a modular architecture consisting of three primary stages:

1.  **Lifecycle Generation (`lcgen`):** Simulates synthetic timelines of storm events based on historical data and statistical models (Poisson recurrence).
2.  **Hydrograph Manipulation (`HydroManipulator`):** Constructs detailed time-series hydrographs (surge, water elevation, wave characteristics) for each simulated storm event.
3.  **Structure Response (`eurotop`):** Calculates wave runup and overtopping rates for coastal structures using Eurotop 2018 empirical formulas.
4.  **Hazard Curves (`hazard_curves`):** Calculates extreme value statistics and hazard curves using Joint Probability Method (JPM) and Peaks-over-Threshold (PST/POT) analysis.

## Architecture & Data Flow
The workflow follows a linear pipeline:
`Lifecycle Generator` -> `Hydrograph Manipulator` -> `Eurotop`

Hazard curve analysis can be performed as a standalone component or used to provide probability-based inputs to the main pipeline.

### Key Components
- **`src/stormsim/`**: Core logic and package implementation.
    - `lcgen/`: Lifecycle generation logic (sampling, loading, validation).
    - `hydrograph_manipulator/`: Hydrograph processing logic.
    - `eurotop/`: Eurotop 2018 response models.
    - `hazard_curves/`: JPM and PST/POT analysis logic.
    - `sea_level_rise/`: Sea level rise scenario generation and trend analysis.
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
    - Porting MATLAB JPM/PST logic to Python (see `src/stormsim/hazard_curves/` directory).
    - Includes unit tests with MATLAB-derived validation datasets.

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

## Automated Releases
This project is configured to automatically build and release to GitHub when a version tag is pushed.
- **Workflow**: `.github/workflows/publish.yml`
- **Trigger**: Push a tag starting with `v` (e.g., `v0.1.0`).

## Development Conventions
- **Configuration**: Store stage-specific configs in their respective data directories (e.g., `data/lcgen/config_*.json`).
- **Data Abstraction**: Use DuckDB for reading tabular data to allow seamless switching between local files and S3.
- **Environment**: Use `uv` for environment management and `uv run` for execution.
- **Package Imports**: Always use absolute imports from the `stormsim` namespace (e.g., `from stormsim.lcgen import sampling`).

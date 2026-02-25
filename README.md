# StormSim: Coastal Storm Simulation Workflow

StormSim is a modular coastal storm simulation system designed to model synthetic storm lifecycles and their physical impacts on coastal structures.

## Workflow Overview

The system operates as a linear pipeline:
**Lifecycle Generator** $\rightarrow$ **Hydrograph Manipulator** $\rightarrow$ **Eurotop Structure Response**

### 1. Lifecycle Generation (`lcgen`)
- **Purpose**: Simulates synthetic timelines of storm events based on historical recurrence rates ($\lambda$) and seasonal probability distributions.
- **Key Logic**: Uses Poisson sampling and rejection sampling to ensure realistic storm arrival patterns and minimum temporal separation.
- **Data Abstraction**: Utilizes DuckDB to support seamless data ingestion from both local CSV files and S3/MinIO buckets.

### 2. Hydrograph Manipulation
- **Purpose**: Constructs detailed time-series forcing (surge and wave characteristics) for each simulated storm.
- **Process**: Matches simulated events to ADCIRC/Wave model HDF5 data, performing temporal alignment and interpolation.
- **Steric Adjustment**: Applies seasonal trends and upper confidence intervals to water elevations.

### 3. Eurotop (Structure Response)
- **Purpose**: Calculates wave runup, overtopping rates, and flood volumes for specific coastal geometries.
- **Logic**: Implements Eurotop 2018 empirical formulas to derive physical responses (R2%, q, Q) and resulting flood stages.

---

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Recommended for environment and dependency management)

### Installation
```bash
uv sync
```

### Running the Simulation
The entry points are located in `implementation-scripts/`.

**Example: Running Lifecycle Generation**
```bash
# Run with local configuration
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_local.json

# Run with S3/MinIO configuration
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_s3.json
```

## AWS Lambda Deployment

The Lifecycle Generator (`lcgen`) can be deployed as a containerized AWS Lambda function using the provided Docker configuration. This environment uses **Python 3.12 (Amazon Linux 2023)** to provide a modern toolchain for scientific dependencies.

For detailed instructions, see: [lambda/lcgen/README.md](./lambda/lcgen/README.md)

---

## Project Structure

- `classes/`: Core logic and package implementation.
    - `lcgen/`: Lifecycle generation models.
    - `hydrograph_manipulator/`: Surge/Wave alignment and processing.
    - `eurotop/`: Structure response models.
- `lambda/`: AWS Lambda deployment packages.
    - `lcgen/`: LCG Lambda function, Dockerfile, and specific `requirements.txt`.
- `implementation-scripts/`: Command-line drivers for each stage.
- `data/`: Input datasets (CHS tracks, probability bins) and simulation outputs.
- `config-files/`: Shared configuration files (JSON).

## Configuration

Configuration is managed via JSON files. For the Lifecycle Generator, specific configurations are located in `data/lcgen/`.

- **S3 Support**: Configure `s3_config` in your JSON file to target MinIO or AWS S3.
- **DuckDB**: Enabled via `inputs.use_duckdb` for high-performance data loading.

# StormSim: Coastal Storm Simulation Workflow

StormSim is a modular coastal storm simulation system designed to model synthetic storm lifecycles and their physical impacts on coastal structures.

## Workflow Overview

The system operates as a linear pipeline:
**Lifecycle Generator** $\rightarrow$ **Hydrograph Manipulator** $\rightarrow$ **Eurotop Structure Response**

### 1. Lifecycle Generation (`lcgen`)
- **Purpose**: Simulates synthetic timelines of storm events based on historical recurrence rates ($\lambda$) and seasonal probability distributions.
- **Key Logic**: Uses Poisson sampling and rejection sampling to ensure realistic storm arrival patterns and minimum temporal separation.

### 2. Hydrograph Manipulation
- **Purpose**: Constructs detailed time-series forcing (surge and wave characteristics) for each simulated storm.

### 3. Eurotop (Structure Response)
- **Purpose**: Calculates wave runup, overtopping rates, and flood volumes for specific coastal geometries.

### 4. Hazard Curves (JPM & PST)
- **Purpose**: Calculates extreme value statistics and hazard curves using Joint Probability Method (JPM) and Peaks-over-Threshold (PST/POT) analysis.

---

## Getting Started

### Installation

**As a developer (editable):**
```bash
git clone https://github.com/trietmnj/stormsim.git
cd stormsim
uv sync
```

**As a library:**
```bash
pip install git+https://github.com/trietmnj/stormsim.git
```

### Library Usage

#### High-Level Orchestration
The simplest way to run a simulation is via the centralized `run_lc_generator` entry point. This handles data loading, simulation, and output saving.

```python
from stormsim.lcgen import run_lc_generator

config = {
    "simulation_params": { ... },
    "inputs": { ... },
    "outputs": { ... }
}

# Run simulation (local or cloud)
result = run_lc_generator(config)
```

#### Smart Storage Handling
The library includes a `StorageContext` utility that automatically resolves local vs. S3 paths and handles AWS credentials.

```python
from stormsim.utilities.storage import StorageContext

ctx = StorageContext(config, is_lambda=True)
input_path = ctx.get_input_path("rel_prob_file")
output_path = ctx.get_output_path()
```

### Running Scripts
Standalone entry points are located in `implementation-scripts/`.
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_local.json
```

---

## Releasing New Versions

This project uses GitHub Actions to automate releases. To create a new release:

1. Update the `version` in `pyproject.toml`.
2. Commit and push your changes.
3. Create and push a version tag:
   ```bash
   git tag v0.1.x
   git push origin v0.1.x
   ```
4. The **Release** workflow will automatically build the package and create a GitHub Release with the artifacts.

---

## Project Structure

- `src/stormsim/`: Core package namespace.
    - `lcgen/`: Lifecycle generation models and orchestration.
    - `hydrograph_manipulator/`: Surge/Wave alignment and processing.
    - `eurotop/`: Structure response models.
    - `utilities/`: General-purpose utilities, including `storage.py` for I/O.
- `implementation-scripts/`: Command-line drivers for each stage.
- `lambda/`: AWS Lambda deployment packages.
- `data/`: Input datasets and simulation outputs.
- `config-files/`: Shared configuration files (JSON).
- `tests/`: Unit and integration tests.

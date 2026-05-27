# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**StormSim** is a modular Python library for coastal storm lifecycle simulation,
used as the upstream hazard source for the CHART Screening Tool. It models
synthetic storm timelines and their physical impacts on coastal structures.

## Commands

```bash
# Install dependencies
uv sync

# Run lifecycle generation locally
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_local.json

# Run hydrograph manipulation
uv run implementation-scripts/hydro_manipulator_main.py --config config-files/hydroManipulator_config.json

# Run EurOtop structure response
uv run implementation-scripts/eurotop_main.py --config config-files/eurotop_run_config.json

# Aggregate overtopping rates across transects
uv run implementation-scripts/q_aggregation_main.py <transect_sim_path>

# Run all tests
uv run pytest tests/

# Run a single test file
uv run pytest tests/hazard_curves/test_jpm.py -v

# Install as a dependency in another project
uv add "stormsim @ git+https://github.com/trietmnj/stormsim.git"
```

## Pipeline Architecture

The simulation runs as a linear pipeline:

```
lcgen (lifecycle generation)
  → hydrograph_manipulator (surge/wave time-series)
    → eurotop (wave runup / overtopping volumes)
          ↓
  eurotop.aggregate_q (aggregate overtopping across transects)
```

A parallel module handles extreme-value statistics from simulation outputs:

```
hazard_curves (JPM / PST-POT analysis)
```

## Package Structure

Source lives in `src/stormsim/`:

```
src/stormsim/
├── lcgen/                  # Lifecycle generation (Poisson storm arrivals)
│   ├── simulation.py       # run_lc_generator — top-level orchestrator
│   ├── sampling.py         # simulate_lifecycle + rejection sampling
│   ├── load.py             # Load CHS/parquet inputs via DuckDB
│   └── validation.py       # Config + output validation
├── hydrograph_manipulator/ # Surge/wave time-series construction
│   └── HydroManipulator.py # Class with SLR + bias correction methods
├── eurotop/                # Wave runup and overtopping (EurOtop 2018)
│   ├── simulation.py       # run_eurotop — top-level orchestrator
│   ├── processing.py       # Per-file processing loop
│   ├── responses.py        # Structure response calculations
│   ├── runup_and_ot_eurotop_2018.py
│   └── aggregation.py      # aggregate_q — sum overtopping across transects
├── hazard_curves/
│   ├── common.py           # Shared utilities, grid values, parquet I/O
│   ├── jpm/                # Joint Probability Method
│   │   ├── core.py         # Options dataclass (pydantic), enums
│   │   └── jpm.py          # compute() — preprocessing, integration, interpolation
│   └── pst/                # Peaks-over-Threshold (PST/POT)
│       ├── core.py         # PSTOptions / ResponseData dataclasses
│       ├── fit.py          # StormSim_PST_Fit — main PST fitting logic
│       ├── mrl.py          # StormSim_MRL — mean residual life threshold selection
│       └── pst.py          # StormSim_PST — top-level PST entry point
├── sea_level_rise/         # SLR scenario generation and trend analysis
├── noaa_py/                # NOAA tidal gauge data access
└── utilities/
    ├── storage.py          # StorageContext — local/S3 I/O abstraction
    └── chs_utils.py        # CHS HDF5 file utilities
```

Implementation entry points are in `implementation-scripts/`. Config templates
are in `config-files/` and `data/lcgen/`.

## Key Patterns

### StorageContext

`StorageContext` (`utilities/storage.py`) transparently resolves local vs. S3
paths for all three pipeline stages. In Lambda, IAM role credentials are used
automatically — never pass `access_key`/`secret_key` explicitly:

```python
from stormsim.utilities.storage import StorageContext

ctx = StorageContext(config, is_lambda=True)
input_path  = ctx.get_input_path("rel_prob_file")  # resolves to s3:// or local
output_path = ctx.get_output_path()
opts        = ctx.get_pandas_storage_options()     # None for local
```

For SAM local testing with local files, set `LCGEN_USE_LOCAL_INPUTS=true`.

### High-Level Entry Points

Each stage exposes a single callable exported from its `__init__.py`:

```python
from stormsim.lcgen import run_lc_generator
from stormsim.eurotop import run_eurotop, aggregate_q
from stormsim.hazard_curves import jpm, StormSim_PST

result = run_lc_generator(config)
result = run_eurotop(config)
aggregate_q("data/outputs/eurotop")          # writes to .../aggregate_responses/
jpm.compute(fpath, key, opts)
StormSim_PST(response_dict, options_dict)
```

### DuckDB for Data Loading

`lcgen/load.py` uses DuckDB to read tabular inputs, enabling seamless switching
between local CSV/parquet files and S3 objects. Enable via
`config["inputs"]["use_duckdb"] = True`.

### Hazard Curves (JPM / PST)

Both modules use pydantic dataclasses for options validation. `IntegrationEnum`,
`UncertaintyEnum`, and `TideEnum` accept integer, case-insensitive string, or
enum values. `StormSim_PST` takes two positional dicts (`response_data`,
`pst_options`) — the old `plot_options` third argument has been removed.

## Tests

Tests live in `tests/hazard_curves/`. They are script-style (no `def test_*`
functions) — pytest runs the module-level code during collection.

**Before running `test_jpm.py` for the first time**, generate the parquet
input files from the MATLAB source data:

```bash
cd tests/hazard_curves && uv run --project ../.. python matlab2parquet.py
```

`test_pst.py` requires `tables` (PyTables/HDF5), which is a dev-only dependency:

```bash
uv add --dev tables
```

## Configuration Schema

```json
{
  "simulation_params": {
    "initialize_year": 2000,
    "lifecycle_duration": 100,
    "num_lcs": 50,
    "lam_target": 3.5,
    "min_arrival_trop_days": 2
  },
  "inputs": {
    "use_s3": false,
    "use_duckdb": false,
    "rel_prob_file": "data/lcgen/Relative_probability_bins_Atlantic 4.csv",
    "storm_id_prob_file": "..."
  },
  "outputs": {
    "storage_type": "local",
    "local_directory": "data/outputs/lcgen",
    "filename": "lifecycle_output.csv"
  }
}
```

Local config template: `data/lcgen/config_local.json`
S3 config template: `data/lcgen/config_s3.json`

## Lambda Deployment

`lambda/lcgen/` wraps `run_lc_generator` in a Docker-based AWS Lambda.

- Base image: `public.ecr.aws/lambda/python:3.12` (AL2023, GCC 11.3)
- Lambda `requirements.txt` pins `numpy < 2.0.0` for stability
- Use `docker-compose.yml` in `lambda/` for local Lambda testing

## Releasing New Versions

1. Bump `version` in `pyproject.toml`
2. Commit and push
3. `git tag v0.1.x && git push origin v0.1.x`
4. GitHub Actions (`.github/workflows/publish.yml`) builds and creates a
   GitHub Release automatically on any `v*` tag push

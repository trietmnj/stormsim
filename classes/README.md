# Coastal Storm Simulation Workflow

This project implements a workflow for simulating coastal storm events and their impact on structures. The workflow consists of three main stages: Lifecycle Generation, Hydrograph Manipulation, and Eurotop Response Calculation.

## Workflow Overview

The general data flow is as follows:
`Lifecycle Generator` -> `Hydrograph Manipulator` -> `Eurotop`

### 1. Lifecycle Generation

*   **Directory**: `lifecycle-generation/`
*   **Main Script**: `main.py`
*   **Purpose**: Simulates a synthetic timeline of storm events based on historical probabilities.
*   **Inputs**:
    *   Configuration variables (years, duration, lambda) in `main.py`.
    *   Probability bins (e.g., `Relative_probability_bins_Atlantic 4.csv`).
    *   Storm ID cumulative distribution functions (CDFs) (e.g., `stormprob.csv`).
*   **Outputs**:
    *   A CSV file (default: `EventDate_LC.csv`) containing a schedule of storm events.
    *   **Key Columns**: `lifecycle`, `year`, `month`, `day`, `hour`, `storm_id`.
*   **Relation to Next Step**: This output CSV serves as the primary input schedule for the Hydrograph Manipulator, defining *which* storms happen and *when*.

### 2. Hydrograph Manipulation

*   **Directory**: `HydroManipulator_example_Fabian/` (or similar implementation folders)
*   **Main Script**: `Hydromanipulator_example_implementation_MODIFIED.py` (recommended for Eurotop compatibility)
*   **Purpose**: Constructs detailed time-series hydrographs for each storm event identified in the lifecycle generation step.
*   **Inputs**:
    *   `EventDate_LC.csv` (Output from Lifecycle Generation).
    *   **ADCIRC HDF5 Files**: Contain surge/water elevation data.
    *   **Wave HDF5 Files**: Contain wave characteristics (height, period, direction).
*   **Process**:
    *   Matches `storm_id` from the lifecycle list to data in the HDF5 files.
    *   Aligns and interpolates the ADCIRC and Wave model data to a common time base.
    *   Extracts relevant variables: Water Elevation, Wave Height (Hm0), Peak Period (Tp).
*   **Outputs**:
    *   Individual CSV files for each storm event (e.g., `LC_0_stormID_175_TC_...UTC.csv`) or a consolidated CSV.
    *   **Key Columns**: `water_elevation`, `wave_height`, `wave_peak_period`, `wave_direction`, `date`.
*   **Relation to Next Step**: These hydrograph files provide the physical forcing timeseries required by the Eurotop module to calculate structure response.

### 3. Eurotop (Structure Response)

*   **Directory**: `eurotop/`
*   **Main Script**: `eurotop_implementation.py`
*   **Purpose**: Calculates wave runup, overtopping rates, and resulting water stages for coastal structures.
*   **Inputs**:
    *   Hydrograph CSV files (Output from Hydrograph Manipulator).
    *   `eurotop_run_config.json`: Configuration for file paths.
    *   `pse_geometry` (JSON): Geometric parameters of the coastal structure (slope, berms, walls).
    *   `stage_vol_file` (CSV): Stage-volume relationship for the protected area.
*   **Process**:
    *   Reads the forcing variables (`water_elevation`, `wave_height`, `wave_peak_period`) from the hydrographs.
    *   Applies Eurotop 2018 empirical formulas (`runup_and_ot_eurotop_2018_mod.py`).
    *   Integrates overtopping rates to find total volumes and corresponding flood stages.
*   **Outputs**:
    *   `*_responses.csv` files corresponding to input hydrographs.
    *   **Key Columns**: `overtopping_rate` (q), `runup` (R2p), `overtopping_volume` (Q), `stage`.

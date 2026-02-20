# Lifecycle Generation Module (`lcgen`)

This module generates a synthetic schedule of coastal storm events based on historical storm recurrence rates (Poisson distribution) and daily/seasonal probability distributions.

## Components

### `load.py`
Provides functions for loading:
- **Relative Probabilities**: Daily/monthly probabilities of storm events (e.g., from `Relative_probability_bins_Atlantic 4.csv`).
- **Storm ID CDF**: A lookup table for storm IDs and their relative weights (e.g., from `CHS-NA_Master_Track_Table.csv`).
- **Data Abstraction**: Supports both standard Pandas and DuckDB ingestion for local or S3-based data.

### `sampling.py`
Core simulation logic:
- `simulate_lifecycle`: The main entry point for a single lifecycle simulation.
- `_sample_with_minimal_arrival`: Ensures a minimum time separation (e.g., 7 days) between events using rejection sampling.

### `validation.py`
Utility to verify that the generated storm counts match the target recurrence rate ($\lambda$) after simulation.

## Usage

### Local Configuration (`config_local.json`)
Set `outputs.storage_type` to `"local"`. All input/output paths should be relative to the project root.

### S3/MinIO Configuration (`config_s3.json`)
To write to a MinIO instance:
1. Set `outputs.storage_type` to `"s3"`.
2. Configure `s3_config` with your `endpoint`, `access_key`, and `secret_key`.
3. Set `outputs.s3_bucket` and `outputs.s3_prefix`.

### Running the Generator
```bash
uv run implementation-scripts/lc_generator_main.py --config data/lcgen/config_s3.json
```

## Input Data Management
If you wish to move your input data to S3:
1. Upload your CSV files to your bucket.
2. Update the `rel_prob_file` and `storm_id_prob_file` paths to use the `s3://` URI format.
3. Set `inputs.use_s3: true` in your configuration.

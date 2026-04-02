import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import os
import sys
from typing import Dict

# Import StormSim Packages
from src import lcgen

# -----------------------------
# CONFIG LOADING
# -----------------------------
DEFAULT_CONFIG = Path("data/lcgen/config_local.json")

def load_config(path: Path) -> Dict:
    if not path.exists():
        print(f"Error: Config file {path} not found.")
        sys.exit(1)
    with open(path, "r") as f:
        return json.load(f)

# -----------------------------
# CORE LOGIC
# -----------------------------
def run_lc_generator(config: Dict):
    print(f"Running LC Generator...")

    # Simulation Params
    sim_params = config["simulation_params"]
    init_year = sim_params["initialize_year"]
    duration = sim_params["lifecycle_duration"]
    num_lcs = sim_params["num_lcs"]
    lam_target = sim_params["lam_target"]
    min_sep = sim_params["min_arrival_trop_days"]

    # Input paths/settings
    inputs = config["inputs"]
    use_duckdb = inputs.get("use_duckdb", False)
    rel_prob_file = inputs["rel_prob_file"]
    storm_id_file = inputs["storm_id_prob_file"]

    # Storage and S3 settings
    s3_config_raw = config.get("s3_config", {})
    s3_config = {
        "use_s3": inputs.get("use_s3", False),
        "s3_endpoint": s3_config_raw.get("endpoint"),
        "s3_access_key": s3_config_raw.get("access_key"),
        "s3_secret_key": s3_config_raw.get("secret_key")
    }

    # Load Data
    prob_schedule: pd.DataFrame = lcgen.load.load_relative_probabilities(
        rel_prob_file, use_duckdb=use_duckdb, s3_config=s3_config
    )
    storm_set: pd.DataFrame = lcgen.load.load_storm_id_cdf(
        storm_id_file, use_duckdb=use_duckdb, s3_config=s3_config
    )

    # Columns for split outputs
    cols = [
        "location_id",
        "lifecycle",
        "year_offset",
        "year",
        "month",
        "day",
        "hour",
        "timestamp",
        "storm_id",
    ]

    all_dfs: list[pd.DataFrame] = []

    # Full simulation
    for lc in range(num_lcs):
        df = lcgen.sampling.simulate_lifecycle(
            lifecycle_index=lc,
            init_year=init_year,
            duration_years=duration,
            lam=lam_target,
            min_sep_days=min_sep,
            prob_schedule=prob_schedule,
            storm_set=storm_set,
            show_progress=False,
        )

        # Assign location_id and keep only the ID / timing columns for outputs
        df["location_id"] = config.get("location_id", "unknown_location")
        df_ids = df[cols].copy()
        all_dfs.append(df_ids)

    data = pd.concat(all_dfs, ignore_index=True)

    # Handle Output
    outputs = config["outputs"]
    output_filename = outputs["filename"]
    storage_type = outputs.get("storage_type", "local")

    if storage_type == "s3":
        s3_path = f"s3://{outputs['s3_bucket']}/{outputs['s3_prefix']}/{output_filename}"

        storage_options = {}
        if s3_config_raw.get("access_key"):
            storage_options["key"] = s3_config_raw["access_key"]
        if s3_config_raw.get("secret_key"):
            storage_options["secret"] = s3_config_raw["secret_key"]
        if s3_config_raw.get("endpoint"):
            storage_options["client_kwargs"] = {"endpoint_url": s3_config_raw["endpoint"]}

        print(f"Writing output to {s3_path}...")
        data.to_csv(s3_path, index=False, storage_options=storage_options if storage_options else None)
        output_result = s3_path
    else:
        out_dir = Path(outputs["local_directory"])
        out_dir.mkdir(parents=True, exist_ok=True)
        local_path = out_dir / output_filename
        print(f"Writing output to {local_path}...")
        data.to_csv(local_path, index=False)
        output_result = str(local_path)

    # Validation
    if config.get("runtime", {}).get("validate_lambda", False):
        if all_dfs:
            df_all = pd.concat(all_dfs, ignore_index=True)
            counts = lcgen.validation.compute_storm_counts(df_all)
            lcgen.validation.verify_lambda(counts, lam_target)
        else:
            print("[warn] No lifecycle data generated; skipping lambda validation.")

    return {"status": "success", "output": output_result}

# -----------------------------
# MAIN DRIVER
# -----------------------------
def main(config_path: Path):
    config = load_config(config_path)
    print(f"Using config: {config_path}")

    if config["runtime"].get("profile", False):
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

        result = run_lc_generator(config)
        print(result)

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
        ps.print_stats(40)
        print(s.getvalue())
    else:
        result = run_lc_generator(config)
        print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lifecycle Generator Main Script")
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help=f"Path to the JSON config file (default: {DEFAULT_CONFIG})"
    )
    args = parser.parse_args()
    config_path = Path(args.config)

    main(config_path)

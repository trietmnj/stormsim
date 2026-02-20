import json
from pathlib import Path
import pandas as pd
from typing import Dict

# Import StormSim Packages
from classes import lcgen

# -----------------------------
# CONFIG LOADING
# -----------------------------
CONFIG_PATH = Path("data/lcgen/config.json")


def load_config(path: Path) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


# -----------------------------
# MAIN DRIVER
# -----------------------------
def main():
    config = load_config(CONFIG_PATH)

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
        "s3_secret_key": s3_config_raw.get("secret_key"),
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
        "lifecycle",
        "year_offset",
        "year",
        "month",
        "day",
        "hour",
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

        # Keep only the ID / timing columns for outputs
        df_ids = df[cols].copy()
        all_dfs.append(df_ids)

    data = pd.concat(all_dfs, ignore_index=True)

    # Handle Output
    outputs = config["outputs"]
    output_filename = outputs["filename"]
    storage_type = outputs.get("storage_type", "local")

    if storage_type == "s3":
        s3_path = (
            f"s3://{outputs['s3_bucket']}/{outputs['s3_prefix']}/{output_filename}"
        )
        storage_options = {
            "key": s3_config_raw.get("access_key"),
            "secret": s3_config_raw.get("secret_key"),
            "client_kwargs": {"endpoint_url": s3_config_raw.get("endpoint")},
        }
        print(f"Writing output to {s3_path}")
        data.to_csv(s3_path, index=False, storage_options=storage_options)
    else:
        out_dir = Path(outputs["local_directory"])
        out_dir.mkdir(parents=True, exist_ok=True)
        local_path = out_dir / output_filename
        print(f"Writing output to {local_path}...")
        data.to_csv(local_path, index=False)

    # Validation
    if config["runtime"].get("validate_lambda", False):
        if all_dfs:
            df_all = pd.concat(all_dfs, ignore_index=True)
            counts = lcgen.validation.compute_storm_counts(df_all)
            lcgen.validation.verify_lambda(counts, lam_target)
        else:
            print("[warn] No lifecycle data generated; skipping lambda validation.")


if __name__ == "__main__":
    config = load_config(CONFIG_PATH)
    if config["runtime"].get("profile", False):
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

        main()

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
        ps.print_stats(40)
        print(s.getvalue())
    else:
        main()

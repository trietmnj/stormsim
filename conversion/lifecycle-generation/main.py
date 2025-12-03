from pathlib import Path

import numpy as np
import pandas as pd

import lcgen


# -----------------------------
# CONFIG / USER INPUTS
# -----------------------------
INITIALIZE_YEAR = 2033
LIFECYCLE_DURATION = 50  # number of years in a lifecycle
NUM_LCS = 100  # number of lifecycles
LAM_TARGET = 1.7  # local storm recurrence rate (Poisson lambda)

# minimum separation between storms in days
MIN_ARRIVAL_TROP_DAYS = 7.0
MIN_ARRIVAL_EXTRA_DAYS = 4.0  # not used yet, but kept for future

REL_PROB_FILE = "../data/raw/conversion-lifecycle-generation/Relative_probability_bins_Atlantic 4.csv"
STORM_ID_PROB_FILE = (
    "../data/intermediate/conversion-lifecycle-generation/stormprob.csv"
)
OUTPUT_DIRECTORY = Path("../data/intermediate/conversion-lifecycle-generation/")

RNG = np.random.default_rng()  # consistent RNG
PROFILE = False  # set to True to enable cProfile profiling
VALIDATE_LAMBDA = False  # set to True to run validation after simulating


# -----------------------------
# MAIN DRIVER
# -----------------------------
def main():
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    prob_schedule: pd.DataFrame = lcgen.load.load_relative_probabilities(REL_PROB_FILE)
    storm_set: pd.DataFrame = lcgen.load.load_storm_id_cdf(STORM_ID_PROB_FILE)

    # Columns for split outputs
    cols = [
        "lifecycle",
        "year_offset",
        "year",
        "month",
        "day",
        "hour",
        "storm_id",
        # "rcdf",
    ]

    all_dfs: list[pd.DataFrame] = []

    # Full simulation using calibrated lambda
    for lc in range(NUM_LCS):
        df = lcgen.sampling.simulate_lifecycle(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=LAM_TARGET,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
            prob_schedule=prob_schedule,
            storm_set=storm_set,
            show_progress=False,
        )

        # Keep only the ID / timing columns for outputs
        df_ids = df[cols].copy()
        all_dfs.append(df_ids)

    data = pd.concat(all_dfs, ignore_index=True)
    data.to_csv(OUTPUT_DIRECTORY / f"EventDate_LC.csv", index=False)

    if VALIDATE_LAMBDA:
        # Concatenate all lifecycles for validation (use in-memory frames)
        if all_dfs:
            df_all = pd.concat(all_dfs, ignore_index=True)
            counts = lcgen.validation.compute_storm_counts(df_all)
            lcgen.validation.verify_lambda(counts, LAM_TARGET)
        else:
            print("[warn] No lifecycle data generated; skipping lambda validation.")


if __name__ == "__main__":
    if PROFILE:
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

        main()

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")  # or "tottime"
        ps.print_stats(40)  # top 40 entries
        print(s.getvalue())
    else:
        main()

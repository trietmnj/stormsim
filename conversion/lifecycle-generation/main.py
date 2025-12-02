from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

import lcgen


# -----------------------------
# CONFIG / USER INPUTS
# -----------------------------
INITIALIZE_YEAR = 2033
LIFECYCLE_DURATION = 50  # number of years in a lifecycle
NUM_LCS = 100  # number of lifecycles
LAM_TARGET = 1.7  # local storm recurrence rate (Poisson lambda)
YEAR_LENGTH_DAYS = 365.0

# minimum separation between storms in days
MIN_ARRIVAL_TROP_DAYS = 7.0
MIN_ARRIVAL_EXTRA_DAYS = 4.0  # not used yet, but kept for future

REL_PROB_FILE = "../data/raw/conversion-lifecycle-generation/Relative_probability_bins_Atlantic 4.csv"
STORM_ID_PROB_FILE = "../data/intermediate/stormprob.csv"
OUTPUT_DIRECTORY = Path("../data/intermediate/conversion-lifecycle-generation/")

RNG = np.random.default_rng()  # consistent RNG
PROFILE = False  # set to True to enable cProfile profiling
VALIDATE_LAMBDA = True  # set to True to run validation after simulating


# -----------------------------
# LOAD DATA
# -----------------------------
def _load_relative_probabilities(filepath: str):
    """
    Load daily cumulative storm probabilities by (Month, Day).
    Expects columns: 'Month', 'Day', 'Cumulative trop prob'.
    """
    df = pd.read_csv(
        filepath,
        usecols=["Month", "Day", "Cumulative trop prob"],
        dtype={"Month": int, "Day": int, "Cumulative trop prob": float},
    )
    return df


def _load_storm_id_cdf(filepath: str):
    """
    Load storm IDs and their probabilities from CHS master track.
    Expects columns: 'storm_ID', 'DSW' (or similar).
    """
    df = pd.read_csv(filepath, usecols=["storm_ID", "DSW"])
    df = df.sort_values(by="DSW").reset_index(drop=True)

    total_weight = df["DSW"].sum()
    df["probability"] = df["DSW"] / total_weight
    df["cdf"] = np.cumsum(df["probability"])
    return df


# -----------------------------
# SAMPLING
# -----------------------------
def _inverse_cdf_sample(u: np.ndarray, cdf: np.ndarray) -> np.ndarray:
    """
    Given uniform samples u in [0, 1), return indices into cdf such that
    cdf[idx] is the first element > u (standard inverse CDF sampling).
    """
    idx = np.searchsorted(cdf, u, side="right")
    last = len(cdf) - 1
    over = idx > last
    if np.any(over):
        idx[over] = last
    return idx


# -----------------------------
# VALIDATION
# -----------------------------
def compute_storm_counts(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Given a full concatenated lifecycle dataframe,
    return a table of storm counts per (lifecycle, year).
    """
    counts = (
        df_all.groupby(["lifecycle", "year"]).size().rename("n_storms").reset_index()
    )
    return counts


def verify_lambda(counts: pd.DataFrame, lambda_target: float) -> None:
    """
    Print summary stats showing how well the output storm count distribution
    matches the target lambda.
    """
    mean_emp = counts["n_storms"].mean()
    var_emp = counts["n_storms"].var(ddof=0)

    print("\n--- Storm Count Verification ---")
    print(f"Target lambda:       {lambda_target:.4f}")
    print(f"Empirical mean:      {mean_emp:.4f}")
    print(f"Empirical variance:  {var_emp:.4f}")

    # show empirical distribution of N
    value_counts = counts["n_storms"].value_counts().sort_index()
    emp_prob = value_counts / value_counts.sum()

    print("\nk | empirical P(N=k)")
    for k, p in emp_prob.items():
        print(f"{k:2d} | {p:.4f}")


# -----------------------------
# SIMULATION ROUTINES
# -----------------------------
def simulate_lifecycle(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    min_sep_days: float,
    relative_probs_df: pd.DataFrame,
    storm_set: pd.DataFrame,
    show_progress: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> pd.DataFrame:
    """
    Simulate one lifecycle using day-of-year indexing:

    Returns a DataFrame with one row per storm event.
    """
    if rng is None:
        rng = np.random.default_rng()

    records: list[dict] = []

    year_iter = range(duration_years)
    if show_progress:
        from tqdm.auto import tqdm

        year_iter = tqdm(year_iter, desc=f"LC {lifecycle_index}")

    rand = rng.random

    for year_offset in year_iter:
        year = init_year + year_offset

        # 1) Sample for the number of storms this year
        n_events = rng.poisson(lam)
        if n_events == 0:
            continue

        # 2) Day-of-year + hour with min separation (no thinning)
        doy, hour, t, month, day = lcgen.sampling.sample_year_events(
            lam=lam,
            cdf_day=cdf_day,
            min_sep_days=min_sep_days,
            year=year,
            rng=rng,
        )

        n_kept = doy.size
        if n_kept == 0:
            continue

        # 3) populate Storm IDs
        u_id = rand(n_kept)
        idx_id = np.searchsorted(storm_set["cdf"], u_id, side="right")
        sid = storm_set["storm_ID"][idx_id]
        rcdf = storm_set["cdf"][idx_id]

        # 4) Convert day_idx -> month/day for outputs (if desired)
        base = datetime(year, 1, 1)
        for k in range(n_kept):
            dt = base + timedelta(days=int(day_idx[k]) - 1, hours=float(hour[k]))
            records.append(
                {
                    "lifecycle": lifecycle_index,
                    "year_offset": year_offset,
                    "year": year,
                    "day_of_year": int(day_idx[k]),
                    "month": dt.month,
                    "day": dt.day,
                    "hour": dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
                    "storm_id": int(sid[k]),
                    "rcdf": float(rcdf[k]),
                }
            )

    return pd.DataFrame.from_records(records)


# -----------------------------
# MAIN DRIVER
# -----------------------------
def main():
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    relative_probs: pd.DataFrame = _load_relative_probabilities(REL_PROB_FILE)
    storm_set: pd.DataFrame = _load_storm_id_cdf(STORM_ID_PROB_FILE)

    # Columns for split outputs
    cols = [
        "lifecycle",
        "year_offset",
        "year",
        "month",
        "day",
        "hour",
        "storm_id",
        "rcdf",
    ]

    all_dfs: list[pd.DataFrame] = []

    # Full simulation using calibrated lambda
    for lc in range(NUM_LCS):
        df = simulate_lifecycle(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=LAM_TARGET,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
            relative_probs_df=relative_probs,
            storm_set=storm_set,
            # cum_probs_day=cum_probs_day,
            # cdf=cdf,
            # storm_ids=storm_ids,
            show_progress=False,
        )

        # Keep only the ID / timing columns for outputs
        df_ids = df[cols].copy()
        all_dfs.append(df_ids)

        ids_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}.csv"
        df_ids.to_csv(ids_path, index=False)

    if VALIDATE_LAMBDA:
        # Concatenate all lifecycles for validation (use in-memory frames)
        if all_dfs:
            df_all = pd.concat(all_dfs, ignore_index=True)
            counts = compute_storm_counts(df_all)
            verify_lambda(counts, LAM_TARGET)
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

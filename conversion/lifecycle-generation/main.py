from pathlib import Path
import numpy as np
import pandas as pd
from tqdm.auto import tqdm  # <-- progress bar


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
# HELPERS
# -----------------------------
def _load_relative_probabilities(filepath: str):
    """
    Load daily cumulative storm probabilities by (Month, Day).
    Expects columns: 'Month', 'Day', 'Cumulative trop prob'.
    """
    df = pd.read_csv(filepath)
    cum_probs = df["Cumulative trop prob"].to_numpy()
    months = df["Month"].to_numpy(dtype=int)
    days = df["Day"].to_numpy(dtype=int)
    return cum_probs, months, days


def _load_storm_id_cdf(filepath: str):
    """
    Load storm IDs and their probabilities from CHS master track.
    Expects columns: 'storm_ID', 'DSW' (or similar).
    """
    df = pd.read_csv(filepath)
    df = df.sort_values(by="DSW").reset_index(drop=True)

    weights = df["DSW"].to_numpy()
    probs = weights / weights.sum()
    cdf = np.cumsum(probs)
    storm_ids = df["storm_ID"].to_numpy()

    return cdf, storm_ids


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


def _thin_by_min_separation(times: np.ndarray, min_sep_days: float) -> np.ndarray:
    """
    Given sorted times (days since Jan 1), keep only events such that each kept
    event is at least min_sep_days after the last kept one.

    Returns indices into the original `times` array (after sorting).
    """
    n = times.size
    if n == 0:
        return np.empty(0, dtype=int)

    keep = [0]
    last_t = times[0]
    for i in range(1, n):
        if times[i] - last_t >= min_sep_days:
            keep.append(i)
            last_t = times[i]
    return np.asarray(keep, dtype=int)


def _estimate_lambda_eff(
    lam_raw: float,
    cum_probs: np.ndarray,
    months: np.ndarray,
    days: np.ndarray,
    min_sep_days: float,
    cdf: np.ndarray,
    storm_ids: np.ndarray,
    init_year: int,
    duration_years_cal: int = 30,
    num_lcs_cal: int = 30,
) -> float:
    """
    Estimate the effective lambda (mean storms/year) produced by simulate_lifecycle
    when using lam_raw. Uses a smaller calibration run for speed.
    """
    dfs = []
    for lc in range(num_lcs_cal):
        df = simulate_lifecycle(
            lifecycle_index=lc,
            init_year=init_year,
            duration_years=duration_years_cal,
            lam=lam_raw,
            cum_probs=cum_probs,
            months=months,
            days=days,
            min_sep_days=min_sep_days,
            cdf=cdf,
            storm_ids=storm_ids,
            show_progress=False,
        )
        dfs.append(df)

    if not dfs:
        return 0.0

    df_all = pd.concat(dfs, ignore_index=True)
    counts = compute_storm_counts(df_all)  # helper from earlier
    return float(counts["n_storms"].mean())


def calibrate_lam_raw_with_simulator(
    lambda_target: float,
    cum_probs: np.ndarray,
    months: np.ndarray,
    days: np.ndarray,
    min_sep_days: float,
    cdf: np.ndarray,
    storm_ids: np.ndarray,
    init_year: int,
) -> float:
    """
    Binary search lam_raw so that the simulate_lifecycle output
    has mean storms/year ≈ lambda_target.
    """
    lam_low = max(1e-6, lambda_target * 0.5)
    lam_high = lambda_target * 3.0

    # ensure upper bound is high enough
    for _ in range(5):
        mean_high = _estimate_lambda_eff(
            lam_high,
            cum_probs,
            months,
            days,
            min_sep_days,
            cdf,
            storm_ids,
            init_year,
        )
        if mean_high >= lambda_target:
            break
        lam_high *= 2.0

    for _ in range(12):  # 2^12 ≈ 4096, enough precision
        mid = 0.5 * (lam_low + lam_high)
        mean_mid = _estimate_lambda_eff(
            mid,
            cum_probs,
            months,
            days,
            min_sep_days,
            cdf,
            storm_ids,
            init_year,
        )

        if mean_mid < lambda_target:
            lam_low = mid
        else:
            lam_high = mid

    lam_raw = 0.5 * (lam_low + lam_high)
    print(f"[calibration] lam_raw={lam_raw:.4f} gives mean ≈ {lambda_target}")
    return lam_raw


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
    cum_probs: np.ndarray,
    months: np.ndarray,
    days: np.ndarray,
    min_sep_days: float,
    cdf: np.ndarray,
    storm_ids: np.ndarray,
    show_progress: bool = False,
) -> pd.DataFrame:
    """
    Simulate one lifecycle:

    - For each year:
      1) Draw N ~ Poisson(lam) candidate storms.
      2) Sample calendar-based timing (month/day/hour) using cum_probs/months/days.
      3) Build within-year times t (in days), sort, and thin by min_sep_days.
      4) For the kept events, sample storm IDs from the CHS storm-ID CDF.

    Returns a DataFrame with one row per kept storm event.
    """
    records: list[dict] = []

    year_iter = range(duration_years)
    if show_progress:
        from tqdm.auto import tqdm

        year_iter = tqdm(year_iter, desc=f"LC {lifecycle_index}")

    rand = RNG.random  # local alias for speed

    for year_offset in year_iter:
        year = init_year + year_offset

        # 1) Number of storms this year
        n_events = RNG.poisson(lam)
        if n_events == 0:
            continue

        # 2) Sample calendar-based timing (month/day/hour) once
        #    Use cum_probs/months/days for seasonality
        u_time = rand(n_events)
        idx_time = _inverse_cdf_sample(u_time, cum_probs)

        mo = months[idx_time]
        da = days[idx_time]
        hour = rand(n_events) * 24.0

        # 3) Build within-year time, sort, and thin by min separation
        t = da + hour / 24.0
        order = np.argsort(t)

        t = t[order]
        mo = mo[order]
        da = da[order]
        hour = hour[order]

        keep_idx = _thin_by_min_separation(t, min_sep_days)
        if keep_idx.size == 0:
            # All events were too close together in this realization
            continue

        t = t[keep_idx]
        mo = mo[keep_idx]
        da = da[keep_idx]
        hour = hour[keep_idx]
        n_kept = keep_idx.size

        # 4) For those *same* events, sample storm IDs via storm CDF
        u_id = rand(n_kept)
        idx_id = _inverse_cdf_sample(u_id, cdf)

        sid = storm_ids[idx_id]
        rcdf = cdf[idx_id]

        # Collect rows
        for k in range(n_kept):
            records.append(
                {
                    "lifecycle": lifecycle_index,
                    "year_offset": year_offset,
                    "year": year,
                    "month": int(mo[k]),
                    "day": int(da[k]),
                    "hour": float(hour[k]),
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

    # Load inputs
    cum_probs, months, days = _load_relative_probabilities(REL_PROB_FILE)
    cdf, storm_ids = _load_storm_id_cdf(STORM_ID_PROB_FILE)

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

    # 1) Calibrate lam_raw automatically
    lam_raw = calibrate_lam_raw_with_simulator(
        lambda_target=LAM_TARGET,
        cum_probs=cum_probs,
        months=months,
        days=days,
        min_sep_days=MIN_ARRIVAL_TROP_DAYS,
        cdf=cdf,
        storm_ids=storm_ids,
        init_year=INITIALIZE_YEAR,
    )

    # 2) Full simulation using calibrated lam_raw
    all_dfs = []
    for lc in range(NUM_LCS):
        df = simulate_lifecycle(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=lam_raw,
            cum_probs=cum_probs,
            months=months,
            days=days,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
            cdf=cdf,
            storm_ids=storm_ids,
            show_progress=False,
        )
        df_ids = df[cols]
        ids_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}.csv"
        df_ids.to_csv(ids_path, index=False)

    if VALIDATE_LAMBDA:
        # Concatenate all lifecycles for validation
        all_dfs = []
        for lc in range(NUM_LCS):
            ids_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}.csv"
            df_lc = pd.read_csv(ids_path)
            all_dfs.append(df_lc)
        df_all = pd.concat(all_dfs, ignore_index=True)

        counts = compute_storm_counts(df_all)
        verify_lambda(counts, LAM_TARGET)


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

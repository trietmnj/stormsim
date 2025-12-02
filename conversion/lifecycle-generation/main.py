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
LAM = 1.7  # local storm recurrence rate (Poisson lambda)

# minimum separation between storms in days
MIN_ARRIVAL_TROP_DAYS = 7.0
MIN_ARRIVAL_EXTRA_DAYS = 4.0  # not used yet, but kept for future

REL_PROB_FILE = "../data/raw/conversion-lifecycle-generation/Relative_probability_bins_Atlantic 4.csv"
STORM_ID_PROB_FILE = "../data/intermediate/stormprob.csv"
OUTPUT_DIRECTORY = Path("../data/intermediate/conversion-lifecycle-generation/")

RNG = np.random.default_rng()  # consistent RNG
PROFILE = False  # set to True to enable cProfile profiling


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
    Simulate one lifecycle of storms, using:

      - `cum_probs`, `months`, `days` for timing (calendar-based)
      - `cdf`, `storm_ids` for assigning storm IDs / probabilities

    The key point: event *timing* is simulated once per year and then both
    calendar fields and storm IDs are attached to the same events.
    """

    records: list[dict] = []

    year_iter = (
        tqdm(
            range(duration_years),
            desc=f"LC {lifecycle_index} (combined)",
            leave=False,
        )
        if show_progress
        else range(duration_years)
    )

    # Local RNG shortcuts (micro-optimization)
    rand = RNG.random

    for year_offset in year_iter:
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
            # All events too close together in this realization
            continue

        mo = mo[keep_idx]
        da = da[keep_idx]
        hour = hour[keep_idx]
        t = t[keep_idx]
        n_kept = keep_idx.size

        # 4) For those *same* events, sample storm IDs via storm CDF
        u_id = rand(n_kept)
        idx_id = _inverse_cdf_sample(u_id, cdf)

        sid = storm_ids[idx_id]
        rcdf = cdf[idx_id]

        # 5) Record rows (calendar fields + storm IDs share the same timing)
        year = init_year + year_offset
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
                    "t_within_year": float(t[k]),  # optional, handy for QA
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

    # Run lifecycles with a progress bar
    for lc in tqdm(range(NUM_LCS), desc="Simulating lifecycles"):
        df = simulate_lifecycle(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=LAM,
            cum_probs=cum_probs,
            months=months,
            days=days,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
            cdf=cdf,
            storm_ids=storm_ids,
            show_progress=False,  # outer tqdm already used
        )
        df_ids = df[cols]
        ids_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}.csv"
        df_ids.to_csv(ids_path, index=False)


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

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
def _simulate_lifecycle_with_calendar(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    cum_probs: np.ndarray,
    months: np.ndarray,
    days: np.ndarray,
    min_sep_days: float,
    show_progress: bool = False,
) -> pd.DataFrame:
    records: list[dict] = []

    year_iter = (
        tqdm(
            range(duration_years),
            desc=f"LC {lifecycle_index} (calendar)",
            leave=False,
        )
        if show_progress
        else range(duration_years)
    )

    for year_offset in year_iter:
        n_events = RNG.poisson(lam)
        if n_events == 0:
            continue

        # 1) sample events once
        u = RNG.random(n_events)  # no need to sort u
        idx = _inverse_cdf_sample(u, cum_probs)

        mo = months[idx]
        da = days[idx]
        hour = RNG.random(n_events) * 24.0

        # 2) build within-year time and sort
        t = da + hour / 24.0
        order = np.argsort(t)
        t = t[order]
        mo = mo[order]
        da = da[order]
        hour = hour[order]

        # 3) thin by min separation
        keep_idx = _thin_by_min_separation(t, min_sep_days)
        if keep_idx.size == 0:
            # all storms too close together given this year's realization
            continue

        year = init_year + year_offset
        for k in keep_idx:
            records.append(
                {
                    "lifecycle": lifecycle_index,
                    "year_offset": year_offset,
                    "year": year,
                    "month": int(mo[k]),
                    "day": int(da[k]),
                    "hour": float(hour[k]),
                }
            )

    return pd.DataFrame.from_records(records)


def _simulate_lifecycle_with_storm_ids(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    cdf: np.ndarray,
    storm_ids: np.ndarray,
    min_sep_days: float,
    show_progress: bool = False,
) -> pd.DataFrame:
    """
    Simulate one lifecycle of storms using the CHS storm ID probability file.
    Here we sample storm IDs and assign random (month, day) within a year.
    """
    records: list[dict] = []

    year_iter = (
        tqdm(
            range(duration_years),
            desc=f"LC {lifecycle_index} (Storm ID)",
            leave=False,
        )
        if show_progress
        else range(duration_years)
    )

    for year_offset in year_iter:
        n_events = RNG.poisson(lam)
        if n_events == 0:
            continue

        # 1) sample storm IDs once
        u = RNG.random(n_events)
        idx = _inverse_cdf_sample(u, cdf)

        sid = storm_ids[idx]
        rcdf = cdf[idx]

        # random month/day (placeholder until you wire in real seasonal calendar)
        mo = RNG.integers(1, 13, size=n_events)  # 1–12
        da = RNG.integers(1, 32, size=n_events)  # 1–31

        hour = RNG.random(n_events) * 24.0

        # 2) build within-year time and sort
        t = da + hour / 24.0
        order = np.argsort(t)
        t = t[order]
        mo = mo[order]
        da = da[order]
        hour = hour[order]
        sid = sid[order]
        rcdf = rcdf[order]

        # 3) thin by min separation
        keep_idx = _thin_by_min_separation(t, min_sep_days)
        if keep_idx.size == 0:
            continue

        year = init_year + year_offset
        for k in keep_idx:
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

    # Run lifecycles with a progress bar
    for lc in tqdm(range(NUM_LCS), desc="Simulating lifecycles"):
        # --- Calendar-based simulation (uses Month/Day/CDF from file)
        df_calendar = _simulate_lifecycle_with_calendar(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=LAM,
            cum_probs=cum_probs,
            months=months,
            days=days,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
        )

        calendar_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}_calendar.csv"
        df_calendar.to_csv(calendar_path, index=False)

        # --- Storm-ID-based simulation
        df_ids = _simulate_lifecycle_with_storm_ids(
            lifecycle_index=lc,
            init_year=INITIALIZE_YEAR,
            duration_years=LIFECYCLE_DURATION,
            lam=LAM,
            cdf=cdf,
            storm_ids=storm_ids,
            min_sep_days=MIN_ARRIVAL_TROP_DAYS,
        )

        ids_path = OUTPUT_DIRECTORY / f"EventDate_LC_{lc}_with_ids.csv"
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

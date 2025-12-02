from pathlib import Path
import numpy as np
import pandas as pd


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

REL_PROB_FILE = (
    r"C:\Users\RDCRLHPS\Documents\STORMSIM CHART\Relative_probability_bins_Atlantic.csv"
)
STORM_ID_PROB_FILE = r"C:\Users\RDCRLHPS\Documents\Chart-Python\stormprob.csv"
OUTPUT_DIRECTORY = Path(r"C:\Users\RDCRLHPS\Documents\Chart-Python")

RNG = np.random.default_rng()  # consistent RNG


# -----------------------------
# HELPERS
# -----------------------------
def load_relative_probabilities(filepath: str):
    """
    Load daily cumulative storm probabilities by (Month, Day).
    Expects columns: 'Month', 'Day', 'Cumulative trop prob'.
    """
    df = pd.read_csv(filepath)
    cum_probs = df["Cumulative trop prob"].to_numpy()
    months = df["Month"].to_numpy(dtype=int)
    days = df["Day"].to_numpy(dtype=int)
    return cum_probs, months, days


def load_storm_id_cdf(filepath: str):
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


def inverse_cdf_sample(u: np.ndarray, cdf: np.ndarray) -> np.ndarray:
    """
    Given uniform samples u in [0, 1), return indices into cdf such that
    cdf[idx] is the first element > u (standard inverse CDF sampling).
    """
    idx = np.searchsorted(cdf, u, side="right")
    idx = np.clip(idx, 0, len(cdf) - 1)
    return idx


def enforce_min_separation_days(times: np.ndarray, min_sep_days: float) -> bool:
    """
    Simple check: given within-year times (days since Jan 1, as floats),
    returns True if all adjacent events are at least min_sep_days apart.
    """
    if len(times) <= 1:
        return True
    return np.all(np.diff(times) >= min_sep_days)


# -----------------------------
# SIMULATION ROUTINES
# -----------------------------
def simulate_lifecycle_with_calendar(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    cum_probs: np.ndarray,
    months: np.ndarray,
    days: np.ndarray,
    min_sep_days: float,
) -> pd.DataFrame:
    """
    Simulate one lifecycle of storms using the daily calendar probability bins
    (Month, Day, cumulative probability).
    """
    records = []

    for year_offset in range(duration_years):
        n_events = RNG.poisson(lam)

        if n_events == 0:
            continue

        # Sample storm times within the year and enforce min separation
        while True:
            u = np.sort(RNG.random(n_events))
            idx = inverse_cdf_sample(u, cum_probs)

            mo = months[idx]
            da = days[idx]
            hour = RNG.random(n_events) * 24.0

            # A crude within-year time measure: day + hour/24
            # (ignores month length; you can refine if needed)
            t = da + hour / 24.0

            if enforce_min_separation_days(t, min_sep_days):
                break

        year = init_year + year_offset
        for k in range(n_events):
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


def simulate_lifecycle_with_storm_ids(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    cdf: np.ndarray,
    storm_ids: np.ndarray,
    min_sep_days: float,
) -> pd.DataFrame:
    """
    Simulate one lifecycle of storms using the CHS storm ID probability file.
    Here we sample storm IDs and assign random (month, day) within a year.
    """
    records = []

    for year_offset in range(duration_years):
        n_events = RNG.poisson(lam)

        if n_events == 0:
            continue

        while True:
            u = np.sort(RNG.random(n_events))
            idx = inverse_cdf_sample(u, cdf)

            sid = storm_ids[idx]
            rcdf = cdf[idx]

            # For now: random month/day (you can replace with a calendar file)
            mo = RNG.integers(1, 13, size=n_events)  # 1–12
            da = RNG.integers(1, 32, size=n_events)  # 1–31 (no month-length check)

            hour = RNG.random(n_events) * 24.0
            t = da + hour / 24.0

            if enforce_min_separation_days(t, min_sep_days):
                break

        year = init_year + year_offset
        for k in range(n_events):
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
    cum_probs, months, days = load_relative_probabilities(REL_PROB_FILE)
    cdf, storm_ids = load_storm_id_cdf(STORM_ID_PROB_FILE)

    # Run lifecycles
    for lc in range(NUM_LCS):
        # --- Calendar-based simulation (uses Month/Day/CDF from file)
        df_calendar = simulate_lifecycle_with_calendar(
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
        df_ids = simulate_lifecycle_with_storm_ids(
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

        print(
            f"Processed lifecycle {lc} "
            f"(calendar events: {len(df_calendar)}, id events: {len(df_ids)})"
        )


if __name__ == "__main__":
    main()

# conversion/lifecycle-generation/lcgen/sampling.py
import numpy as np
import pandas as pd
from typing import Tuple, Optional

from tqdm.auto import tqdm

import lcgen

# simulate_lifecycle → _sample_year_events → (_sample_yearly_storm_count & _sample_layout_with_min_sep → _sample_day_of_year)


# -----------------------------
# SIMULATION ROUTINES
# -----------------------------
def simulate_lifecycle(
    lifecycle_index: int,
    init_year: int,
    duration_years: int,
    lam: float,
    min_sep_days: float,
    prob_schedule: pd.DataFrame,
    storm_set: pd.DataFrame,
    show_progress: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> pd.DataFrame:
    """
    Simulate one lifecycle
    """
    if rng is None:
        rng = np.random.default_rng()

    records: list[dict] = []

    year_iter = range(duration_years)
    if show_progress:
        year_iter = tqdm(year_iter, desc=f"LC {lifecycle_index}")

    rand = rng.random

    n_failed = 0

    for year_offset in year_iter:
        year = init_year + year_offset

        # Sample all events for this year (count + layout handled internally)
        doy, hour, failed = _sample_year(
            lam=lam,
            prob_schedule=prob_schedule,
            min_sep_days=min_sep_days,
            rng=rng,
        )

        n_kept = doy.size
        if n_kept == 0:
            continue

        # populate Storm IDs
        u_id = rand(n_kept)
        idx_id = np.searchsorted(storm_set["cdf"], u_id, side="right")
        sid = storm_set["storm_id"].to_numpy()[idx_id]
        rcdf = storm_set["cdf"].to_numpy()[idx_id]
        month, day = lcgen.utils.doy_to_month_day(year, doy)

        for k in range(n_kept):
            records.append(
                {
                    "lifecycle": lifecycle_index,
                    "year_offset": year_offset,
                    "year": year,
                    "day_of_year": int(doy[k]),
                    "month": int(month[k]),
                    "day": int(day[k]),
                    "hour": float(hour[k]),
                    "storm_id": int(sid[k]),
                    "rcdf": float(rcdf[k]),
                }
            )
    return pd.DataFrame.from_records(records)


def _sample_year(
    lam: float,
    prob_schedule: pd.DataFrame,
    min_sep_days: float,
    rng: Optional[np.random.Generator] = None,
):
    """
    High-level: sample all storms in a given year, enforcing:
      - N ~ Poisson(lam) (with feasibility cap)
      - daily seasonality via cdf_day
      - minimum separation via rejection sampling

    Returns
    -------
    doy   : np.ndarray (int)
    hour  : np.ndarray (float)
    failed: bool
    """
    if rng is None:
        rng = np.random.default_rng()

    # 1) storm count yearly
    yearly_storm_count = _sample_storm_count_in_year(
        lam, prob_schedule, min_sep_days, rng
    )
    if yearly_storm_count == 0:
        return (np.array([], dtype=int), np.array([], dtype=float), True)

    # 2) sample with min separation
    doy, hour, failed = _sample_with_minimal_arrival(
        n_storms=yearly_storm_count,
        prob_schedule=prob_schedule,
        min_sep_days=min_sep_days,
        rng=rng,
    )

    return doy, hour, failed


def _sample_storm_count_in_year(
    lam: float,
    prob_schedule: pd.DataFrame,
    min_sep_days: float,
    rng: np.random.Generator,
) -> int:
    """
    Sample N ~ Poisson(lam) for the count of storms in a year,
    """
    n_events = rng.poisson(lam)
    if n_events == 0:
        return 0
    max_feasible = int(np.floor(len(prob_schedule) / min_sep_days)) + 1
    n_events = min(n_events, max_feasible)
    return n_events


def _sample_with_minimal_arrival(
    n_storms: int,
    prob_schedule: pd.DataFrame,
    min_sep_days: float,
    rng: np.random.Generator,
    max_attempts: int = 1000,
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """
    Given n_events, sample DOY + hour with min separation.
    """
    if n_storms <= 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            False,
        )

    last_doy = last_hour = None

    failed = True
    gaps = None
    for _ in range(max_attempts):
        doy = _sample_day_of_year(prob_schedule, rng, n_storms)
        hour = rng.random(n_storms) * 24.0

        timestamps = doy + hour / 24.0
        order = np.argsort(timestamps)
        doy = doy[order]
        hour = hour[order]
        timestamps = timestamps[order]
        last_doy, last_hour = doy, hour
        if n_storms <= 1:
            failed = False
            break

        gaps = np.diff(timestamps)
        if np.all(gaps >= min_sep_days):
            failed = False
            # return last_doy, last_hour, False
            break  # success

    if last_doy is None:
        failed = False
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            False,
        )
    if failed:
        print("Failed to sample with min separation:")
        print(f"n_storms={n_storms} min_sep_days: {min_sep_days}")
        print(f"timestamps={timestamps}, gaps={gaps}")

    return last_doy, last_hour, failed


def _sample_day_of_year(
    prob_schedule: pd.DataFrame,
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Sample n day-of-year from a daily CDF.
    """
    u = rng.random(n)
    idx = np.searchsorted(prob_schedule["trop_day_cdf"], u, side="right")
    return prob_schedule.iloc[idx]["day_of_year"].to_numpy().astype(int)

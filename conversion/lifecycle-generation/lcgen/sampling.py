# conversion/lifecycle-generation/lcgen/sampling.py
import numpy as np
import pandas as pd
import datetime as dt
from typing import Tuple, Optional

import lcgen


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
    Simulate one lifecycle using day-of-year indexing.

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

        # Sample all events for this year (count + layout handled internally)
        doy, hour, t, month, day = _sample_year_events(
            lam=lam,
            prob_schedule=prob_schedule,
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
        sid = storm_set["storm_id"].to_numpy()[idx_id]
        rcdf = storm_set["cdf"].to_numpy()[idx_id]

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


def _sample_poisson_count_with_cap(
    lam: float,
    cdf_day: np.ndarray,
    min_sep_days: float,
    rng: np.random.Generator,
) -> int:
    """
    Sample N ~ Poisson(lam) and cap at the maximum
    number of events that can fit in the year with min_sep_days.
    """
    n_events = rng.poisson(lam)
    if n_events == 0:
        return 0

    year_length = len(cdf_day)  # e.g. 365
    max_feasible = int(np.floor(year_length / min_sep_days)) + 1
    n_events = min(n_events, max_feasible)

    return n_events


def _sample_day_of_year(
    prob_schedule: pd.DataFrame,
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Sample n day-of-year values (1..len(cdf_day)) from a daily CDF.
    Returns an array of day-of-year.
    """
    u = rng.random(n)
    idx = np.searchsorted(prob_schedule["trop_day_cdf"], u, side="right")
    return prob_schedule.iloc[idx]["day_of_year"].to_numpy().astype(int)


def _sample_layout_with_min_sep(
    n_events: int,
    prob_schedule: pd.DataFrame,
    min_sep_days: float,
    rng: np.random.Generator,
    max_attempts: int = 100,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Given n_events, sample DOY + hour with min separation.
    Returns (doy, hour, t) sorted by t.
    """
    if n_events <= 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            np.array([], dtype=float),
        )

    last_doy = last_hour = last_t = None

    for _ in range(max_attempts):
        doy = _sample_day_of_year(prob_schedule, rng, n_events)
        hour = rng.random(n_events) * 24.0

        t = doy + hour / 24.0
        order = np.argsort(t)

        doy = doy[order]
        hour = hour[order]
        t = t[order]

        last_doy, last_hour, last_t = doy, hour, t

        if n_events <= 1:
            break

        gaps = np.diff(t)
        if np.all(gaps >= min_sep_days):
            break  # success

    if last_doy is None:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            np.array([], dtype=float),
        )

    return last_doy, last_hour, last_t


def _sample_year_events(
    lam: float,
    prob_schedule: pd.DataFrame,
    min_sep_days: float,
    year: int,
    rng: Optional[np.random.Generator] = None,
    max_attempts: int = 100,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    High-level: sample all storms in a given year, enforcing:
      - N ~ Poisson(lam) (with feasibility cap)
      - daily seasonality via cdf_day
      - minimum separation via rejection sampling

    Returns
    -------
    doy   : np.ndarray (int)
    hour  : np.ndarray (float)
    t     : np.ndarray (float, days since Jan 1)
    month : np.ndarray (int)
    day   : np.ndarray (int)
    """
    if rng is None:
        rng = np.random.default_rng()

    cdf_day = prob_schedule["trop_day_cdf"].to_numpy()

    # 1) count
    n_events = _sample_poisson_count_with_cap(lam, cdf_day, min_sep_days, rng)
    if n_events == 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=int),
            np.array([], dtype=int),
        )

    # 2) layout with min separation
    doy, hour, t = _sample_layout_with_min_sep(
        n_events=n_events,
        prob_schedule=prob_schedule,
        min_sep_days=min_sep_days,
        rng=rng,
        max_attempts=max_attempts,
    )

    if doy.size == 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=int),
            np.array([], dtype=int),
        )

    # 3) convert to calendar
    month, day = lcgen.utils.doy_to_month_day(year, doy)
    return doy, hour, t, month, day

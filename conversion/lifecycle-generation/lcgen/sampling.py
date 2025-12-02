import numpy as np
from typing import Tuple, Optional


def sample_poisson_count_with_cap(
    lam: float,
    cdf_day: np.ndarray,
    min_sep_days: float,
    rng: np.random.Generator,
) -> int:
    """
    Sample N ~ Poisson(lam) and (optionally) cap at the maximum
    number of events that can fit in the year with min_sep_days.
    """
    n_events = rng.poisson(lam)
    if n_events == 0:
        return 0

    year_length = len(cdf_day)  # e.g. 365
    max_feasible = int(np.floor(year_length / min_sep_days)) + 1

    if n_events > max_feasible:
        n_events = max_feasible

    return n_events


def sample_day_of_year(
    cdf_day: np.ndarray,
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """Sample n day-of-year values (1..len(cdf_day)) from a daily CDF."""
    u = rng.random(n)
    idx = np.searchsorted(cdf_day, u, side="right")
    return idx + 1  # 1-based DOY


def sample_layout_with_min_sep(
    n_events: int,
    cdf_day: np.ndarray,
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
        doy = sample_day_of_year(cdf_day, rng, n_events)
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


def sample_year_events(
    lam: float,
    cdf_day: np.ndarray,
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

    # 1) count
    n_events = sample_poisson_count_with_cap(lam, cdf_day, min_sep_days, rng)
    if n_events == 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=int),
            np.array([], dtype=int),
        )

    # 2) layout with min separation
    doy, hour, t = sample_layout_with_min_sep(
        n_events=n_events,
        cdf_day=cdf_day,
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
    month, day = doy_to_month_day_vec(year, doy)
    return doy, hour, t, month, day

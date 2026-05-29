"""
Input and options dataclasses for the StormSim-PST (Probabilistic Simulation
Technique) hazard curve fitting pipeline. Ported from StormSim_PST.m.
"""

import numpy as np
from pydantic import ConfigDict, Field, field_validator
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(arbitrary_types_allowed=True, extra="ignore"))
class ResponseData:
    """
    Observed response dataset passed into the PST pipeline.

    data columns: [timestamp (datenum), response (no tides), response (with tides)]
    """

    data: np.ndarray
    flag_value: list[float] | None = None  # sentinel values to exclude before fitting
    annual_rate: float | None = None  # λ — mean annual rate of events (events/yr); Timeseries only
    n_years: float | None = None  # record length in years; POT only
    slc: float | None = None  # sea level change implicit in the storm surge (metres)
    data_type: str = "POT"  # 'POT' or 'Timeseries'
    gpr_mdl: object | None = None  # GPR metamodel for skew-tide prediction; apply_skew only


@dataclass(config=ConfigDict(extra="ignore"))
class PSTOptions:
    """Algorithmic options controlling the PST fitting pipeline."""

    t_lag: float | None = None  # inter-event time lag (hours); Timeseries only
    gpd_criterion: int = Field(default=1, ge=1, le=2)  # 1 = sample-intensity (λ), 2 = min-WMSE
    apply_skew: bool = False   # add GPR-predicted skew tides to surge
    use_aep: bool = False      # express frequencies as AEP instead of AEF
    percentiles: list[float] | None = None  # confidence-limit percentages, max 4 values
    apply_gpd: bool = False    # force GPD fit regardless of sample size
    bootstrap_sims: int = Field(default=100, gt=0)  # number of bootstrap resampling iterations

    @field_validator("percentiles")
    @classmethod
    def validate_percentiles(cls, v):
        if v is not None and any(not 0 <= p <= 100 for p in v):
            raise ValueError("All percentiles must be in [0, 100]")
        return v

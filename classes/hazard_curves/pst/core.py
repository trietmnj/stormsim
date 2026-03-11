from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ResponseData:
    data: np.ndarray
    flag_value: list[float] | None = None
    lambda_: float | None = None
    Nyrs: float | None = None
    SLC: float | None = None
    DataType: str = "POT"
    gprMdl: object | None = None


@dataclass
class PSTOptions:
    tLag: float | None = None
    GPD_TH_crit: int = 1
    ind_Skew: int = 0
    use_AEP: int = 0
    prc: list[float] | None = None
    apply_GPD_to_SS: int = 0
    #    stat_print: int = 0
    #    create_plots: int = 0
    y_log: int = 0
    bootstrap_sims: int = 100

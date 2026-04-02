import logging

import numpy as np
from numpy.typing import ArrayLike


class POT:
    """
    SOFTWARE NAME:
        StormSim-POT (Statistics)

    DESCRIPTION:
    This script generates the Peaks-Over-Threshold (POT) sample from a raw
    time series data set.

    INPUT ARGUMENTS:
        dt = timestamps of response data; as a datenum vector
        Resp = response data; specified as a vector. Cannot be a PDS/POT sample.
        tLag = inter-event time in hours; specified as a scalar
        lambda = mean annual rate of events; specified as a scalar
        Nyrs = record length in years; specified as a scalar

    OUTPUT ARGUMENTS:
    POTout = response POT sample; as a matrix with format:
        col(01): timestamps of POT values
        col(02): POT values
        col(03): data time range used for selection of POT value: lower bound
        col(04): data time range used for selection of POT value: upper bound
    Threshold = selected threshold for identification of excesses.

    AUTHORS:
        Norberto C. Nadal-Caraballo, PhD (NCNC)
        Efrain Ramos-Santiago (ERS)
        Michael-Angelo Y.-H. Lam (MYL)

    CONTRIBUTORS:
        ERDC-CHL Coastal Hazards Group

    HISTORY OF REVISIONS:
    20200903-ERS: revised.
    20200914-ERS: revised.
    20231207-LAA: Revised to add noice to duplicate values in POT sample.
    202511XX-MYL: Converted MATLAB code to Python
    """

    def __init__(
        self,
        dt: ArrayLike,
        response: ArrayLike,
        time_lag: float,
        return_rate: float,
        n_yrs: float,
        threshold_multpiler: float = 1.0,
    ) -> None:

        _MULTIPLIER_CHECK_ = 0.1
        _TIME_LAG_CHECK = 48
        try:
            dt = np.array(dt)
        except TypeError:
            raise TypeError(
                "Timestamp of response data does not appear to be a vector."
            )

        try:
            response = np.array(response)
        except TypeError:
            raise TypeError("Response data does not appear to be a vector.")

        if threshold_multpiler <= _MULTIPLIER_CHECK_ and time_lag < _TIME_LAG_CHECK:
            msg = f"""Threshold multipler set below {_MULTIPLIER_CHECK_:f} with inter-event time set below {_TIME_LAG_CHECK:d} hours.
              An almost contious time serries will be created in response matrix."""
            logging.warning(msg)

        # Converting from days to hours
        time_lag /= 24

        self._dt: np.ndarray = dt
        self._resp: np.ndarray = response
        self._t_lag = time_lag
        self._lambda = return_rate
        self._n_yrs = n_yrs

        self._th_mult = threshold_multpiler

    def compute(self) -> tuple[ArrayLike, ArrayLike]:

        th_mult = self._th_mult
        avg_resp = np.mean(self._resp)
        std_resp = np.std(self._resp, mean=avg_resp)

        # Determine the threshold that yields a required amount of peak response events
        n_storms = 10**5
        # NOTE: Add max iteration check
        dt = id = []
        while n_storms > (self._n_yrs * th_mult):

            # Compute threshold and identify response values above it
            thresh = avg_resp + std_resp * th_mult
            index = np.argwhere(self._resp > thresh)

            # Take corresponding time values
            dt = self._dt[index]

            # Compute sample inter-event times

            filt = np.diff(dt) <= self._t_lag
            dt = np.concatenate([1, filt, 0])
            # dt = [1;np.diff(dt)<= self._t_lag ;0];

            # Identify inter-event times longer than tLag
            id = np.argwhere(dt == 0)

            # Compute amount of resulting events and increase the multiplier
            n_storms = len(id)
            th_mult += 0.01

        shp = len(dt), len(id)
        stm_col = np.full(shp, np.nan)
        resp_peak = np.full(shp, np.nan)

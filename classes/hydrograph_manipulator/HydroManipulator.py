import json
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import os
import glob
from datetime import datetime, timedelta
from collections.abc import Iterable
import csv

class HydroManipulator:
    def __init__(self, config_path=None):
        """
        Initialize HydroManipulator with optional JSON config.
        """
        self.config = {}
        
        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path):
        """
        Load configuration from JSON file.
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)[0]  # assuming single dict in list

    def correct_bias(self, surge_val, Ba, Br):
        """
        Calculates the surge response based on Ba and Br parameters.
        
        Args:
            surge_val (float or np.array): The input surge value (x).
            Ba (float): B_a_SWL parameter.
            Br (float): B_r_SWL parameter.
            
        Returns:
            float or np.array: The calculated result.
        """
        # 1. Calculate the sign term: Ba / |Ba|
        sign_Ba = Ba / np.abs(Ba)
        
        # 2. Calculate the term inside the square root
        # MATLAB: 1./B_a_SWL.^2 + 1./(B_r_SWL .* x).^2
        term_inside_sqrt = (1 / Ba**2) + (1 / (Br * surge_val)**2)
        
        # 3. Final Calculation
        # MATLAB: x - (sign_Ba) ./ sqrt(...)
        result = surge_val - (sign_Ba / np.sqrt(term_inside_sqrt))
        
        return result

    def add_slr(self, data_in, adjustment):
        """
        Apply sea level rise adjustment if enabled in config.
        """
        if self.config.get("add_slr", ["False"])[0] == "True":
            pass
        return np.array(data_in)

    def add_tides(self, data_in, time_in, tide_signal, tide_time):
        # Interp Tidal Signal To Input Signal 
        interp_tide = self.interp_hydrograph(tide_signal, tide_time, time_in)
        # Add Adjustment
        data_with_tides = data_in + interp_tide

        return data_with_tides

    def add_depth_limitation(self, data_in, adjustment):
        """
        Apply depth limitation if enabled in config.
        """
        if self.config.get("add_depth_limitation", ["False"])[0] == "True":
            pass
        return np.array(data_in)

    def interp_hydrograph(self, y, t, tq):
        """
        Linear interpolation of signal values at query times.

        Parameters
        ----------
        y : array-like
            Values of original signal
        t : array-like of datetime
            Time values of original signal
        tq : array-like of datetime
            Query time points

        Returns
        -------
        yq : np.ndarray
            Interpolated values at tq
        """
        # Convert datetime arrays to numeric (seconds since t[0])
        t0 = t[0]
        t_sec  = np.array([(ti - t0).total_seconds() for ti in t])
        tq_sec = np.array([(tqi - t0).total_seconds() for tqi in tq])

        # Build linear interpolator
        f = interp1d(t_sec, y, kind="linear", fill_value="extrapolate")

        # Evaluate at query points
        yq = f(tq_sec)
        return yq


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

    def add_slr(self, data_in, adjustment):
        """
        Apply sea level rise adjustment if enabled in config.
        """
        if self.config.get("add_slr", ["False"])[0] == "True":
            pass
        return np.array(data_in)

    def add_tides(self, data_in, adjustment):
        """
        Apply tidal adjustment if enabled in config.
        """
        if self.config.get("add_tides", ["False"])[0] == "True":
            pass
        return np.array(data_in)

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

    
    def list_h5_files(self):
        files = glob.glob(os.path.join(self.config["node_data_path"], "*.h5"))
        return [os.path.basename(f) for f in files]

    def chs_wave_model_header_locator(self, headers):
        """
        Identify the actual header strings for Hm0, Tp/Tm, and wave direction.

        Parameters
        ----------
        headers : list of str
            List of header strings from the converted CHS file.

        Returns
        -------
        matched_headers : dict
            Dictionary with keys "Hm0", "Tp", "wDir" containing the actual matched header strings.
        Tp_special : int
            Flag value: 0 if Tp is found, 1 if only Tm is found.
        """

        # --- Hm0 ---
        hm0_candidates = [
            "Zero Moment Wave Height",
            "Significant Wave Height",
            "Significant Wave Height Total Sea"
        ]
        hm0 = next((h for h in hm0_candidates if h in headers), None)
        if hm0 is None:
            raise ValueError("Hm0 not found.")

        # --- Tp or Tm ---
        tp_candidates = [
            "Peak Spectral Wave Period Total Sea",
            "Peak Period",
            "Smoothed Peak Period",
            "Peak Wave Period"
        ]
        tp = next((h for h in tp_candidates if h in headers), None)
        if tp is None:
            tm_candidates = ["Mean Wave Period"]
            tp = next((h for h in tm_candidates if h in headers), None)
            if tp is None:
                raise ValueError("Tp/Tm not found.")
            Tp_special = 1  # Tm case
        else:
            Tp_special = 0  # Tp case

        # --- Wave direction ---
        wdir_candidates = [
            "Mean Wave Direction Total Sea",
            "Mean Wave Direction"
        ]
        wdir = next((h for h in wdir_candidates if h in headers), None)
        if wdir is None:
            raise ValueError("Mean Wave Direction not found.")

        # --- Result ---
        matched_headers = {
            "Hm0": hm0,
            "Tp": tp,
            "wDir": wdir
        }

        return matched_headers, Tp_special
    
    def parse_timestamps(self, arr):
        """
        Convert an array of floats in YYYYMMDDHHMM format into datetimes,
        and compute timestep differences in seconds.
        
        Parameters
        ----------
        arr : np.ndarray
            Array of floats like 200007110510.0
        
        Returns
        -------
        dates : list of datetime
            Parsed datetime objects
        dts : np.ndarray
            Differences between consecutive datetimes in seconds
        """
        # Convert each float to datetime
        dates = [datetime.strptime(str(int(x)), "%Y%m%d%H%M") for x in arr]
        
        # Compute differences in seconds
        dts = np.array([
            (dates[i+1] - dates[i]).total_seconds()
            for i in range(len(dates)-1)
        ])/60
        
        return dates, dts
    
    def datetime_vector(self, seed_date, dt_minutes, length):
        """
        Create an array of datetimes starting from seed_date,
        spaced by dt_minutes, with given length.
        
        Parameters
        ----------
        seed_date : datetime
            Starting datetime
        dt_minutes : int or float
            Step size in minutes
        length : int
            Number of elements in the vector
        
        Returns
        -------
        list of datetime
        """
        step = timedelta(minutes=dt_minutes)
        return [seed_date + i*step for i in range(length)]

    def write_dict_to_csv(self, data_dict, filename):
        """
        Write a dictionary to CSV.
        - Scalar fields are broadcast to match vector length.
        - Vector fields are written row-wise.
        
        Parameters
        ----------
        data_dict : dict
            Dictionary with scalar and/or vector fields.
        filename : str
            Output CSV filename
        """
        # Normalize values: convert scalars to repeated arrays
        normalized = {}
        max_len = 1
        
        # First pass: find max vector length
        for key, val in data_dict.items():
            if isinstance(val, Iterable) and not isinstance(val, (str, bytes)):
                length = len(val)
            else:
                length = 1
            max_len = max(max_len, length)
        
        # Second pass: broadcast scalars
        for key, val in data_dict.items():
            if isinstance(val, Iterable) and not isinstance(val, (str, bytes)):
                arr = list(val)
            else:
                arr = [val] * max_len
            normalized[key] = arr
        
        # Write to CSV
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=normalized.keys())
            writer.writeheader()
            for i in range(max_len):
                row = {k: normalized[k][i] for k in normalized}
                writer.writerow(row)
                
    def write_dicts_to_csv(self, dicts, filename):
        """
        Write a list of dictionaries to a single CSV file.
        - Scalars are broadcast to match the longest vector length *within that dictionary*.
        - Vectors are written row-wise.

        Parameters
        ----------
        dicts : list of dict
            Each dictionary may contain scalar and/or vector fields.
        filename : str
            Output CSV filename
        """

        # Collect all fieldnames across dictionaries
        all_fields = set()
        for d in dicts:
            all_fields.update(d.keys())
            fieldnames = list(all_fields)

        normalized_dicts = []
        for d in dicts:
            # Find max vector length for this dict
            local_max = 1
            for val in d.values():
                if isinstance(val, Iterable) and not isinstance(val, (str, bytes)):
                    local_max = max(local_max, len(val))

            # Broadcast scalars to local_max
            normalized = {}
            for key in fieldnames:
                val = d.get(key, None)
                if isinstance(val, Iterable) and not isinstance(val, (str, bytes)):
                    arr = list(val)
                else:
                    arr = [val] * local_max
                normalized[key] = arr
            normalized_dicts.append(normalized)

        # Write to CSV
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for nd in normalized_dicts:
                length = len(next(iter(nd.values())))
                for i in range(length):
                    row = {k: nd[k][i] for k in fieldnames}
                    writer.writerow(row)

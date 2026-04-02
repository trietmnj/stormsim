# Import Packages 
from datetime import datetime, timedelta
import numpy as np

def parse_hour_float(hour_float):
    """Parses a float hour (e.g. 12.5) into hours, minutes, seconds."""
    hours = int(hour_float)
    minutes_remainder = (hour_float - hours) * 60
    minutes = int(minutes_remainder)
    seconds = int((minutes_remainder - minutes) * 60)
    return hours, minutes, seconds

def parse_timestamps(arr):
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
    
def datetime_vector(seed_date, dt_minutes, length):
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

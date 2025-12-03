# noaa-requests/noaa-py/noaapy/gap_filler.py
import numpy as np
import pandas as pd


def gap_filler(
    data: pd.DataFrame,
    stDates,
    endDates,
    flag1: str,
    jj: int,
) -> pd.DataFrame:
    """
    Detects temporal gaps between chunks of CO-OPS Water Level data and inserts missing timestamps so the final dataset is continuous

    Parameters
    ----------
    data : pd.DataFrame
        Existing concatenated data with columns ['DateTime', 'WaterLevel'].
    stDates, endDates :
        For non-monthly:
            - list of list of strings, e.g. stDates[jj][kk] == 'yyyymmdd HH:MM'
        For monthly:
            - list/array of strings, e.g. stDates[jj] == 'yyyyMMdd HH:mm'
    flag1 : str
        '6', '6p', '1', 'hilo', or 'm'.
    jj : int
        0-based index of the current outer loop (segment).

    Returns
    -------
    pd.DataFrame
        `data` with any gap rows (NaN WaterLevel) appended.
    """
    # MATLAB: if jj > 1  --> Python: if jj > 0 (0-based)
    if jj <= 0:
        return data

    # --------------------------------------------------------------
    # 1) Determine upper and lower bounds (uBound, lBound)
    # --------------------------------------------------------------
    if flag1 != "m":
        # Non-monthly: use last endDate of previous segment and
        # first startDate of current segment.
        #
        # MATLAB:
        #   uBound = datenum(endDates{jj-1}(end,:),'yyyymmdd HH:MM');
        #   lBound = datenum(stDates{jj}(1,:),'yyyymmdd HH:MM');
        #
        # Python: assume nested lists of strings.
        u_str = endDates[jj - 1][-1]  # last string from previous segment
        l_str = stDates[jj][0]  # first string from current segment

        u_bound = pd.to_datetime(u_str, format="%Y%m%d %H:%M")
        l_bound = pd.to_datetime(l_str, format="%Y%m%d %H:%M")

    else:
        # Monthly: use last timestamp already in data and
        # first startDate of this segment.
        #
        # MATLAB:
        #   uBound = data.DateTime(end);
        #   lBound = datetime(stDates(jj,:),
        #                     'InputFormat','yyyyMMdd HH:mm',...);
        if data.empty:
            # Nothing to fill against
            return data

        u_bound = data["DateTime"].iloc[-1]

        l_str = stDates[jj]  # e.g. 'yyyyMMdd HH:mm'
        # If you know you only have 'yyyyMMdd', adjust format accordingly
        try:
            l_bound = pd.to_datetime(l_str, format="%Y%m%d %H:%M")
        except ValueError:
            # fallback: only date, no time
            l_bound = pd.to_datetime(l_str, format="%Y%m%d")

    # If no gap (or negative gap), skip
    if l_bound <= u_bound:
        return data

    # --------------------------------------------------------------
    # 2) Build a DateTime vector from uBound to lBound with the
    #    appropriate time step, drop the first element (uBound),
    #    and create NaN WaterLevel.
    # --------------------------------------------------------------
    if flag1 in ("1", "hilo"):
        # Hourly
        # MATLAB:
        #   dt = datenum(0,0,0,1,0,0);
        #   DateTime = datetime(datestr([uBound:dt:lBound]'), ...);
        freq = "1H"
        dt_range = pd.date_range(start=u_bound, end=l_bound, freq=freq)
        datetimes = dt_range[1:]  # eliminate uBound
    elif flag1 in ("6", "6p"):
        # 6-minute
        # MATLAB:
        #   dt = datenum(0,0,0,0,6,0);
        freq = "6min"
        dt_range = pd.date_range(start=u_bound, end=l_bound, freq=freq)
        datetimes = dt_range[1:]  # eliminate uBound
    elif flag1 == "m":
        # Monthly
        # MATLAB:
        #   dt = calmonths(1);
        #   DateTime = [uBound:dt:lBound]';
        #   DateTime = DateTime(2:end);
        #
        # Here we assume u_bound and l_bound are aligned with month starts.
        # If they’re not, you may want to normalize them.
        dt_range = pd.date_range(start=u_bound, end=l_bound, freq="MS")
        datetimes = dt_range[1:]  # eliminate uBound
    else:
        # Unknown flag, just return data unchanged
        return data

    if len(datetimes) == 0:
        return data

    water_level = np.full(shape=len(datetimes), fill_value=np.nan)

    gap_df = pd.DataFrame({"DateTime": datetimes, "WaterLevel": water_level})

    # Concatenate NaN gap rows to existing data
    data = pd.concat([data, gap_df], ignore_index=True)

    return data

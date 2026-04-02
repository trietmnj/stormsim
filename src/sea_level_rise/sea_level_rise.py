from datetime import date
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt 

def generate_slr_curves(alpha, beta_values, y1, y2):
    """
    Generates multiple sea level rise curves for different beta values.

    Args:
        alpha (float): The linear rate of sea level rise (mm/year).
        beta_values (list or np.array): A list of beta values (acceleration in mm/year²).
        y1 (int): The start year for the projection.
        y2 (int): The end year for the projection.

    Returns:
        pd.DataFrame: A DataFrame with columns 'year', 'scenario1', 'scenario2', etc.,
                      showing the cumulative sea level rise in mm.
    """
    # 1. Create the array of years for the x-axis
    years = np.arange(y1, y2 + 1)

    # 2. Calculate time variables based on the 1992 reference date
    july1992 = date(1992, 7, 1)
    start_date = date(y1, 7, 1)

    # Time from 1992 to the start of our projection (a scalar)
    t1 = (start_date - july1992).days / 365.25

    # An array of time values, one for each year in our projection
    t_array = np.array([(date(y, 7, 1) - july1992).days / 365.25 for y in years])

    # 3. Initialize a dictionary to build the DataFrame
    # The first column is the year
    curves_data = {'year': years}

    # 4. Loop through each beta value to generate a scenario curve
    for i, beta in enumerate(beta_values):
        # The equation now uses the array of time values (t_array)
        # This calculates the cumulative rise from y1 to each year in the t_array
        p_curve = alpha * (t_array - t1) + beta * (t_array**2 - t1**2)

        # Add the resulting curve to our dictionary
        curves_data[f'scenario{i+1}'] = p_curve

    # 5. Convert the dictionary to a DataFrame and return it
    df_curves = pd.DataFrame(curves_data)
    return df_curves

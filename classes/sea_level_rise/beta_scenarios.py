import pandas as pd
import numpy as np

def print_beta_table(proj_source=None):
    """
    Prints the sea level rise beta table based on the requested projection source.
    Drops NaN rows only for specific projection requests.
    
    Args:
        proj_source (str, optional): 'usace_2019', 'noaa_2012', or 'carswg_2016'. 
                                     If None or empty (e.g., []), prints the entire table.
    """
    data = {
        'Global sea level rise (1992 to 2100, m)': [0.2, 0.5, 1.0, 1.2, 1.5, 2.0],
        'β value (mm/year²)': [0, 0.0271, 0.0700, 0.0871, 0.113, 0.156],
        'USACE 2019': ['Low', 'Intermediate', np.nan, np.nan, 'High', np.nan],
        'NOAA et al. 2012': ['Lowest', 'Intermediate-Low', np.nan, 'Intermediate-High', np.nan, 'Highest'],
        'CARSWG 2016': ['Lowest', 'Low', 'Medium', np.nan, 'High', 'Highest']
    }

    df = pd.DataFrame(data)

    # Base columns that should always be displayed
    base_cols = ['Global sea level rise (1992 to 2100, m)', 'β value (mm/year²)']

    # Map the input strings to the actual DataFrame column names
    source_map = {
        'usace_2019': 'USACE 2019',
        'noaa_2012': 'NOAA et al. 2012',
        'carswg_2016': 'CARSWG 2016'
    }

    # If no source is provided (evaluates to False for None, [], "", etc.), print everything
    if not proj_source:
        print("--- All Projection Sources ---")
        print(df)
        return df
    
    # Force the input to lowercase to avoid capitalization errors
    proj_source = proj_source.lower()

    # Check if the requested source is valid
    if proj_source in source_map:
        target_col = source_map[proj_source]
        
        # Filter columns AND drop rows where the target column is NaN
        filtered_df = df[base_cols + [target_col]].dropna(subset=[target_col])
        
        print(f"--- Projection Source: {target_col} ---")
        print(filtered_df)
        return filtered_df
        
    else:
        print(f"Error: '{proj_source}' is not a valid projection source.")
        print(f"Valid options are: {list(source_map.keys())} or leave empty.")
        return None
# Import Packages 
from datetime import datetime 

# Define Methods
def filter_tide_data(data_dict:dict, st_date:datetime, end_date:datetime):
    
    # If input is already datetime, just ensure it starts at midnight
    start_dt = st_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # If input is already datetime, force it to end of day
    end_dt = end_date.replace(hour=23, minute=59, second=59)

    out_time = []
    out_tide = []

    # --- BLOCK 3: Filter Loop ---
    for t_val, y_val in zip(data_dict['time'], data_dict['value']):
        
        # Check if t_val in the dictionary is a string or datetime
        current_dt = t_val
            
        if start_dt <= current_dt <= end_dt:
            out_time.append(t_val)
            out_tide.append(y_val)

    return out_time, out_tide
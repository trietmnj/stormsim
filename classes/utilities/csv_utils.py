# Import Packages
from collections.abc import Iterable
import csv

# Define Methods 
# ---------------------------------------------------------
# Utility: Split DF into storm segments
# ---------------------------------------------------------
def split_df_on_zero(df, col):
    zero_idx = df.index[df[col] == 0].tolist()
    boundaries = zero_idx + [len(df)]
    return [df.iloc[zero_idx[i]:boundaries[i+1]] for i in range(len(zero_idx))]
# ---------------------------------------------------------
# Utility: Write storm LCs to multiple CSV file
# ---------------------------------------------------------
def write_dict_to_csv(data_dict:dict, filename:str):
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
# ---------------------------------------------------------
# Utility: Write storm LCs to single CSV file
# ---------------------------------------------------------                   
def write_dicts_to_csv(dicts, filename:str):
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
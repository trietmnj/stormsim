import os
from datetime import datetime
import warnings

# ---------------------------------------------------------
# Utility: Split DF into storm segments
# ---------------------------------------------------------
def split_df_on_zero(df, col):
    zero_idx = df.index[df[col] == 0].tolist()
    boundaries = zero_idx + [len(df)]
    return [df.iloc[zero_idx[i]:boundaries[i+1]] for i in range(len(zero_idx))]


# ---------------------------------------------------------
# Resolve input path (single file vs directory)
# ---------------------------------------------------------
def resolve_input_paths(config):
    lc_path = config["lc_data"]

    if os.path.isfile(lc_path):
        config["single_file"] = True
        return [lc_path], config["outpath"]

    if os.path.isdir(lc_path):
        config["single_file"] = False
        subfol = os.path.basename(lc_path)
        outfol = os.path.join(config["outpath"], subfol)

        files = [
            os.path.join(lc_path, f)
            for f in os.listdir(lc_path)
            if f.lower().endswith(".csv")
        ]
        return files, outfol

    raise FileNotFoundError(f"Invalid lc_data path: {lc_path}")



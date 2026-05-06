import os
import re
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

def sanitize_header(name: str) -> str:
    """Sanitizes a string for use as a parquet column header."""
    # Replace spaces and special characters with underscores, remove leading/trailing non-alphanumeric
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return sanitized.strip("_")

def aggregate_q(transect_sim_path: str):
    """
    Aggregates overtopping rates (q) across multiple transects for each reach and lifecycle.
    Includes individual transect columns and a total sum.
    
    Args:
        transect_sim_path: Base directory containing transect subfolders.
    """
    base_path = Path(transect_sim_path)
    if not base_path.is_dir():
        print(f"Error: {transect_sim_path} is not a directory.")
        return

    # Dictionary to store data for aggregation: (reach_id, lc_id) -> List[(transect_name, dataframe)]
    aggregation_map: Dict[Tuple[int, int], List[Tuple[str, pd.DataFrame]]] = {}

    print(f"Scanning directory: {transect_sim_path}")

    # Scan for subfolders (transects)
    subfolders = [d for d in base_path.iterdir() if d.is_dir()]
    print(f"Found {len(subfolders)} subfolders.")

    for transect_dir in subfolders:
        transect_name = transect_dir.name
        # Scan for parquet files in each transect folder
        for file_path in transect_dir.glob("*.parquet"):
            filename = file_path.name
            
            # Identify "responses_loc_X_lc_Y.parquet" files, excluding "stage_"
            if filename.startswith("stage_"):
                continue
            
            match = re.search(r"loc_(\d+)_lc_(\d+)", filename)
            if not match:
                continue
            
            reach_id = int(match.group(1))
            lc_id = int(match.group(2))
            key = (reach_id, lc_id)
            
            try:
                df = pd.read_parquet(file_path)
                
                if "overtopping_rate" not in df.columns:
                    continue

                if key not in aggregation_map:
                    aggregation_map[key] = []
                aggregation_map[key].append((transect_name, df))
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")

    if not aggregation_map:
        print("No matching response files found for aggregation.")
        return

    # Create output directory
    output_dir = base_path / "aggregate_responses"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Aggregating data for {len(aggregation_map)} unique (reach, lc) pairs...")

    for (reach_id, lc_id), data_list in aggregation_map.items():
        if not data_list:
            continue
        
        # We'll use the first dataframe's metadata columns as the base
        # But we'll remove response-specific columns to rebuild them
        first_transect_name, first_df = data_list[0]
        
        # Columns to keep as metadata (not to be summed or duplicated)
        metadata_cols = [c for c in first_df.columns if c not in ["overtopping_rate", "runup", "overtopping_volume", "stage"]]
        out_df = first_df[metadata_cols].copy()
        
        q_cols = []
        for transect_name, df in data_list:
            if len(df) != len(out_df):
                print(f"Warning: Row count mismatch for {transect_name} at reach {reach_id}, LC {lc_id}. Skipping.")
                continue
            
            col_header = f"q_{sanitize_header(transect_name)}"
            out_df[col_header] = df["overtopping_rate"].values
            q_cols.append(col_header)
        
        if not q_cols:
            continue

        # Add the total aggregation column
        out_df["q_total"] = out_df[q_cols].sum(axis=1)
        
        # Save the aggregated dataframe
        out_name = f"q_aggregate_loc_{reach_id}_lc_{lc_id}.parquet"
        out_path = output_dir / out_name
        out_df.to_parquet(out_path)
        print(f"  Saved: {out_name} (included {len(q_cols)} transects)")


def main():
    parser = argparse.ArgumentParser(description="Aggregate overtopping rates across transects.")
    parser.add_argument(
        "transect_sim_path", 
        type=str, 
        help="Path to the directory containing transect subfolders."
    )
    
    args = parser.parse_args()
    aggregate_q(args.transect_sim_path)

if __name__ == "__main__":
    main()

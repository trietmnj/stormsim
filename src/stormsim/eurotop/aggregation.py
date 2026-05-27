import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple


def _sanitize_header(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return sanitized.strip("_")


def aggregate_q(transect_sim_path: str) -> None:
    """
    Aggregates overtopping rates (q) across multiple transects for each reach
    and lifecycle. Writes one parquet per (reach, lc) pair to
    <transect_sim_path>/aggregate_responses/.

    Input directory layout:
        <transect_sim_path>/
            <transect_name>/
                responses_loc_<N>_lc_<M>.parquet   # must contain overtopping_rate
                stage_*.parquet                      # ignored
    """
    base_path = Path(transect_sim_path)
    if not base_path.is_dir():
        print(f"Error: {transect_sim_path} is not a directory.")
        return

    aggregation_map: Dict[Tuple[int, int], List[Tuple[str, pd.DataFrame]]] = {}

    print(f"Scanning directory: {transect_sim_path}")
    subfolders = [d for d in base_path.iterdir() if d.is_dir()]
    print(f"Found {len(subfolders)} subfolders.")

    for transect_dir in subfolders:
        transect_name = transect_dir.name
        for file_path in transect_dir.glob("*.parquet"):
            if file_path.name.startswith("stage_"):
                continue
            match = re.search(r"loc_(\d+)_lc_(\d+)", file_path.name)
            if not match:
                continue
            key = (int(match.group(1)), int(match.group(2)))
            try:
                df = pd.read_parquet(file_path)
                if "overtopping_rate" not in df.columns:
                    continue
                aggregation_map.setdefault(key, []).append((transect_name, df))
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")

    if not aggregation_map:
        print("No matching response files found for aggregation.")
        return

    output_dir = base_path / "aggregate_responses"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Aggregating data for {len(aggregation_map)} unique (reach, lc) pairs...")

    _response_cols = {"overtopping_rate", "runup", "overtopping_volume", "stage"}

    for (reach_id, lc_id), data_list in aggregation_map.items():
        _, first_df = data_list[0]
        metadata_cols = [c for c in first_df.columns if c not in _response_cols]
        out_df = first_df[metadata_cols].copy()

        q_cols = []
        for transect_name, df in data_list:
            if len(df) != len(out_df):
                print(
                    f"Warning: Row count mismatch for {transect_name} "
                    f"at reach {reach_id}, LC {lc_id}. Skipping."
                )
                continue
            col = f"q_{_sanitize_header(transect_name)}"
            out_df[col] = df["overtopping_rate"].values
            q_cols.append(col)

        if not q_cols:
            continue

        out_df["q_total"] = out_df[q_cols].sum(axis=1)
        out_name = f"q_aggregate_loc_{reach_id}_lc_{lc_id}.parquet"
        out_df.to_parquet(output_dir / out_name)
        print(f"  Saved: {out_name} (included {len(q_cols)} transects)")

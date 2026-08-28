from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _join_storage_path(base: str, child: str) -> str:
    """Join a local path or S3 URI without corrupting the URI scheme."""
    if base.startswith("s3://"):
        return f"{base.rstrip('/')}/{child.lstrip('/')}"
    return str(Path(base) / child)


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
    if transect_sim_path.startswith("s3://"):
        _aggregate_q_s3(transect_sim_path)
        return

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


def _aggregate_q_s3(transect_sim_path: str) -> None:
    """Aggregate transect response parquet files stored under an S3 prefix."""
    from urllib.parse import urlparse

    import boto3

    parsed = urlparse(transect_sim_path)
    prefix = parsed.path.lstrip("/").rstrip("/") + "/"
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    aggregation_map: Dict[Tuple[int, int], List[Tuple[str, pd.DataFrame]]] = {}

    for page in paginator.paginate(Bucket=parsed.netloc, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            relative_key = key[len(prefix):]
            parts = relative_key.split("/", 1)
            if len(parts) != 2 or parts[0] == "aggregate_responses":
                continue
            filename = parts[1]
            if not filename.endswith(".parquet") or filename.startswith("stage_"):
                continue

            match = re.search(r"loc_(\d+)_lc_(\d+)", filename)
            if not match:
                continue

            file_path = f"s3://{parsed.netloc}/{key}"
            try:
                df = pd.read_parquet(file_path)
                if "overtopping_rate" not in df.columns:
                    continue
                key_pair = (int(match.group(1)), int(match.group(2)))
                aggregation_map.setdefault(key_pair, []).append((parts[0], df))
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")

    if not aggregation_map:
        print("No matching response files found for aggregation.")
        return

    output_prefix = _join_storage_path(transect_sim_path, "aggregate_responses")
    print(f"Aggregating data for {len(aggregation_map)} unique (reach, lc) pairs...")
    response_cols = {"overtopping_rate", "runup", "overtopping_volume", "stage"}

    for (reach_id, lc_id), data_list in aggregation_map.items():
        _, first_df = data_list[0]
        metadata_cols = [c for c in first_df.columns if c not in response_cols]
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
        out_df.to_parquet(_join_storage_path(output_prefix, out_name), index=False)
        print(f"  Saved: {out_name} (included {len(q_cols)} transects)")


def run_aggregate_q(
    config: Dict[str, Any],
    is_lambda: bool = False,
    storage_context: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Standard entry point for overtopping aggregation.

    Config keys:
      inputs.transect_sim_path — directory containing per-transect eurotop output subfolders

    Output is written to <transect_sim_path>/aggregate_responses/.
    """
    from ..utilities.storage import StorageContext

    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)
    transect_sim_path = ctx.get_input_path("transect_sim_path")
    aggregate_q(transect_sim_path)
    output_dir = _join_storage_path(transect_sim_path, "aggregate_responses")
    return {"status": "success", "output": output_dir}

import pandas as pd
import numpy as np
import duckdb
from typing import Optional, Dict

def _get_duckdb_con(s3_config: Optional[Dict] = None):
    con = duckdb.connect(database=':memory:')
    if s3_config and s3_config.get("use_s3", False):
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_endpoint='{s3_config['s3_endpoint'].replace('http://', '').replace('https://', '')}';")
        con.execute(f"SET s3_access_key_id='{s3_config['s3_access_key']}';")
        con.execute(f"SET s3_secret_access_key='{s3_config['s3_secret_key']}';")
        con.execute("SET s3_use_ssl='false';") if "http://" in s3_config['s3_endpoint'] else None
        con.execute("SET s3_url_style='path';")
    return con

def load_relative_probabilities(filepath: str, use_duckdb: bool = False, s3_config: Optional[Dict] = None):
    """
    Load daily cumulative storm probabilities by (Month, Day).
    """
    if use_duckdb:
        con = _get_duckdb_con(s3_config)
        query = f"""
            SELECT 
                Month as month, 
                Day as day, 
                "Cumulative trop prob" as trop_day_cdf 
            FROM read_csv_auto('{filepath}')
        """
        df = con.query(query).to_df()
    else:
        storage_options = {}
        if s3_config:
            if s3_config.get("s3_access_key"):
                storage_options["key"] = s3_config["s3_access_key"]
            if s3_config.get("s3_secret_key"):
                storage_options["secret"] = s3_config["s3_secret_key"]
            if s3_config.get("s3_endpoint"):
                storage_options["client_kwargs"] = {"endpoint_url": s3_config["s3_endpoint"]}
        
        df = pd.read_csv(
            filepath,
            usecols=["Month", "Day", "Cumulative trop prob"],
            dtype={"Month": int, "Day": int, "Cumulative trop prob": float},
            storage_options=storage_options if storage_options else None
        ).rename(
            columns={
                "Month": "month",
                "Day": "day",
                "Cumulative trop prob": "trop_day_cdf",
            }
        )
    
    # Common post-processing
    df["day_of_year"] = pd.to_datetime(
        df[["month", "day"]].assign(Year=2025), errors="coerce"
    ).dt.dayofyear
    return df


def load_storm_id_cdf(filepath: str, use_duckdb: bool = False, s3_config: Optional[Dict] = None):
    """
    Load storm IDs and their probabilities from CHS master track.
    """
    if use_duckdb:
        con = _get_duckdb_con(s3_config)
        query = f"""
            SELECT 
                stormID as storm_id, 
                DSW as dsw 
            FROM read_csv_auto('{filepath}')
            ORDER BY DSW
        """
        df = con.query(query).to_df()
    else:
        storage_options = {}
        if s3_config:
            if s3_config.get("s3_access_key"):
                storage_options["key"] = s3_config["s3_access_key"]
            if s3_config.get("s3_secret_key"):
                storage_options["secret"] = s3_config["s3_secret_key"]
            if s3_config.get("s3_endpoint"):
                storage_options["client_kwargs"] = {"endpoint_url": s3_config["s3_endpoint"]}
        
        df = pd.read_csv(
            filepath, 
            usecols=["stormID", "DSW"], 
            dtype={"stormID": int, "DSW": float},
            storage_options=storage_options if storage_options else None
        ).rename(
            columns={
                "stormID": "storm_id",
                "DSW": "dsw",
            }
        )
        df = df.sort_values(by="dsw").reset_index(drop=True)

    total_weight = df["dsw"].sum()
    df["prob"] = df["dsw"] / total_weight
    df["cdf"] = np.cumsum(df["prob"])
    return df

import numpy as np
import pandas as pd
from stormsim.hazard_curves.pst.cleaner import clean_pot_data


def test_data_cleaning_with_reference_data():
    # Load raw and cleaned datasets from Parquet
    raw_df = pd.read_parquet("data/hazard_curves/pst/01_pst_input_raw.parquet")
    target_df = pd.read_parquet("data/hazard_curves/pst/02_pst_input_cleaned.parquet")

    # We need to process raw_df using clean_pot_data
    # Based on the structure in the matlab ref, the raw data is passed as a (N, 3) matrix.
    data = raw_df.values
    cleaned = clean_pot_data(data, flag_value=[])

    # Validate against target cleaned data (ignoring index for comparison)
    assert np.allclose(cleaned, target_df.values, atol=1e-6)

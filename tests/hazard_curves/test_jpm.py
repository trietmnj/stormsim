import pytest
from stormsim.hazard_curves.jpm import run_jpm


def test_run_jpm_writes_outputs(hazard_curves_input, test_output_dir):
    config = {
        "inputs": {
            "data_file": str(hazard_curves_input / "jpm_input.parquet"),
        },
        "outputs": {
            "local_directory": str(test_output_dir.parent),
            "filename": test_output_dir.name,
        },
        "jpm_params": {},
        "jpm_options": {
            "flag_value": [],
            "ua": 0.3738,
            "ur": 0.5840,
            "integration_mode": "ITCS",
            "uncertainty_mode": "combined",
            "tide_mode": "none",
            "percentiles": [16, 84],
            "use_aep": False,
            "return_table": True,
        },
    }
    result = run_jpm(config)
    assert result["status"] == "success"
    out_dir = test_output_dir
    assert (out_dir / "hc_plot.parquet").exists()
    assert (out_dir / "hc_table.parquet").exists()

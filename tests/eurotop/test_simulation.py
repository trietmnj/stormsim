import json

from stormsim.eurotop import simulation


class _StorageContext:
    def __init__(self, paths):
        self.paths = paths

    def get_input_path(self, key):
        return self.paths[key]

    def get_output_path(self):
        return self.paths["output"]


def _config(tmp_path):
    lc_data = tmp_path / "lifecycles"
    lc_data.mkdir()
    pse_geometry = tmp_path / "geometry.json"
    pse_geometry.write_text(json.dumps([]))
    stage_volume = tmp_path / "stage_volume.csv"
    stage_volume.write_text("stage,volume\n0,0\n")

    return {
        "lc_data": str(lc_data),
        "pse_geometry": str(pse_geometry),
        "stage_vol_file": str(stage_volume),
        "output": str(tmp_path / "output"),
    }


def test_run_eurotop_reports_aggregation_failure_as_partial_success(tmp_path, monkeypatch):
    paths = _config(tmp_path)
    monkeypatch.setattr(simulation, "StorageContext", lambda *_args, **_kwargs: _StorageContext(paths))

    def fail_aggregation(_outpath):
        raise OSError("S3 write denied")

    monkeypatch.setattr(simulation, "aggregate_q", fail_aggregation)

    result = simulation.run_eurotop({})

    assert result == {
        "status": "success",
        "output": paths["output"],
        "aggregated": 0,
        "aggregation_error": "S3 write denied",
    }


def test_run_eurotop_reports_aggregation_results(tmp_path, monkeypatch):
    paths = _config(tmp_path)
    monkeypatch.setattr(simulation, "StorageContext", lambda *_args, **_kwargs: _StorageContext(paths))
    monkeypatch.setattr(
        simulation,
        "aggregate_q",
        lambda _outpath: {
            "pairs_written": 2,
            "output_paths": ["aggregate_responses/q_aggregate_loc_1_lc_2.parquet"],
        },
    )

    result = simulation.run_eurotop({})

    assert result == {
        "status": "success",
        "output": paths["output"],
        "aggregated": 2,
        "pairs_written": 2,
        "output_paths": ["aggregate_responses/q_aggregate_loc_1_lc_2.parquet"],
    }

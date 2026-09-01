import pandas as pd
import pytest

from stormsim.eurotop import aggregation
from stormsim.eurotop.aggregation import AggregationError, aggregate_q


def _write_response(transect_dir, filename, overtopping_rates):
    pd.DataFrame(
        {
            "location_id": 1,
            "lifecycle": 1,
            "date": ["2025-01-01"] * len(overtopping_rates),
            "overtopping_rate": overtopping_rates,
        }
    ).to_parquet(transect_dir / filename, index=False)


def test_aggregate_q_sums_transect_overtopping_rates(tmp_path):
    transect_one = tmp_path / "transect-one"
    transect_two = tmp_path / "transect-two"
    transect_one.mkdir()
    transect_two.mkdir()
    filename = "lifecycle_responses_loc_1_lc_1.parquet"
    _write_response(transect_one, filename, [0.1, 0.2])
    _write_response(transect_two, filename, [0.3, 0.4])
    _write_response(transect_one, f"stage_{filename}", [99.0, 99.0])

    result = aggregate_q(str(tmp_path))

    output_path = tmp_path / "aggregate_responses" / "q_aggregate_loc_1_lc_1.parquet"
    assert result == {"pairs_written": 1, "output_paths": [str(output_path)]}
    assert output_path.is_file()

    output = pd.read_parquet(output_path)
    assert output["q_transect_one"].tolist() == [0.1, 0.2]
    assert output["q_transect_two"].tolist() == [0.3, 0.4]
    pd.testing.assert_series_equal(
        output["q_total"],
        output["q_transect_one"] + output["q_transect_two"],
        check_names=False,
    )


def test_aggregate_q_raises_on_mismatched_row_counts(tmp_path):
    transect_one = tmp_path / "transect-one"
    transect_two = tmp_path / "transect-two"
    transect_one.mkdir()
    transect_two.mkdir()
    filename = "lifecycle_responses_loc_1_lc_1.parquet"
    _write_response(transect_one, filename, [0.1, 0.2])
    _write_response(transect_two, filename, [0.3])

    with pytest.raises(AggregationError, match="Row count mismatch"):
        aggregate_q(str(tmp_path))

    assert list((tmp_path / "aggregate_responses").glob("*.parquet")) == []


class _FakePaginator:
    def __init__(self, keys):
        self._keys = keys

    def paginate(self, Bucket, Prefix):
        yield {"Contents": [{"Key": k} for k in self._keys]}


class _FakeS3Client:
    def __init__(self, keys):
        self._keys = keys

    def get_paginator(self, name):
        return _FakePaginator(self._keys)


def test_aggregate_q_s3_ignores_nested_keys(monkeypatch):
    """A nested copy under a transect prefix must not double-count q_total."""
    prefix = "runs/outputs"
    filename = "lifecycle_responses_loc_1_lc_1.parquet"
    keys = [
        f"{prefix}/transect-one/{filename}",
        f"{prefix}/transect-one/archive/{filename}",  # nested duplicate
        f"{prefix}/transect-one/sub/stage_{filename}",  # nested stage file
        f"{prefix}/transect-two/{filename}",
    ]

    frames = {
        f"s3://bucket/{prefix}/transect-one/{filename}": pd.DataFrame(
            {"location_id": 1, "overtopping_rate": [0.1, 0.2]}
        ),
        f"s3://bucket/{prefix}/transect-one/archive/{filename}": pd.DataFrame(
            {"location_id": 1, "overtopping_rate": [10.0, 20.0]}
        ),
        f"s3://bucket/{prefix}/transect-two/{filename}": pd.DataFrame(
            {"location_id": 1, "overtopping_rate": [0.3, 0.4]}
        ),
    }

    import boto3

    monkeypatch.setattr(boto3, "client", lambda name: _FakeS3Client(keys))
    monkeypatch.setattr(aggregation.pd, "read_parquet", lambda path: frames[path])
    written = {}
    monkeypatch.setattr(
        aggregation.pd.DataFrame,
        "to_parquet",
        lambda self, path, **kwargs: written.update({path: self.copy()}),
    )

    result = aggregate_q(f"s3://bucket/{prefix}")

    assert result["pairs_written"] == 1
    (out_df,) = written.values()
    assert out_df["q_transect_one"].tolist() == [0.1, 0.2]
    assert out_df["q_transect_two"].tolist() == [0.3, 0.4]
    assert out_df["q_total"].tolist() == [0.1 + 0.3, 0.2 + 0.4]

import pandas as pd

from stormsim.eurotop.aggregation import aggregate_q


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


def test_aggregate_q_skips_transects_with_mismatched_row_counts(tmp_path):
    transect_one = tmp_path / "transect-one"
    transect_two = tmp_path / "transect-two"
    transect_one.mkdir()
    transect_two.mkdir()
    filename = "lifecycle_responses_loc_1_lc_1.parquet"
    _write_response(transect_one, filename, [0.1, 0.2])
    _write_response(transect_two, filename, [0.3])

    aggregate_q(str(tmp_path))

    output = pd.read_parquet(
        tmp_path / "aggregate_responses" / "q_aggregate_loc_1_lc_1.parquet"
    )
    assert output["q_transect_one"].tolist() == [0.1, 0.2]
    assert "q_transect_two" not in output
    assert output["q_total"].tolist() == [0.1, 0.2]

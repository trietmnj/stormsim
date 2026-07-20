"""
Config/input resolution for the hydrograph manipulator.

Covers the failure modes that previously passed silently:
  - S3 tide_config read as a local file -> {} -> SLR/tides skipped, no error
  - CHART h5 naming not matching the sniffed CHS convention
  - an unrecognized SLR scenario name falling through to scenario1
"""
import json
from pathlib import Path

import fsspec
import pytest

from stormsim.hydrograph_manipulator.HydroManipulator import HydroManipulator
from stormsim.hydrograph_manipulator.simulation import (
    resolve_tides_config,
    run_hydro_manipulator,
    select_h5_files,
)

CHS_NAMES = [
    "CHS-NA_TS_SimB1RT_Post0_SP0064_STWAVE04_Timeseries.h5",
    "CHS-NA_TS_SimB1RT_Post0_SP00133_ADCIRC01_Timeseries.h5",
]
CHART_NAMES = ["wave_64.h5", "water-level_64.h5"]


def _h5_dir(tmp_path, names):
    for n in names:
        (tmp_path / n).touch()
    return str(tmp_path)


def test_sniffs_chs_naming(tmp_path):
    adcirc, wave = select_h5_files(_h5_dir(tmp_path, CHS_NAMES), {})
    assert "ADCIRC" in adcirc and "STWAVE" in wave


def test_chart_naming_fails_loudly_when_sniffing(tmp_path):
    with pytest.raises(FileNotFoundError):
        select_h5_files(_h5_dir(tmp_path, CHART_NAMES), {})


def test_explicit_filenames_bypass_sniffing(tmp_path):
    inputs = {"adcirc_file": "water-level_64.h5", "wave_file": "wave_64.h5"}
    adcirc, wave = select_h5_files(_h5_dir(tmp_path, CHART_NAMES), inputs)
    assert (adcirc, wave) == ("water-level_64.h5", "wave_64.h5")


def test_explicit_filenames_skip_listing_entirely():
    # no such directory -- proves we never listed it
    inputs = {"adcirc_file": "a.h5", "wave_file": "w.h5"}
    assert select_h5_files("s3://does-not-exist/nope/", inputs) == ("a.h5", "w.h5")


def _cfg(tmp_path, **inputs):
    return {
        "inputs": {"lc_path": str(tmp_path / "missing_lc.csv"), **inputs},
        "outputs": {"local_directory": str(tmp_path), "filename": "o.parquet"},
        "add_slr": True,
        "slr_projection": "usace_2019",
        "slr_projection_scenario": "low",
    }


def test_add_slr_without_tide_config_raises(tmp_path):
    with pytest.raises(ValueError, match="station"):
        run_hydro_manipulator(_cfg(tmp_path))


GAUGE = [{"station": "8557380", "datum": "MSL", "interval": "1"}]


def test_local_tide_config_resolves(tmp_path):
    tc = tmp_path / "tidal_gauge.json"
    tc.write_text(json.dumps(GAUGE))
    # station resolves -> passes the guard -> fails later on the absent lc_path
    with pytest.raises(FileNotFoundError):
        run_hydro_manipulator(_cfg(tmp_path, tide_config=str(tc)))


def test_remote_tide_config_resolves(tmp_path):
    """
    The regression that mattered: a non-local URI. os.path.exists() returns
    False for these, so the old plain-open() path yielded {} and silently
    disabled SLR. memory:// stands in for s3:// -- same fsspec code path,
    no network.
    """
    with fsspec.open("memory://tidal_gauge.json", "w") as f:
        json.dump(GAUGE, f)
    with pytest.raises(FileNotFoundError):
        run_hydro_manipulator(_cfg(tmp_path, tide_config="memory://tidal_gauge.json"))


def test_inline_tide_station_needs_no_file(tmp_path):
    # station resolves from inputs alone -> past the guard -> absent lc_path
    with pytest.raises(FileNotFoundError):
        run_hydro_manipulator(_cfg(tmp_path, tide_station="8557380"))


def test_inline_tide_station_accepts_numeric(tmp_path):
    # chart_feat.noaa_station.stationid is numeric, so json may carry an int
    with pytest.raises(FileNotFoundError):
        run_hydro_manipulator(_cfg(tmp_path, tide_station=8557380))


def test_inline_station_defaults_match_shipped_config():
    """
    get_tidal_prediction defaults interval to 'h' (hourly), but the shipped
    tidal_gauge.json uses '1' (1-minute). Inline must not silently coarsen.
    """
    shipped = json.loads(
        (Path(__file__).parents[2] / "config-files" / "tidal_gauge.json").read_text()
    )[0]
    cfg = resolve_tides_config("", {"tide_station": "8557380"})
    assert cfg["interval"] == shipped["interval"]
    assert cfg["datum"] == shipped["datum"]


def test_inline_station_overrides_file_but_keeps_its_other_values(tmp_path):
    tc = tmp_path / "tidal_gauge.json"
    tc.write_text(json.dumps([{"station": "1111111", "datum": "NAVD", "interval": "6"}]))
    cfg = resolve_tides_config(str(tc), {"tide_station": "8557380"})
    assert cfg == {"station": "8557380", "datum": "NAVD", "interval": "6"}


def test_file_alone_is_passed_through_verbatim(tmp_path):
    tc = tmp_path / "tidal_gauge.json"
    tc.write_text(json.dumps(GAUGE))
    assert resolve_tides_config(str(tc), {}) == GAUGE[0]


def test_no_station_anywhere_yields_empty():
    assert resolve_tides_config("", {}) == {}


@pytest.mark.parametrize("scenario", ["low", "intermediate", "high"])
def test_valid_usace_scenarios_resolve(scenario):
    _, df = HydroManipulator().get_slr_projections("usace_2019", scenario, 0.002, 2000, 2010)
    assert list(df.columns) == ["year", scenario]


@pytest.mark.parametrize("scenario", ["low_usace", "intermediate-low", "LOW", None])
def test_unknown_scenario_raises_instead_of_defaulting(scenario):
    with pytest.raises(ValueError, match="not valid for"):
        HydroManipulator().get_slr_projections("usace_2019", scenario, 0.002, 2000, 2010)

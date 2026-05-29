from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from stormsim.stage_volume import StageVolumeCalculator, StageVolumeConfig, run_stage_volume


# ---------------------------------------------------------------------------
# Shared fixture: 10×10 DEM, 1 m² cells, elevations 0–9 m, nodata = -9999
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_dem():
    """10×10 DEM with uniform 5 m elevation — simple volume checks."""
    dem = np.full((10, 10), 5.0)
    config = StageVolumeConfig(stage_units="meters", dem_vertical_units="meters")
    return StageVolumeCalculator(dem, nodata=-9999, cell_area_m2=1.0, config=config)


@pytest.fixture
def ramp_dem():
    """10×10 DEM where each row has elevation equal to its row index (0–9 m)."""
    dem = np.tile(np.arange(10, dtype=float), (10, 1))
    config = StageVolumeConfig(stage_units="meters", dem_vertical_units="meters")
    return StageVolumeCalculator(dem, nodata=-9999, cell_area_m2=1.0, config=config)


# ---------------------------------------------------------------------------
# StageVolumeConfig
# ---------------------------------------------------------------------------


def test_config_defaults():
    cfg = StageVolumeConfig()
    assert cfg.stage_units == "feet"
    assert cfg.dem_vertical_units == "meters"


def test_config_rejects_invalid_units():
    with pytest.raises(Exception):
        StageVolumeConfig(stage_units="cubits")
    with pytest.raises(Exception):
        StageVolumeConfig(dem_vertical_units="inches")


# ---------------------------------------------------------------------------
# StageVolumeCalculator — init
# ---------------------------------------------------------------------------


def test_brentq_bounds_derived_from_dem(ramp_dem):
    # DEM valid range 0–9 m; bounds should be just outside that
    assert ramp_dem._brentq_lo < 0.0
    assert ramp_dem._brentq_hi > 9.0


def test_nodata_excluded_from_bounds():
    dem = np.array([[5.0, -9999.0], [5.0, 5.0]])
    config = StageVolumeConfig(stage_units="meters", dem_vertical_units="meters")
    calc = StageVolumeCalculator(dem, nodata=-9999, cell_area_m2=1.0, config=config)
    # bounds must reflect only valid elevations (all 5 m), not the nodata sentinel
    assert calc._brentq_lo == pytest.approx(4.0)   # 5.0 - 1 margin
    assert calc._brentq_hi == pytest.approx(6.0)   # 5.0 + 1 margin


def test_dem_feet_conversion():
    dem = np.full((5, 5), 1.0)  # 1 ft elevation
    config = StageVolumeConfig(stage_units="meters", dem_vertical_units="feet")
    calc = StageVolumeCalculator(dem, nodata=-9999, cell_area_m2=1.0, config=config)
    # Internal DEM should be stored in metres
    assert np.allclose(calc.dem_data[calc.valid_mask], 0.3048)


# ---------------------------------------------------------------------------
# get_relationship — return type
# ---------------------------------------------------------------------------


def test_get_relationship_always_returns_list_n1(ramp_dem):
    result = ramp_dem.get_relationship(5.0)
    assert isinstance(result, list)
    assert len(result) == 1


def test_get_relationship_returns_list_n_gt_1(ramp_dem):
    result = ramp_dem.get_relationship(0.0, 9.0, n=5)
    assert isinstance(result, list)
    assert len(result) == 5


def test_get_relationship_keys(ramp_dem):
    result = ramp_dem.get_relationship(5.0)
    assert set(result[0].keys()) == {"stage", "volume"}


# ---------------------------------------------------------------------------
# get_relationship — stage → volume
# ---------------------------------------------------------------------------


def test_zero_volume_below_terrain(flat_dem):
    # Stage below all terrain → no flooding
    result = flat_dem.get_relationship(4.99)
    assert result[0]["volume"] == pytest.approx(0.0)


def test_volume_above_terrain(flat_dem):
    # Stage 1 m above uniform 5 m DEM: 10×10 cells × 1 m depth × 1 m² = 100 m³
    result = flat_dem.get_relationship(6.0)
    assert result[0]["volume"] == pytest.approx(100.0)


def test_volume_increases_with_stage(ramp_dem):
    result = ramp_dem.get_relationship(0.0, 9.0, n=10)
    volumes = [r["volume"] for r in result]
    assert all(v2 >= v1 for v1, v2 in zip(volumes, volumes[1:]))


def test_vectorised_matches_scalar(ramp_dem):
    stages = np.array([1.0, 4.0, 7.0])
    batch_vols = ramp_dem._calc_vol_batch(stages)
    for s, bv in zip(stages, batch_vols):
        assert bv == pytest.approx(ramp_dem._calc_vol(s), rel=1e-10)


# ---------------------------------------------------------------------------
# get_relationship — volume → stage (brentq roundtrip)
# ---------------------------------------------------------------------------


def test_volume_to_stage_roundtrip(ramp_dem):
    fwd = ramp_dem.get_relationship(5.0)[0]
    inv = ramp_dem.get_relationship(fwd["volume"], volume_to_stage=True)[0]
    assert inv["stage"] == pytest.approx(5.0, abs=1e-8)


def test_volume_to_stage_multiple(ramp_dem):
    fwd = ramp_dem.get_relationship(1.0, 8.0, n=5)
    for r in fwd:
        if r["volume"] == 0.0:
            continue
        inv = ramp_dem.get_relationship(r["volume"], volume_to_stage=True)[0]
        assert inv["stage"] == pytest.approx(r["stage"], abs=1e-6)


# ---------------------------------------------------------------------------
# Stage unit conversion (feet input)
# ---------------------------------------------------------------------------


def test_stage_feet_conversion():
    # 1 ft ≈ 0.3048 m; uniform DEM at 0 m, stage in feet
    dem = np.zeros((10, 10))
    config = StageVolumeConfig(stage_units="feet", dem_vertical_units="meters")
    calc = StageVolumeCalculator(dem, nodata=-9999, cell_area_m2=1.0, config=config)

    result_ft = calc.get_relationship(1.0)[0]["volume"]   # 1 ft stage
    # 0.3048 m depth × 100 cells × 1 m² = 30.48 m³
    assert result_ft == pytest.approx(30.48, rel=1e-6)


# ---------------------------------------------------------------------------
# run_stage_volume — mocked I/O
# ---------------------------------------------------------------------------


def test_run_stage_volume_writes_parquet(tmp_path):
    dem_arr = np.tile(np.arange(10, dtype=np.float32), (10, 1))

    mock_src = MagicMock()
    mock_src.__enter__ = MagicMock(return_value=mock_src)
    mock_src.__exit__ = MagicMock(return_value=False)
    mock_src.nodata = -9999.0
    mock_transform = MagicMock()
    mock_transform.__getitem__ = lambda self, i: {0: 1.0, 4: -1.0}[i]

    with (
        patch("stormsim.stage_volume.processing.gpd.read_file") as mock_gdf,
        patch("stormsim.stage_volume.processing.rasterio.open", return_value=mock_src),
        patch("stormsim.stage_volume.processing.mask", return_value=(dem_arr[None, :, :], mock_transform)),
    ):
        mock_gdf.return_value = MagicMock()

        config = {
            "inputs": {"dem_file": "fake.tif", "model_area_file": "fake.geojson"},
            "outputs": {"local_directory": str(tmp_path), "filename": "sv_out"},
            "stage_volume_params": {
                "stage_units": "meters",
                "dem_vertical_units": "meters",
                "start": 0.0,
                "stop": 9.0,
                "n": 5,
            },
        }
        result = run_stage_volume(config)

    assert result["status"] == "success"
    out = tmp_path / "sv_out" / "stage_volume.parquet"
    assert out.exists()

    import pandas as pd
    df = pd.read_parquet(out)
    assert list(df.columns) == ["stage", "volume"]
    assert len(df) == 5
    assert (df["volume"] >= 0).all()

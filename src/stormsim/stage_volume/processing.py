from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pydantic import BaseModel, Field
from rasterio.mask import mask
from scipy.optimize import brentq

from ..utilities.storage import StorageContext


class StageVolumeConfig(BaseModel):
    stage_units: str = Field(default="feet", pattern="^(feet|meters)$")
    dem_vertical_units: str = Field(default="meters", pattern="^(feet|meters)$")


class StageVolumeCalculator:
    """
    Pure stage-volume compute class. Accepts pre-loaded DEM arrays;
    file I/O is handled by run_stage_volume.
    """

    def __init__(
        self,
        dem_data: np.ndarray,
        nodata: float,
        cell_area_m2: float,
        config: StageVolumeConfig,
    ):
        self.config = config
        self.cell_area_m2 = cell_area_m2
        self.dem_data = dem_data.copy().astype(float)
        self.valid_mask = self.dem_data != nodata

        if config.dem_vertical_units == "feet":
            self.dem_data[self.valid_mask] *= 0.3048

        # Flat array of valid elevations (metres) — avoids broadcasting the full
        # 2D DEM on every call, which matters when nodata coverage is large.
        self._valid_elev = self.dem_data[self.valid_mask]

        # Precomputed unit conversion: stage units → metres
        self._stage_to_m = 0.3048 if config.stage_units == "feet" else 1.0

        # Brentq search bounds in stage units, derived from DEM elevation range.
        # Lower bound sits below the minimum elevation (zero volume); upper bound
        # sits above the maximum (all valid cells flooded).
        to_stage = 1.0 / self._stage_to_m
        self._brentq_lo = float(self._valid_elev.min()) * to_stage - 1.0
        self._brentq_hi = float(self._valid_elev.max()) * to_stage + 1.0

    def _calc_vol(self, stage: float) -> float:
        depth = stage * self._stage_to_m - self._valid_elev
        return float(np.sum(np.clip(depth, 0, None)) * self.cell_area_m2)

    def _calc_vol_batch(self, stages: np.ndarray) -> np.ndarray:
        """Vectorised stage→volume for multiple stages at once."""
        stages_m = np.asarray(stages, dtype=float) * self._stage_to_m
        # (n_stages, N_valid) — works on valid cells only, not the full 2D DEM
        depth = stages_m[:, None] - self._valid_elev[None, :]
        return np.sum(np.clip(depth, 0, None), axis=1) * self.cell_area_m2

    def get_relationship(
        self,
        start: float,
        stop: Optional[float] = None,
        n: int = 1,
        volume_to_stage: bool = False,
    ) -> list[dict]:
        """
        Compute stage-volume pairs over a range.

        Always returns a list of dicts with keys 'stage' and 'volume'.
        """
        if stop is None:
            stop = start

        range_vals = np.linspace(start, stop, n) if n > 1 else np.array([start])

        if not volume_to_stage:
            volumes = self._calc_vol_batch(range_vals)
            return [{"stage": float(s), "volume": float(v)} for s, v in zip(range_vals, volumes)]

        results = []
        for vol in range_vals:
            stage = brentq(lambda s: self._calc_vol(s) - vol, self._brentq_lo, self._brentq_hi)
            results.append({"stage": stage, "volume": float(vol)})
        return results


def run_stage_volume(
    config: dict[str, Any],
    is_lambda: bool = False,
    storage_context: StorageContext | None = None,
) -> dict[str, Any]:
    """
    Standard entry point for stage-volume computation.
    Loads inputs via StorageContext, runs compute, writes output.

    Output files written to the configured output directory:
      stage_volume.parquet — stage/volume pairs; columns: stage, volume

    Config keys under 'stage_volume_params':
      stage_units        — 'feet' or 'meters' (default: 'feet')
      dem_vertical_units — 'feet' or 'meters' (default: 'meters')
      start              — start of stage (or volume) range
      stop               — end of range (defaults to start)
      n                  — number of evenly spaced points (default: 1)
      volume_to_stage    — if True, invert: compute stage from target volume
    """
    ctx = storage_context or StorageContext(config, is_lambda=is_lambda)

    dem_path = ctx.get_input_path("dem_file")
    area_path = ctx.get_input_path("model_area_file")

    model_area_gdf = gpd.read_file(area_path)
    with rasterio.open(dem_path) as src:
        out_image, out_transform = mask(src, model_area_gdf.geometry, crop=True)
        dem_data = out_image[0]
        nodata = src.nodata
        cell_area_m2 = abs(out_transform[0] * out_transform[4])

    sv_params = config.get("stage_volume_params", {})
    sv_config = StageVolumeConfig(
        stage_units=sv_params.get("stage_units", "feet"),
        dem_vertical_units=sv_params.get("dem_vertical_units", "meters"),
    )

    calc = StageVolumeCalculator(dem_data, nodata, cell_area_m2, sv_config)
    results = calc.get_relationship(
        start=sv_params["start"],
        stop=sv_params.get("stop"),
        n=sv_params.get("n", 1),
        volume_to_stage=sv_params.get("volume_to_stage", False),
    )

    out_dir = Path(ctx.get_output_path())
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_parquet(out_dir / "stage_volume.parquet", index=False)

    print(f"Stage-volume outputs written to {out_dir}")
    return {"status": "success", "output": str(out_dir)}

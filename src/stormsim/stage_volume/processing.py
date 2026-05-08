import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from scipy.optimize import brentq
from pydantic import BaseModel, Field
from typing import Optional


class StageVolumeConfig(BaseModel):
    dem_path: str
    stage_units: str = Field(default="feet", pattern="^(feet|meters)$")
    dem_vertical_units: str = Field(default="meters", pattern="^(feet|meters)$")


class StageVolumeCalculator:
    def __init__(self, config: StageVolumeConfig, model_area_gdf: gpd.GeoDataFrame):
        self.config = config
        with rasterio.open(self.config.dem_path) as src:
            out_image, out_transform = mask(src, model_area_gdf.geometry, crop=True)
            self.dem_data = out_image[0]
            self.nodata = src.nodata
            self.cell_area_m2 = abs(out_transform[0] * out_transform[4])
            self.valid_mask = self.dem_data != self.nodata

            # Normalize internal elevation to meters once during initialization
            if self.config.dem_vertical_units == "feet":
                self.dem_data = self.dem_data * 0.3048

    def _calc_vol(self, stage: float) -> float:
        """Internal helper to calculate volume for a single stage."""
        stage_meters = stage * 0.3048 if self.config.stage_units == "feet" else stage
        depth_map_m = stage_meters - self.dem_data
        flood_mask = self.valid_mask & (depth_map_m > 0)
        return np.sum(depth_map_m[flood_mask]) * self.cell_area_m2

    def get_relationship(
        self,
        start: float,
        stop: Optional[float] = None,
        n: int = 1,
        volume_to_stage: bool = False,
    ):
        """
        Calculates stage-volume relationships.

        Args:
            start: Start value of the range (stage or volume).
            stop: Stop value of the range (stage or volume). Defaults to start.
            n: Number of equidistant points.
            volume_to_stage: If True, calculate stage from target volume.
        """
        if stop is None:
            stop = start

        range_vals = np.linspace(start, stop, n) if n > 1 else [start]

        results = []
        for val in range_vals:
            if not volume_to_stage:
                results.append({"stage": val, "volume": self._calc_vol(val)})
            else:  # volume_to_stage
                stage = brentq(lambda s: self._calc_vol(s) - val, -100, 100.0)
                results.append({"stage": stage, "volume": val})

        return results[0] if n == 1 else results

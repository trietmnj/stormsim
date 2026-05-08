import geopandas as gpd
from shapely.geometry import box
from stormsim.stage_volume import StageVolumeCalculator, StageVolumeConfig

# 1. Representative bounding box in UTM Zone 17N (matches projected CRS)
# The file miami_30m_2.tif bounds: 578525, 2847059 to 583614, 2852049
test_geometry = box(578600, 2847100, 583500, 2852000)
model_area_gdf = gpd.GeoDataFrame(
    {"id": [1]}, geometry=[test_geometry], crs="EPSG:32617"
)

# 2. Run calculation for 5 ft
dem_path = "temp/data/miami_30m_2.tif"
dem_path = "temp/data/USGS_1_n26w081_20221103_utm.tif"
config = StageVolumeConfig(dem_path=dem_path, stage_units="feet")
calc = StageVolumeCalculator(config, model_area_gdf)

print("--- 1. Equispace Feet Stages for Feet Range (0 ft, 5 ft, n=5) ---")
res1 = calc.get_relationship(0, 1, n=20)
for r in res1:
    print(f"Stage: {r['stage']:.2f} ft | Volume: {r['volume']:.2f} m3")

print("\n--- 2. Stage Single for a given Volume (10M m3, volume_to_stage) ---")
res2 = calc.get_relationship(1, volume_to_stage=True)

print(f"Volume: {res2['volume']:.2f} m3 | Stage: {res2['stage']:.2f} ft")

print(
    "\n--- 3. Stages for Equal Volume Range (1M m3, 20M m3, n=10, volume_to_stage=True) ---"
)
res3 = calc.get_relationship(res1[0]["volume"], 20_000_000, n=100, volume_to_stage=True)
for r in res3:
    print(f"Volume: {r['volume']:.2f} m3 | Stage: {r['stage']:.2f} ft")

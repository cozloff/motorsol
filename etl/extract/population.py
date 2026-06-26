from __future__ import annotations

from pathlib import Path

import folium
import numpy as np
import rasterio
from PIL import Image
from rasterio.windows import from_bounds


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "gpw_v4_population_density_rev11_2020_30_sec_2020.tif"
HEATMAP_PATH = ROOT / "data" / "population_density_heatmap.png"
MAP_PATH = ROOT / "data" / "population_density_map.html"
WEB_MERCATOR_MAX_LAT = 85.05112877980659


def colorize_density(values: np.ma.MaskedArray) -> Image.Image:
    dense = values.filled(0).astype("float32")
    dense[dense < 0] = 0

    visible = dense > 0
    scale_max = np.percentile(dense[visible], 99.5)
    scaled = np.clip(np.log1p(dense) / np.log1p(scale_max), 0, 1)

    rgba = np.zeros((*dense.shape, 4), dtype=np.uint8)
    rgba[..., 0] = (255 * scaled).astype(np.uint8)
    rgba[..., 1] = (210 * scaled**1.8).astype(np.uint8)
    rgba[..., 2] = (40 * (1 - scaled)).astype(np.uint8)
    rgba[..., 3] = np.where(visible, (220 * scaled + 25).astype(np.uint8), 0)
    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    with rasterio.open(DATA_PATH) as dataset:
        # Leaflet/OpenStreetMap uses Web Mercator, which stops around +/-85 degrees.
        # Crop and let Folium project the latitude/longitude raster into that shape.
        bounds = rasterio.coords.BoundingBox(
            left=-180.0,
            bottom=-WEB_MERCATOR_MAX_LAT,
            right=180.0,
            top=WEB_MERCATOR_MAX_LAT,
        )
        window = from_bounds(*bounds, transform=dataset.transform)
        density = dataset.read(1, window=window, out_shape=(8640, 8640), masked=True)

    heat_image = colorize_density(density)
    heat_image.save(HEATMAP_PATH)

    world_map = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles="OpenStreetMap",
        max_bounds=True,
    )
    folium.raster_layers.ImageOverlay(
        name="Population density",
        image=np.asarray(heat_image),
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        opacity=0.75,
        interactive=True,
        cross_origin=False,
        mercator_project=True,
    ).add_to(world_map)
    folium.LayerControl().add_to(world_map)
    world_map.save(MAP_PATH)

    print(f"Wrote heat layer: {HEATMAP_PATH}")
    print(f"Wrote map: {MAP_PATH}")


if __name__ == "__main__":
    main()

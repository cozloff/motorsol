from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import rasterio


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RASTER_PATH = DATA_DIR / "gpw_v4_population_density_rev11_2020_30_sec_2020.tif"
AUX_PATH = RASTER_PATH.with_suffix(RASTER_PATH.suffix + ".aux.xml")


GPW_VARIABLES_TO_LOOK_FOR = [
    "population_count",
    "population_density",
    "land_area",
    "water_area",
    "data_quality_indicators",
    "national_identifier_grid",
]


def print_aux_metadata(path: Path) -> None:
    if not path.exists():
        print("\nNo .aux.xml sidecar found.")
        return

    print(f"\nAux metadata: {path.name}")
    root = ET.parse(path).getroot()
    for band in root.findall("PAMRasterBand"):
        band_number = band.attrib.get("band", "?")
        description = band.findtext("Description")
        print(f"  band {band_number}: {description}")
        for item in band.findall("./Metadata/MDI"):
            print(f"    {item.attrib.get('key')}: {item.text}")


def infer_gpw_family(path: Path) -> None:
    name = path.name
    match = re.match(r"(gpw_v4)_(.+?)_(rev\d+)_(\d{4})_(.+?)_(\d{4})\.tif$", name)
    if not match:
        return

    product, variable, revision, release_year, resolution, data_year = match.groups()
    print("\nFilename clues:")
    print(f"  product: {product}")
    print(f"  current variable: {variable}")
    print(f"  revision: {revision}")
    print(f"  resolution: {resolution}")
    print(f"  data year: {data_year}")

    print("\nOther GPW files worth looking for/download for count analysis:")
    for candidate in GPW_VARIABLES_TO_LOOK_FOR:
        candidate_name = name.replace(variable, candidate)
        status = "present" if (DATA_DIR / candidate_name).exists() else "missing"
        print(f"  {status:7} {candidate_name}")


def main() -> None:
    print(f"Data directory: {DATA_DIR}")
    print("\nFiles here:")
    for path in sorted(DATA_DIR.iterdir()):
        print(f"  {path.name} ({path.stat().st_size:,} bytes)")

    with rasterio.open(RASTER_PATH) as dataset:
        print(f"\nRaster: {RASTER_PATH.name}")
        print(f"  driver: {dataset.driver}")
        print(f"  bands: {dataset.count}")
        print(f"  shape: {dataset.width:,} x {dataset.height:,}")
        print(f"  dtype(s): {dataset.dtypes}")
        print(f"  crs: {dataset.crs}")
        print(f"  bounds: {dataset.bounds}")
        print(f"  nodata: {dataset.nodata}")
        print(f"  file tags: {dataset.tags()}")

        print("\nBand details:")
        for index in dataset.indexes:
            print(f"  band {index}")
            print(f"    description: {dataset.descriptions[index - 1]}")
            print(f"    tags: {dataset.tags(index)}")
            if hasattr(dataset, "stats"):
                stats = dataset.stats(indexes=[index], approx=True)[0]
            else:
                stats = dataset.statistics(index, approx=True)
            print(f"    approximate stats: {stats}")

    print_aux_metadata(AUX_PATH)
    infer_gpw_family(RASTER_PATH)

    print("\nBottom line:")
    print("  This local GeoTIFF contains population density only: one float32 band.")
    print("  For population count analysis, add the matching GPW population_count GeoTIFF")
    print("  to data/ and inspect it with this script too.")


if __name__ == "__main__":
    main()

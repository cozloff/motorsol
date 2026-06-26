from __future__ import annotations

import argparse
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "hrsl"
BUCKET_URL = "https://dataforgood-fb-data.s3.amazonaws.com/"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

CATEGORIES = {
    "general": "hrsl_general",
    "men": "hrsl_men",
    "women": "hrsl_women",
    "children_under_five": "hrsl_children_under_five",
    "elderly_60_plus": "hrsl_elderly_60_plus",
    "women_15_49": "hrsl_women_of_reproductive_age_15_49",
    "youth_15_24": "hrsl_youth_15_24",
}


def list_s3(prefix: str, delimiter: str | None = None) -> tuple[list[str], list[str]]:
    params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if delimiter:
        params["delimiter"] = delimiter

    keys: list[str] = []
    prefixes: list[str] = []
    token: str | None = None
    while True:
        if token:
            params["continuation-token"] = token
        response = requests.get(BUCKET_URL, params=params, timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        keys.extend(item.text or "" for item in root.findall("s3:Contents/s3:Key", S3_NS))
        prefixes.extend(item.text or "" for item in root.findall("s3:CommonPrefixes/s3:Prefix", S3_NS))
        if root.findtext("s3:IsTruncated", namespaces=S3_NS) != "true":
            break
        token = root.findtext("s3:NextContinuationToken", namespaces=S3_NS)
    return keys, prefixes


def download_key(key: str, output_dir: Path = DATA_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / Path(key).name
    url = urljoin(BUCKET_URL, key)

    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with output_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    return output_path


def category_prefix(category: str) -> str:
    folder = CATEGORIES.get(category, category)
    if folder not in CATEGORIES.values():
        raise SystemExit(f"Unknown category {category!r}. Try: {', '.join(CATEGORIES)}")
    return f"hrsl-cogs/{folder}/"


def latest_vrt_key(category: str) -> str:
    folder = CATEGORIES.get(category, category)
    return f"{category_prefix(category)}{folder}-latest.vrt"



def version_sort_key(key: str) -> tuple[int, ...]:
    version = key.rsplit("-", 1)[-1].removesuffix(".vrt").removeprefix("v")
    return tuple(int(part) for part in version.split("."))
def list_categories() -> None:
    print("Categories:")
    for short_name, folder in CATEGORIES.items():
        print(f"  {short_name:20} {folder}")


def list_versions(category: str) -> None:
    keys, _ = list_s3(category_prefix(category))
    versions = sorted((key for key in keys if key.endswith(".vrt") and "latest" not in key), key=version_sort_key)
    for key in versions:
        print(key)


def list_tiles(category: str, contains: str | None = None) -> None:
    keys, _ = list_s3(category_prefix(category))
    for key in keys:
        if not key.endswith(".tif"):
            continue
        if contains and contains not in key:
            continue
        print(key)


def find_tile(category: str, lat: float, lon: float) -> str | None:
    lat_floor = math.floor(lat / 10) * 10
    lon_floor = math.floor(lon / 10) * 10
    needle = f"globallat_{lat_floor}_lon_{lon_floor}_"
    keys, _ = list_s3(category_prefix(category))
    matches = [key for key in keys if key.endswith(".tif") and needle in key]
    if not matches:
        return None
    return sorted(matches)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore/download Meta CIESIN HRSL public data.")
    parser.add_argument("command", choices=["categories", "versions", "tiles", "download-vrt", "download-tile"])
    parser.add_argument("--category", default="general", help="Category short name, e.g. general, men, women.")
    parser.add_argument("--contains", help="Filter tile keys by substring.")
    parser.add_argument("--lat", type=float, help="Latitude for download-tile.")
    parser.add_argument("--lon", type=float, help="Longitude for download-tile.")
    args = parser.parse_args()

    if args.command == "categories":
        list_categories()
    elif args.command == "versions":
        list_versions(args.category)
    elif args.command == "tiles":
        list_tiles(args.category, args.contains)
    elif args.command == "download-vrt":
        path = download_key(latest_vrt_key(args.category))
        print(f"Downloaded {path}")
    elif args.command == "download-tile":
        if args.lat is None or args.lon is None:
            raise SystemExit("download-tile needs --lat and --lon")
        key = find_tile(args.category, args.lat, args.lon)
        if key is None:
            raise SystemExit("No HRSL tile found for that lat/lon/category.")
        path = download_key(key)
        print(f"Downloaded {path}")


if __name__ == "__main__":
    main()


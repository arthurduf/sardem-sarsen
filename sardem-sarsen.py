import argparse
import logging
import os
from dataclasses import dataclass
from functools import wraps
from time import time

import numpy as np
from osgeo import gdal  # type: ignore
from sardem import cop_dem
import sarsen
import pystac
import json

__version__ = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Remove the sardem logging handler so we can control the output, because the
# cop_dem module adds its own handler (poor practice for a library to do).
logging.getLogger("sardem").handlers.clear()
logger = logging.getLogger("sardem-sarsen")


@dataclass(frozen=True, kw_only=True)
class Args:
    catalog_path: str
    bbox: tuple[float, float, float, float]
    out_dir: str


def logtime(func):
    """Function decorator to log the time (seconds) a function takes to execute."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        logger.info("%s: %.1f seconds", func.__name__, time() - start)
        return result

    return wrapper

@logtime
def get_s1_grd_path(json_file):
    """
    Fetches the paths of S1 GRD products from the STAC catalog.

    Parameters
    ----------
    json_file : str
        Path to the JSON file containing the STAC catalog.

    Returns
    -------
    List[str]
        List of paths of S1 GRD products.
    """
    logger.info("Fetching S1 GRD product paths from the STAC catalog...")
    with open(json_file, 'r') as file:
        catalog_data = json.load(file)
        catalog = pystac.Catalog.from_dict(catalog_data)

    s1_grd_paths = []
    if catalog.links :
        for link in catalog.links:
            if link.rel == 'item':
               with open(link.absolute_href, 'r') as item_file:
                    item_data = json.load(item_file)
                    item = pystac.Item.from_dict(item_data)
                    if item.assets:
                        s1_grd_paths.append(item.assets['PRODUCT'].absolute_href)

    return s1_grd_paths

@logtime
def get_dem(bbox: tuple[float, float, float, float], out_dir: str) -> str:
    """
    Download DEM from Copernicus using Sardem.

    Parameters
    ----------
    bbox : str
        Bounding box coordinates (min_lon, min_lat, max_lon, max_lat).
        Example: '-156 18.8 -154.7 20.3'.
    out_dir : str
        Path to the output directory.

    Returns
    -------
    str
        Path to the downloaded DEM file
    """
    logger.info("Downloading DEM from Copernicus...")
    dem_file = os.path.join(out_dir, "dem.tif")
    cop_dem.download_and_stitch(dem_file, bbox, output_format="GTiff")
    return dem_file


@logtime
def run_sarsen(s1_file: str, dem_file: str, output_dir: str) -> str:
    """
    Runs SARsen processing on a Sentinel-1 GRD product and a DEM.

    Parameters
    ----------
    s1_file : str
        Path to the Sentinel-1 GRD product.
    dem_file : str
        Path to the DEM file.
    output_dir : str
        Path to the output directory.

    Returns
    -------
    str
        Path to the output of SARsen processing.
    """
    logger.info("Running SARsen on the S1 GRD product and the DEM...")
    output_file = os.path.join(output_dir, os.path.basename(s1_file).replace(".SAFE", "_sarsen_output.tif"))
    product = sarsen.Sentinel1SarProduct(s1_file,measurement_group="IW/VV")
    sarsen.terrain_correction(product, dem_file)
    logger.info("SARsen process completed. Output file: %s", output_file)
    return output_file


def parse_args() -> Args:
    """Parse the command-line arguments."""

    parser = argparse.ArgumentParser()

    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "--catalog_path",
        type=str,
        help="URL of the S1 GRD product from the Copernicus STAC Catalog",
        metavar="CATALOG_PATH",
        required=False,
    )
    parser.add_argument(
        "--bbox",
        type=float,
        help="lat/lon bounding box (example: --bbox '-118.068 34.222 -118.058 34.228')",
        nargs=4,
        metavar=("LEFT", "BOTTOM", "RIGHT", "TOP"),
        required=True,
    )
    parser.add_argument(
        "-o",
        "--out_dir",
        dest="out_dir",
        metavar="PATH",
        type=str,
        help="output directory to write DEM GeoTIFF to",
        required=True,
    )

    raw_args = parser.parse_args()

    return Args(
        catalog_path=raw_args.catalog_path,
        bbox=raw_args.bbox,
        out_dir=raw_args.out_dir,
    )


@logtime
def main() -> None:
    """
        Main function to execute the OGC application.

        Steps:
        1. Parse arguments
        2. Get S1 GRD product paths
        3. Download DEM
        4. Run SARsen
    """
    # Step 1: Parse arguments
    args = parse_args()

    # Step 2: Get S1 GRD product paths
    s1_grd_paths = get_s1_grd_path(args.catalog_path)

    # Step 3: Download DEM
    dem_file = get_dem(args.bbox, args.out_dir)

    # Step 4: Run SARsen for each S1 GRD product
    for s1_grd_path in s1_grd_paths:
        run_sarsen(s1_grd_path, dem_file, args.out_dir)

    logger.info("SARSEN process completed for all S1 GRD products.")

if __name__ == "__main__":
    main()

# src/mapping.py

import requests
import osmium

from urllib.parse import urlsplit
from abc import ABC, abstractmethod
from pathlib import Path
from shapely.geometry import Point, shape
from geotools import geocode_city
from applogger import log

class iGeoDownloader(ABC):
    @abstractmethod
    def get_pbf(self, city: str) -> Path:
        ...

class BBBikeDownloader(iGeoDownloader):
 
    def __init__(self, data_dir: str):
        log("info", "[IN] __init__ BBBikeDownloader")
        self.data_dir = data_dir
        log("info", "[OUT] __init__ BBBikeDownloader")

#-------------------------------------------------------------
# get_pbf: Fetch a pbf file for a city
#   city: str -> The city we want the pbf associated
#   return Path -> a path to the pbf containing the city
# misc: this function is inherited from iGeoDownloader
#------------------------------------------------------------- 
    def get_pbf(self, city: str) -> Path:
        log("warning", "Not implemented")
        raise NotImplementedError

class GeofabrikDownloader(iGeoDownloader):

    GEOFABRIK_INDEX = "https://download.geofabrik.de/index-v1.json"

    def __init__(self, data_dir: str):
        log("info", f"[IN] __init__ (data_dir = <{data_dir}>) GeofabrikDownloader")
        self.data_dir = data_dir
        log("info", "[OUT] __init__ GeofabrikDownloader")

#-------------------------------------------------------------
# get_pbf: Fetch a pbf file for a city
#   city: str -> The city we want the pbf associated
#   return Path -> a path to the pbf containing the city
# misc: this function is inherited from iGeoDownloader
#-------------------------------------------------------------
    def get_pbf(self, city: str) -> Path:
        log("info", f"[IN] get_pbf (city = <{city}>) GeofabrikDownloader")
        # 1. Get coordinates (lat/lon)
        coordinates = geocode_city(city)

        # 2. Find the smallest geofabrik region for this coordinates
        # TODO: In future version, search in DB if we already have a fitting region
        region = self.find_geofabrik_region(coordinates["lat"], coordinates["lon"])
        
        # 3. Download the region from geofabrik
        log("info", f"Geofabrik URL: {region['urls']['pbf']}")
        region_pbf = self._download(region["urls"]["pbf"], f"{city}_region.osm.pbf")

        # 4. Clip to city bounding box with osmium
        clipped_pbf = self._clip(region_pbf, coordinates["bbox"], city)
        log("info", f"[OUT] get_pbf (clipped_pbf = <{clipped_pbf}>) GeofabrikDownloader")
        return clipped_pbf

    def _download(self, url: str, filename: str):
        log("info", f"[IN] _download (url = <{url}>, filename = <{filename}>) GeofabrikDownloader")
        filepath = Path(f"../{self.data_dir}/{urlsplit(url).path.replace('/', '_')}")

        # Check if the file already exists
        # TODO: check a timestamp to maybe refresh the cache
        if not filepath.exists(): 
            log("info", f"Downloading {filename} from geofabrik")
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.touch()
            session = requests.Session()
            retries = requests.adapters.Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
            adapter = requests.adapters.HTTPAdapter(max_retries = retries)
            session.mount("https://", adapter)
            res = session.get(url, stream=True, timeout=600)
            res.raise_for_status()

            total_size = int(res.headers.get('content-length', 0))
            dled = 0
            with open(filepath, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
                    dled += len(chunk)
                    if total_size:
                        percent = (dled / total_size) * 100
                        print(f"\r  Progress: {percent:5.1f}% [{dled/1e6:.1f}/{total_size/1e6:.1f} MB]")
            if total_size:
                print() # New line

        else:
            size_mb = filepath.stat().st_size / (1024 * 1024)
            log("info", f"File <{filepath}> ({size_mb} MB) already exists, skipping download")
            print(f"Using cached file: {filepath} ({size_mb:.1f} MB)")
        log("info", f"[OUT] _download (filepath = <{filepath}>) GeofabrikDownloader")
        return filepath

#-------------------------------------------------------------
# _clip: Extract a city from a larger pbf
#   input_pbf: Path -> Path to a pbf containing data for more
#       than the city we're looking for
#   bbox: list -> The bounding box of the city we're looking
#       for (south, north, east, west)
#   city: str -> The city we want to get POIs from
# misc: Private
#-------------------------------------------------------------
    def _clip(self, input_pbf: Path, bbox: list, city: str):
        log("info", f"[IN] _clip (input_pbf = <{input_pbf}>, bbox = {bbox}, city = <{city}>) GeofabrikDownloader")
        # TODO: Not fond of calling processes, find another
        #   way if possible.
        import subprocess
        output = f"{self.data_dir}/{city.lower()}_clipped.osm.pbf"
        if Path.exists(Path(f"../{output}")):
            log("info", f"file {output} already exists. No need to extract again.")
            log("info", f"[OUT] _clip (output = <{output}>) GeofabrikDownloader")
            return Path(output)
        south, north, west, east = bbox
        subprocess.run([
            "osmium", "extract",
            "-b", f"{west},{south},{east},{north}",
            "--overwrite",
            f"{input_pbf}",
            "-o", str(f"../{output}"),
            ], check=True)
        log("info", f"[OUT] _clip (output = <{output}>) GeofabrikDownloader")
        return Path(output)

#-------------------------------------------------------------
# find_geofabrik_region: get the smallest region containing
#   target coordinates.
#   lat: float -> latitude
#   lon: float -> longitude
#   return dict ->
#-------------------------------------------------------------
    def find_geofabrik_region(self, lat: float, lon: float) -> dict:
        log("info", f"[IN] find_geofabrik_region (lat = {lat}, lon = {lon}) GeofabrikDownloader")
        # TODO: Check if we already have an up-to-date index
        res = requests.get(self.GEOFABRIK_INDEX, timeout=30)
        res.raise_for_status()
        index = res.json()

        point = Point(lon, lat)
        candidates = []

        for feature in index["features"]:
            geom = shape(feature["geometry"])
            if geom.contains(point):
                props = feature["properties"]
                size_mb = props.get("pbf", {}).get("size", float("inf"))
                candidates.append((size_mb, props))

        if not candidates:
            # TODO: add log to debug why lat/lon not found
            log("error", f"No Geofabrik region found with coordinates ({lat}, {lon})")
            raise ValueError(f"No Geofabrik region found with coordinates ({lat}, {lon})")

        candidates.sort(key=lambda x: x[0])
        log("info", f"[OUT] find_geofabrik_region (candidate = {candidates[0][1]}) GeofabrikDownloader")
        return candidates[0][1]


class CityLoader:

#-------------------------------------------------------------
# __init__: init
#   data_dir: str -> path to the directory where we store our
#       cities
#-------------------------------------------------------------
    def __init__(self, data_dir: str = "data/geo"):
        log("debug", f"[IN] __init__ (data_dir = <{data_dir}>) CityLoader")
        self.bbbike = BBBikeDownloader(data_dir)
        self.geofabrik = GeofabrikDownloader(data_dir)
        log("debug", f"[OUT] __init__ () Cityloader")

#-------------------------------------------------------------
# dl_pbf: download the pbf associated to the requested city.
#   city: str -> Name of the city we want the pbf from
#-------------------------------------------------------------
    def dl_pbf(self, city: str) -> Path:
        log("debug", f"[IN] dl_pbf (city = <{city}>) CityLoader")
        try:
            p = self.bbbike.get_pbf(city)
            log("debug", f"[OUT] dl_pbf (city_pbf = <{p}>) CityLoader")
            return p
        except:
            # TODO: Add log to indicate fallback
            log("info", f"City '{city}' not found on bbbike, falling back to geofabrik.")
            p = self.geofabrik.get_pbf(city)
            log("debug", f"[OUT] dl_pbf (city_pbf = <{p}>) CityLoader")
            return p 

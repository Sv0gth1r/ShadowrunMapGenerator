# src/mapping.py

import requests

from urllib.parse import urlsplit
from abc import ABC, abstractmethod
from pathlib import Path
from shapely.geometry import Point, shape
from geotools import geocode_city

class iGeoDownloader(ABC):
    @abstractmethod
    def get_pbf(self, city: str) -> Path:
        ...

class BBBikeDownloader(iGeoDownloader):
 
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

#-------------------------------------------------------------
# get_pbf: Fetch a pbf file for a city
#   city: str -> The city we want the pbf associated
#   return Path -> a path to the pbf containing the city
# misc: this function is inherited from iGeoDownloader
#------------------------------------------------------------- 
    def get_pbf(self, city: str) -> Path:
        raise OSError("Not implemented") 

class GeofabrikDownloader(iGeoDownloader):

    GEOFABRIK_INDEX = "https://download.geofabrik.de/index-v1.json"

    def __init__(self, data_dir: str):
        self.data_dir = data_dir

#-------------------------------------------------------------
# get_pbf: Fetch a pbf file for a city
#   city: str -> The city we want the pbf associated
#   return Path -> a path to the pbf containing the city
# misc: this function is inherited from iGeoDownloader
#-------------------------------------------------------------
    def get_pbf(self, city: str) -> Path:
        # 1. Get coordinates (lat/lon)
        coordinates = geocode_city(city)

        # 2. Find the smallest geofabrik region for this coordinates
        # TODO: In future version, search in DB if we already have a fitting region
        region = self.find_geofabrik_region(coordinates["lat"], coordinates["lon"])
        
        # 3. Download the region from geofabrik
        print(f"Geofabrik URL: {region['urls']['pbf']}")
        region_pbf = self._download(region["urls"]["pbf"], f"{city}_region.osm.pbf")

        # 4. Clip to city bounding box with osmium
        clipped_pbf = self._clip(region_pbf, coordinates["bbox"], city)
        return clipped_pbf

    def _download(self, url: str, filename: str):
        #filepath = Path(f"../{self.data_dir}/{filename.replace('/', '_')}")
        filepath = Path(f"../{self.data_dir}/{urlsplit(url).path.replace('/', '_')}")

        # Check if the file already exists
        # TODO: check a timestamp to maybe refresh the cache
        if not filepath.exists():    
            print(f"Downloading {filename} from geofabrik")
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
            print("File already exists, skipping download")
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"Using cached file: {filepath} ({size_mb:.1f} MB)")
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
        # TODO: Not fond of calling processes, find another
        #   way if possible.
        import subprocess
        output = f"{self.data_dir}/{city.lower()}_clipped.osm.pbf"
        south, north, west, east = bbox
        subprocess.run([
            "osmium", "extract",
            "-b", f"{west},{south},{east},{north}",
            "--overwrite",
            f"{input_pbf}",
            "-o", str(f"../{output}"),
            ], check=True)
        return Path(output)

#-------------------------------------------------------------
# find_geofabrik_region: get the smallest region containing
#   target coordinates.
#   lat: float -> latitude
#   lon: float -> longitude
#   return dict ->
#-------------------------------------------------------------
    def find_geofabrik_region(self, lat: float, lon: float) -> dict:
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
            raise ValueError(f"No Geofabrik region found with coordinates ({lat}, {lon})")

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]


class CityLoader:

#-------------------------------------------------------------
# __init__: init
#   data_dir: str -> path to the directory where we store our
#       cities
#-------------------------------------------------------------
    def __init__(self, data_dir: str = "data/geo"):
        self.bbbike = BBBikeDownloader(data_dir)
        self.geofabrik = GeofabrikDownloader(data_dir)

#-------------------------------------------------------------
# dl_pbf: download the pbf associated to the requested city.
#   city: str -> Name of the city we want the pbf from
#-------------------------------------------------------------
    def dl_pbf(self, city: str) -> Path:
        try:
            return self.bbbike.get_pbf(city)
        except:
            # TODO: Add log to indicate fallback
            print(f"City '{city}' not found on bbbike, falling back to geofabrik.")
            return self.geofabrik.get_pbf(city)

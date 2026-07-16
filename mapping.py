#!/usr/bin/env python3

from dataclasses import dataclass

import requests
import json

NOMINATIM_CITY_SEARCH="https://nominatim.openstreetmap.org/search?format=json&q="
OVERPASS_API="https://overpass-api.de/api/interpreter"
SR_USER_AGENT={"User-Agent": "ShadowrunMapper/1.0"}

@dataclass
class BBox:
    south: float
    north: float
    west: float
    east: float

#----------------------------------------------------
# get_city_coords
# [IN] city_name (string): Name of the city to find
# [OUT] obj (City_coords): Two coordinates (x,y) to
#   draw a square around the city
#----------------------------------------------------
def get_city_coords(city_name):
    url = f"{NOMINATIM_CITY_SEARCH}{city_name}"
    resp = requests.get(url, headers=SR_USER_AGENT)
    data = resp.json()
    if data:
        # For simplicity here, we take only the first result
        # TODO: allow user to choose if several cities share the same name
        bbox=BBox(
                float(data[0]['boundingbox'][0]),
                float(data[0]['boundingbox'][1]),
                float(data[0]['boundingbox'][2]),
                float(data[0]['boundingbox'][3]))
        return bbox 
    else:
        raise ValueError("City not found")

#----------------------------------------------------
# get_elements_in_square
# [IN] coordinates (Coords)
#----------------------------------------------------
def get_elements_in_square(bbox: BBox):
    query = f"""
    [out:json][timeout:90];
    (
        node["bar"]({bbox.south},{bbox.west},{bbox.north},{bbox.east});
    );
    out body;
    """
    resp = requests.post(OVERPASS_API, data=query.encode(), headers=SR_USER_AGENT, timeout=240)
    resp.raise_for_status()
    return resp.json()["elements"]

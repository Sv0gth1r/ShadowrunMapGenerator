from dataclasses import dataclass

import overpy
import requests

NOMINATIM_CITY_SEARCH="https://nominatim.openstreetmap.org/search?format=json&q="
SR_USER_AGENT={"User-Agent": "ShadowrunMapper/1.0"}

@dataclass
class Point_2D:
    x: float
    y: float

@dataclass
class Coords:
    top_left: Point_2D
    bottom_right: Point_2D

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
        x_1 = float(data[0]['boundingbox'][0])
        x_2 = float(data[0]['boundingbox'][1])
        y_1 = float(data[0]['boundingbox'][2])
        y_2 = float(data[0]['boundingbox'][3])
        coords=Coords(
                Point_2D(x_1, y_1),
                Point_2D(x_2, y_2))
        return coords
    else:
        raise ValueError("City not found")

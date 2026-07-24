# src/geotools.py

import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
 
#-------------------------------------------------------------
# geocode_city: Get the geographic data for a city (name,
#   latitude, longitude, bounding box)
#   city: str -> The city we want the data associated
#   return dict -> an aggregate of the aforementioned datas
#------------------------------------------------------------- 
def geocode_city(city: str) -> dict:
    resp = requests.get(
        NOMINATIM_SEARCH_URL,
        params={
            "q": city,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        },
        headers={"User-Agent": "shadowrun-mapper/0.1"},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"City '{city}' not found with Nominatim")

    # TODO: With a UI, allow user to pick a city whan multiple cities share a name
    ret = results[0]
    return {
        "display_name": ret["display_name"],
        "lat": float(ret["lat"]),
        "lon": float(ret["lon"]),
        "bbox": [float(c) for c in ret["boundingbox"]],
    }

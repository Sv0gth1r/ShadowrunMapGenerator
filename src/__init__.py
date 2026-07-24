#!/usr/bin/env python3

from map_renderer import render_map
from mapping import CityLoader 
import sys

def main():
    # 1. Get the city name
    city_name = sys.argv[1]

    # 2. (Down)Load the city POIs 
    cityLoader = CityLoader()
    cityLoader.dl_pbf(city_name)

    # 3. Convert the POIs to shadowrun

    # 4. Create the final map
    # render_map(bbox, pois, city_name)
main()

#!/usr/bin/env python3

import sys
import json
import logging.config
from applogger import *
from pathlib import Path
from city_mapping import CityLoader 
from city_parser import converter
from map_renderer import MapGenerator

def main():
    setup_logging()
    log("info", "[IN] main")

    # 1. Get the city name
    city_name = sys.argv[1]

    # 2. (Down)Load the city POIs 
    cityLoader = CityLoader()
    city_pbf = cityLoader.dl_pbf(city_name)

    # 3. Convert the POIs to shadowrun
    cityPOIs, tag_config = converter(f"../{city_pbf}")

    # 4. Create the final map
    mapGen = MapGenerator(cityPOIs, tag_config)
    mapGen.generate_map(Path(f"{city_name}_SR.html"))
    log("info", "[OUT] main")

main()

#!/usr/bin/env python3

from map_renderer import render_map
from mapping import *

def main():
    city_name = "Lyon"
    bbox = get_city_coords(city_name)
    pois = get_elements_in_square(bbox)
    render_map(bbox, pois, city_name)
main()

from mapping import *

import pytest

def test_get_city_coords():
    assert get_city_coords("Lyon") == BBox(45.7073666, 45.8082628, 4.7718132, 4.8984245)

def test_get_city_coords_no_exists():
    with pytest.raises(ValueError, match="City not found"):
        get_city_coords("____")

#bbox = BBox(45.7073666, 4.7718132, 45.8082628, 4.8984245)
#def test_fetching_pois():
#    ret = get_elements_in_square(bbox)
#    assert ret.elements != {}

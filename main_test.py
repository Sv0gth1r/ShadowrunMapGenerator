from main import Point_2D, Coords, get_city_coords

import pytest

def test_get_city_coords():
    assert get_city_coords("Lyon") == Coords(Point_2D(45.7073666, 4.7718132), Point_2D(45.8082628, 4.8984245))

def test_get_city_coords_no_exists():
    with pytest.raises(ValueError, match="City not found"):
        get_city_coords("____")

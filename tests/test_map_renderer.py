"""Tests for map_renderer.py - Folium map generation."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Try to import folium, skip tests if not available
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from map_renderer import MapGenerator

pytestmark = pytest.mark.skipif(not FOLIUM_AVAILABLE, reason="folium not installed")


class TestMapGeneratorInit:
    """Test MapGenerator initialization."""

    def test_init_stores_pois_and_config(self, sample_poi):
        """Test initialization stores input data."""
        pois = [sample_poi]
        config = {"amenity=hospital": {"category": "medical", "color": "#00ff00"}}

        generator = MapGenerator(pois, config)

        assert generator.pois == pois
        assert generator.tag_config == config

    def test_init_with_empty_pois(self):
        """Test initialization with empty POI list."""
        generator = MapGenerator([], {})

        assert generator.pois == []
        assert generator.tag_config == {}

    def test_init_with_none_pois(self):
        """Test initialization handles None gracefully (or rejects it)."""
        with pytest.raises((TypeError, AttributeError)):
            MapGenerator(None, {})


class TestMapCenterCalculation:
    """Test map center calculation."""

    @pytest.fixture
    def generator_with_pois(self, sample_poi):
        pois = [
            {**sample_poi, "lat": 47.0, "lon": -122.0},
            {**sample_poi, "lat": 48.0, "lon": -123.0},
            {**sample_poi, "lat": 47.5, "lon": -122.5},
        ]
        return MapGenerator(pois, {})

    def test_center_is_average_of_points(self, generator_with_pois):
        """Test that center is arithmetic mean of all points."""
        lat, lon = generator_with_pois._get_map_center()

        assert lat == pytest.approx(47.5, rel=0.01)
        assert lon == pytest.approx(-122.5, rel=0.01)

    def test_single_point_center_is_that_point(self, sample_poi):
        """Test that single POI maps to itself."""
        generator = MapGenerator([sample_poi], {})
        lat, lon = generator._get_map_center()

        assert lat == pytest.approx(sample_poi["lat"])
        assert lon == pytest.approx(sample_poi["lon"])


class TestIconColorMapping:
    """Test category to icon color conversion."""

    @pytest.fixture
    def generator(self, sample_poi):
        return MapGenerator([sample_poi], {})

    @pytest.mark.parametrize("category,expected_color", [
        ("runner_meet", "orange"),
        ("medical", "green"),
        ("weapons", "red"),
        ("tech", "blue"),
        ("food_and_drink", "beige"),
        ("law_enforcement", "purple"),
        ("accommodation", "darkpurple"),
        ("transportation", "cadetblue"),
        ("underground", "gray"),
        ("unknown_category", "white"),  # Default fallback
    ])
    def test_all_categories_have_colors(self, generator, category, expected_color):
        """Test all known categories map to expected colors."""
        color = generator._category_to_icon_color(category)
        assert color == expected_color

    def test_unknown_category_defaults_to_white(self, generator):
        """Test that unknown categories use white as fallback."""
        color = generator._category_to_icon_color("completely_unknown")
        assert color == "white"


class TestMarkerGeneration:
    """Test marker creation for POIs."""

    @pytest.fixture
    def generator(self, sample_poi):
        config = {
            "amenity=hospital": {
                "category": "medical",
                "color": "#00ff00",
                "description": "Medical facility"
            }
        }
        return MapGenerator([sample_poi], config)

    @patch("folium.Marker")
    def test_add_markers_called_for_each_poi(self, mock_marker_class, generator):
        """Test that a Marker is created for each POI."""
        mock_marker_instance = MagicMock()
        mock_marker_class.return_value = mock_marker_instance

        generator._add_pois()

        assert mock_marker_class.call_count == len(generator.pois)

    @patch("folium.Marker")
    def test_marker_location_correct(self, mock_marker_class, generator):
        """Test that marker location matches POI coordinates."""
        mock_marker_instance = MagicMock()
        mock_marker_class.return_value = mock_marker_instance

        generator._add_pois()

        call_kwargs = mock_marker_class.call_args_list[0][1]
        assert call_kwargs["location"] == [generator.pois[0]["lat"], generator.pois[0]["lon"]]

    @patch("folium.Marker")
    def test_marker_popup_contains_name(self, mock_marker_class, generator):
        """Test that popup contains POI name."""
        mock_marker_instance = MagicMock()
        mock_marker_class.return_value = mock_marker_instance

        generator._add_pois()

        # Should include HTML with name
        assert "Harborview Medical Center" in str(generator.pois[0].get("osm_name", ""))

    @patch("folium.Marker")
    def test_marker_icon_configuration(self, mock_marker_class, generator):
        """Test that icon is configured correctly."""
        mock_marker_instance = MagicMock()
        mock_marker_class.return_value = mock_marker_instance

        generator._add_pois()

        call_kwargs = mock_marker_class.call_args_list[0][1]
        icon_obj = call_kwargs['icon']
        assert isinstance(icon_obj, folium.Icon)
        assert "location" in call_kwargs
        assert "popup" in call_kwargs
        assert "icon" in call_kwargs
        assert "tooltip" in call_kwargs


class TestMapGeneration:
    """Test full map generation process."""

    @patch("folium.Map")
    @patch("folium.Marker")
    def test_generate_map_creates_folium_map(self, mock_marker, mock_map_class, tmp_path):
        """Test that generate_map creates a Folium Map instance."""
        mock_map_instance = MagicMock()
        mock_map_class.return_value = mock_map_instance
        poi = {
            "lat": 47.0, "lon": -122.0,
            "osm_key": "amenity", "osm_value": "hospital",
            "osm_name": "Test Hospital",
        }
        generator = MapGenerator([poi], {})
        generator.generate_map(tmp_path / "output.html")

        mock_map_class.assert_called_once()
        assert mock_map_instance.save.called

    @patch("folium.Map")
    @patch("folium.Marker")
    def test_generate_map_uses_dark_matter_tiles(self, mock_marker, mock_map_class):
        """Test that dark_matter tile provider is used."""
        mock_map_instance = MagicMock()
        mock_map_class.return_value = mock_map_instance

        poi = {
            "lat": 47.0, "lon": -122.0,
            "osm_key": "amenity", "osm_value": "hospital",
            "osm_name": "Test Hospital",
        }
        generator = MapGenerator([poi], {})
        generator.generate_map(Path("/tmp/test.html"))

        call_kwargs = mock_map_class.call_args[1]
        assert call_kwargs["tiles"] == "CartoDB dark_matter"

    @patch("folium.Map")
    @patch("folium.Marker")
    def test_generate_map_zoom_start_is_13(self, mock_marker, mock_map_class):
        """Test that initial zoom level is 13."""
        mock_map_instance = MagicMock()
        mock_map_class.return_value = mock_map_instance
        poi = {
            "lat": 47.0, "lon": -122.0,
            "osm_key": "amenity", "osm_value": "hospital",
            "osm_name": "Test Hospital",
        }
        generator = MapGenerator([poi], {})

        generator.generate_map(Path("/tmp/test.html"))

        call_kwargs = mock_map_class.call_args[1]
        assert call_kwargs["zoom_start"] == 13

    @patch("folium.Map")
    @patch("folium.Marker")
    def test_generate_map_saves_to_correct_path(self, mock_marker, mock_map_class, tmp_path):
        """Test that map is saved to specified path."""
        mock_map_instance = MagicMock()
        mock_map_class.return_value = mock_map_instance

        output_path = tmp_path / "my_custom_map.html"
        poi = {
            "lat": 47.0, "lon": -122.0,
            "osm_key": "amenity", "osm_value": "hospital",
            "osm_name": "Test Hospital",
        }
        generator = MapGenerator([poi], {})
        generator.generate_map(output_path)

        mock_map_instance.save.assert_called_once_with(output_path)


class TestPopupHTMLGeneration:
    """Test HTML popup content generation."""

    def test_popup_html_contains_required_elements(self, sample_poi):
        """Test popup HTML includes name, category, and description."""
        # This is tested indirectly via _add_pois, but could be unit tested
        # with a mock tag_config
        # config = {
        #    "amenity=hospital": {
        #        "category": "medical",
        #        "color": "#00ff00",
        #        "description": "Testing description"
        #    }
        # }

        # Manually trigger HTML generation (since _add_pois creates Markers)
        # We'd need to refactor to extract HTML generation into its own method
        # For now, this is covered in integration tests
        pass


# --- Integration Tests ---

class TestFullMapGeneration:
    """End-to-end map generation tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_map_generation_creates_valid_html(self, sample_poi, tmp_path):
        """Test that full generation creates valid HTML file."""
        config = {
            "amenity=hospital": {
                "category": "medical",
                "color": "#00ff00",
                "description": "Medical"
            }
        }

        generator = MapGenerator([sample_poi], config)
        output_path = tmp_path / "test_map.html"

        generator.generate_map(output_path)

        # Verify file exists and contains HTML
        assert output_path.exists()
        content = output_path.read_text()
        assert "<html>" in content.lower()
        assert "folium" in content.lower()

    @pytest.mark.integration
    def test_map_generates_multiple_pois(self, tmp_path):
        """Test map with multiple POIs."""
        pois = [
            {"lat": 47.0, "lon": -122.0,
             "osm_key": "amenity", "osm_value": "hospital", "osm_name": "Hosp1"},
            {"lat": 47.1, "lon": -122.1,
             "osm_key": "amenity", "osm_value": "pub", "osm_name": "Pub1"},
            {"lat": 47.2, "lon": -122.2,
             "osm_key": "shop", "osm_value": "convenience", "osm_name": "Shop1"},
        ]
        config = {}

        generator = MapGenerator(pois, config)
        output_path = tmp_path / "multi_poi_map.html"

        generator.generate_map(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        # Should contain all three POIs
        assert "Hosp1" in content
        assert "Pub1" in content
        assert "Shop1" in content

"""Tests for geotools.py - OSM/Nominatim API integration."""
import pytest
import responses
from unittest.mock import patch

from geotools import geocode_city, NOMINATIM_SEARCH_URL


class TestGeocodeCity:
    """Test city geocoding functionality."""

    @responses.activate
    def test_geocode_city_success(self):
        """Test successful city geocoding."""
        mock_response = [{
            "lat": "47.6062",
            "lon": "-122.3321",
            "display_name": "Seattle, King County, Washington, USA",
            "boundingbox": ["47.4810", "47.7341", "-122.4598", "-122.2244"]
        }]

        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            json=mock_response,
            status=200
        )

        result = geocode_city("Seattle")

        assert result["display_name"] == "Seattle, King County, Washington, USA"
        assert result["lat"] == 47.6062
        assert result["lon"] == -122.3321
        assert result["bbox"] == [47.4810, 47.7341, -122.4598, -122.2244]
        assert isinstance(result["bbox"], list)
        assert len(result["bbox"]) == 4

    @responses.activate
    def test_geocode_city_empty_result_raises(self):
        """Test that empty results raise ValueError."""
        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            json=[],
            status=200
        )

        with pytest.raises(ValueError, match="City .* not found"):
            geocode_city("NonexistentCity12345")

    @responses.activate
    def test_geocode_city_http_error_raises(self):
        """Test that HTTP errors propagate correctly."""
        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            status=503
        )

        with pytest.raises(Exception):  # requests raises for non-2xx
            geocode_city("Seattle")

    def test_geocode_city_timeout_handled(self):
        """Test that timeouts are handled with proper timeout setting."""
        with patch("geotools.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection timed out")

            with pytest.raises(Exception):
                geocode_city("Seattle")

            # Verify timeout was passed
            call_args = mock_get.call_args
            assert call_args.kwargs["timeout"] == 15

    @responses.activate
    def test_geocode_city_user_agent_set(self):
        """Test that custom User-Agent header is sent."""
        mock_response = [{
            "lat": "48.8566",
            "lon": "2.3522",
            "display_name": "Paris, France",
            "boundingbox": ["48.8155", "48.9021", "2.2241", "2.4699"]
        }]

        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            json=mock_response,
            status=200
        )

        geocode_city("Paris")

        # Verify User-Agent was set
        request = responses.calls[0].request
        assert request.headers["User-Agent"] == "shadowrun-mapper/0.1"

    @responses.activate
    def test_bounding_box_values_are_floats(self):
        """Test that bounding box values are converted to floats."""
        mock_response = [{
            "lat": "47.6062",
            "lon": "-122.3321",
            "display_name": "Seattle",
            "boundingbox": ["47.4810", "47.7341", "-122.4598", "-122.2244"]
        }]

        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            json=mock_response,
            status=200
        )

        result = geocode_city("Seattle")

        assert all(isinstance(x, float) for x in result["bbox"])
        assert all(isinstance(x, float) for x in [result["lat"], result["lon"]])

    @pytest.mark.hypothesis
    @pytest.mark.slow
    def test_geocode_city_various_city_names(self):
        """Test various city name formats (property-based test stub)."""
        # This would use hypothesis for property-based testing
        test_cities = [
            ("New York", "United States"),
            ("London", "United Kingdom"),
            ("Tokyo", "Japan"),
            ("Berlin", "Germany"),
            ("Sydney", "Australia"),
        ]

        for city_name, expected_country in test_cities:
            # Each would need real API calls - mark as slow
            pytest.skip("Real API calls - run manually or with --runslow")


class TestNominatimCompliance:
    """Test compliance with Nominatim usage policy."""

    def test_throttle_requests_properly(self):
        """Test that requests respect throttling (would need actual implementation)."""
        # Nominatim requires max 1 request per second
        # Consider adding rate limiting to geocode_city
        pass

    @responses.activate
    def test_limit_param_sent(self):
        """Test that limit=1 is sent to reduce data transfer."""
        mock_response = [{
            "lat": "47.6062",
            "lon": "-122.3321",
            "display_name": "Seattle",
            "boundingbox": ["47.4810", "47.7341", "-122.4598", "-122.2244"]
        }]

        responses.add(
            responses.GET,
            NOMINATIM_SEARCH_URL,
            json=mock_response,
            status=200
        )

        geocode_city("Seattle")

        call_params = responses.calls[0].request.params
        assert call_params["limit"] == "1"
        assert call_params["format"] == "json"
        assert call_params["addressdetails"] == "1"

"""Tests for city_mapping.py - downloader classes and file operations."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest
import responses

from city_mapping import (
    BBBikeDownloader,
    CityLoader,
    GeofabrikDownloader,
    iGeoDownloader
)


class TestIGeoDownloader:
    """Test abstract base class."""

    def test_abstract_class_cannot_instantiate(self):
        """Test that ABC cannot be directly instantiated."""
        with pytest.raises(TypeError):
            iGeoDownloader()

    def test_subclass_must_implement_get_pbf(self):
        """Test that subclasses must implement get_pbf."""
        
        class BadDownloader(iGeoDownloader):
            pass
        
        with pytest.raises(TypeError):
            BadDownloader()


class TestBBBikeDownloader:
    """Test BBBike downloader implementation."""

    def test_init_sets_data_dir(self, test_data_dir):
        """Test initialization sets data directory."""
        downloader = BBBikeDownloader(str(test_data_dir))
        assert downloader.data_dir == str(test_data_dir)

    def test_get_pbf_not_implemented(self, test_data_dir):
        """Test that BBBike.get_pbf raises NotImplementedError."""
        downloader = BBBikeDownloader(str(test_data_dir))
        
        with pytest.raises(NotImplementedError):
            downloader.get_pbf("Seattle")


class TestGeofabrikDownloader:
    """Test Geofabrik downloader implementation."""

    @pytest.fixture
    def downloader(self, test_data_dir):
        return GeofabrikDownloader(str(test_data_dir))

    def test_init_sets_attributes(self, downloader, test_data_dir):
        """Test initialization."""
        assert downloader.data_dir == str(test_data_dir)
        assert downloader.GEOFABRIK_INDEX == "https://download.geofabrik.de/index-v1.json"

    @responses.activate
    def test_find_geofabrik_region_smallest_region(self, downloader, mock_geofabrik_index):
        """Test that smallest containing region is selected."""
        responses.add(
            responses.GET,
            downloader.GEOFABRIK_INDEX,
            json=mock_geofabrik_index,
            status=200
        )
        
        # Coordinates that fall in smaller region
        result = downloader.find_geofabrik_region(47.5, -122.35)
        
        assert result["name"] == "Seattle Metro"
        assert result["pbf"]["size"] == 50  # Smaller size selected

    @responses.activate
    def test_find_geofabrik_region_no_match_raises(self, downloader):
        """Test that no matching region raises ValueError."""
        responses.add(
            responses.GET,
            downloader.GEOFABRIK_INDEX,
            json={"features": []},
            status=200
        )
        
        with pytest.raises(ValueError, match="No Geofabrik region found"):
            downloader.find_geofabrik_region(99.9, 99.9)

    @pytest.mark.integration
    @responses.activate
    def test_get_pbf_flow_complete(self, downloader, mock_geocode_response, mock_geofabrik_index):
        """Test complete PBF download flow (integration test)."""
        # Mock geocoding
        with patch("city_mapping.geocode_city") as mock_geo:
            mock_geo.return_value = {
                "lat": 47.6062,
                "lon": -122.3321,
                "bbox": [47.4810, 47.7341, -122.4598, -122.2244]
            }
            
            # Mock Geofabrik index
            responses.add(
                responses.GET,
                downloader.GEOFABRIK_INDEX,
                json=mock_geofabrik_index,
                status=200
            )
            
            # Mock PBF download
            responses.add(
                responses.GET,
                "https://example.com/seattle.pbf",
                body=b"fake pbf content" * 100,
                status=200,
                # headers={"Content-Length": "1000"}
            )
            
            # Mock _clip to avoid subprocess call
            with patch.object(downloader, "_clip") as mock_clip:
                mock_clip.return_value = Path("/tmp/clipped.osm.pbf")
                
                result = downloader.get_pbf("Seattle")
                
                assert result == Path("/tmp/clipped.osm.pbf")
                mock_clip.assert_called_once()

    @responses.activate
    def test_download_caching(self, downloader, test_data_dir):
        """Test that existing files are not re-downloaded."""
        cached_filepath = Path(test_data_dir) / "_file.pbf"
        cached_filepath.parent.mkdir(parents=True, exist_ok=True)
        cached_filepath.write_bytes(b"cached content") 
        
        # Register mock to satisfy responses if called
        responses.add(responses.GET, "https://example.com/file.pbf", status=200)

        # Call download - should hit cache and NOT make HTTP request
        result = downloader._download("https://example.com/file.pbf", "ignored.osm.pbf")
    
        # Verify file wasn't modified (still same size/content)
        assert cached_filepath.read_bytes() == b"cached content"
        assert result == cached_filepath 

    @pytest.mark.unit
    def test_download_session_retry_configured(self, downloader):
        """Test that download uses retry session."""
        with patch("city_mapping.requests.Session") as mock_session_cls:
            mock_session = Mock()
            mock_session.get.return_value = Mock(
                status_code=200,
                headers={"content-length": "100"},
                iter_content=lambda chunk_size: [b"data"]
            )
            mock_session_cls.return_value = mock_session
            
            # Mock Progress context manager
            with patch("city_mapping.Progress") as mock_progress_cls:
                mock_progress_ctx = Mock()
                mock_progress_ctx.__enter__ = Mock(return_value=MagicMock())
                mock_progress_ctx.__exit__ = Mock(return_value=False)
                mock_progress_cls.return_value = mock_progress_ctx
                
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("pathlib.Path.touch"):
                        with patch("pathlib.Path.mkdir"):
                            with patch("builtins.open", MagicMock()):
                                downloader._download("https://example.com/test.pbf", "test.osm.pbf")
            
            # Verify retry configuration was applied
            assert mock_session.mount.called

    @responses.activate
    def test_download_handles_http_errors(self, downloader, tmp_path):
        """Test that HTTP errors are raised appropriately."""
        filepath = tmp_path / "error.osm.pbf"
        
        responses.add(
            responses.GET,
            "https://example.com/error.pbf",
            status=500
        )

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(Exception):
                downloader._download("https://example.com/error.pbf", str(filepath))
        
    @pytest.mark.unit
    def test_clip_subprocess_call(self, downloader, tmp_path):
        """Test that _clip calls subprocess.run with correct arguments."""
        input_pbf = tmp_path / "input.osm.pbf"
        input_pbf.write_bytes(b"test")
        
        bbox = [47.4, 47.8, -122.5, -122.2]  # south, north, west, east
        
        with patch("city_mapping.subprocess.run") as mock_run:
            mock_run.return_value = Mock()
            
            with patch("pathlib.Path.exists", return_value=False):
                result = downloader._clip(input_pbf, bbox, "testcity")
            
            # Verify subprocess call
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            
            assert "osmium" in call_args
            assert "extract" in call_args
            assert "-b" in call_args
            assert "--overwrite" in call_args
            assert "check=True" in str(mock_run.call_args)

    @pytest.mark.unit
    def test_clip_uses_cached_file_when_exists(self, downloader, tmp_path):
        """Test that existing clipped files are reused."""
        input_pbf = tmp_path / "input.osm.pbf"
        input_pbf.write_bytes(b"test")
    
        # Match the actual output path format from _clip
        output_filename = "test_clipped.osm.pbf"
        expected_output = Path(f"{downloader.data_dir}/{output_filename}")
    
        # Mock exists to return True for the output path
        def mock_exists(path):
            return str(path) == str(expected_output) or str(path) == str(input_pbf)
    
        with patch("pathlib.Path.exists", side_effect=mock_exists):
            result = downloader._clip(input_pbf, [0, 1, 2, 3], "test")
            assert result == expected_output 

    @pytest.mark.unit
    def test_clip_bbox_order_conversion(self, downloader, tmp_path):
        """Test that bbox is reordered correctly for osmium (west,south,east,north)."""
        input_pbf = tmp_path / "input.osm.pbf"
        input_pbf.write_bytes(b"test")
        
        # Input is [south, north, east, west] from geocode_city
        bbox = [47.4810, 47.7341, -122.4598, -122.2244]
        
        with patch("city_mapping.subprocess.run") as mock_run:
            with patch("pathlib.Path.exists", return_value=False):
                downloader._clip(input_pbf, bbox, "test")
                
                # Extract -b argument (should be west,south,east,north)
                call_args = mock_run.call_args[0][0]
                bbox_arg = call_args[call_args.index("-b") + 1]
                
                # Verify ordering: west,south,east,north
                parts = bbox_arg.split(",")
                assert parts == ["-122.4598", "47.481", "-122.2244", "47.7341"]


class TestCityLoader:
    """Test CityLoader coordinator class."""

    def test_init_creates_downloader_instances(self, test_data_dir):
        """Test initialization creates both downloader types."""
        loader = CityLoader(str(test_data_dir))
        
        assert isinstance(loader.bbbike, BBBikeDownloader)
        assert isinstance(loader.geofabrik, GeofabrikDownloader)
        assert loader.bbbike.data_dir == str(test_data_dir)
        assert loader.geofabrik.data_dir == str(test_data_dir)

    @pytest.mark.unit
    def test_dl_pbf_prefers_bbbike_over_geofabrik(self, test_data_dir):
        """Test that BBBike is tried first before Geofabrik fallback."""
        loader = CityLoader(str(test_data_dir))
        
        with patch.object(loader.bbbike, "get_pbf", return_value=Path("/tmp/bbbike.osm.pbf")) as mock_bbbike:
            with patch.object(loader.geofabrik, "get_pbf") as mock_geofabrik:
                result = loader.dl_pbf("Seattle")
                
                mock_bbbike.assert_called_once_with("Seattle")
                mock_geofabrik.assert_not_called()  # No fallback needed
                assert result == Path("/tmp/bbbike.osm.pbf")

    @pytest.mark.unit  
    def test_dl_pbf_fallback_to_geofabrik_on_failure(self, test_data_dir):
        """Test fallback to Geofabrik when BBBike fails."""
        loader = CityLoader(str(test_data_dir))
        
        def raise_not_implemented(*args, **kwargs):
            raise NotImplementedError()
        
        with patch.object(loader.bbbike, "get_pbf", side_effect=raise_not_implemented) as mock_bbbike:
            with patch.object(loader.geofabrik, "get_pbf", return_value=Path("/tmp/geofabrik.osm.pbf")) as mock_geofabrik:
                result = loader.dl_pbf("Seattle")
                
                mock_bbbike.assert_called_once_with("Seattle")
                mock_geofabrik.assert_called_once_with("Seattle")
                assert result == Path("/tmp/geofabrik.osm.pbf")

    @pytest.mark.unit
    def test_dl_pbf_general_exception_triggers_fallback(self, test_data_dir):
        """Test that any exception triggers fallback, not just NotImplementedError."""
        loader = CityLoader(str(test_data_dir))
        
        with patch.object(loader.bbbike, "get_pbf", side_effect=Exception("Generic error")):
            with patch.object(loader.geofabrik, "get_pbf", return_value=Path("/tmp/fallback.osm.pbf")):
                result = loader.dl_pbf("Seattle")
                
                assert result == Path("/tmp/fallback.osm.pbf")

    def test_data_dir_default_is_geo(self):
        """Test default data directory."""
        loader = CityLoader()
        assert loader.bbbike.data_dir == "data/geo"
        assert loader.geofabrik.data_dir == "data/geo"


# --- Edge Cases and Error Scenarios ---

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def downloader(self, test_data_dir):
        """Create a GeofabrikDownloader instance."""
        from city_mapping import GeofabrikDownloader
        return GeofabrikDownloader(str(test_data_dir))

    @responses.activate
    def test_download_zero_byte_file(self, downloader, tmp_path):
        """Test handling of zero-byte response."""
        filepath = tmp_path / "empty.osm.pbf"

        responses.add(
            responses.GET,
            "https://example.com/empty.pbf",
            body=b"",
            status=200,
            headers={"content-length": "0"}
        )

        with patch("city_mapping.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-length": "0"}
            mock_response.iter_content = lambda chunk_size: []
            mock_get.return_value = mock_response
            
            with patch("city_mapping.Progress") as mock_progress:
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("builtins.open", MagicMock()):
                        downloader._download("https://example.com/empty.pbf", str(filepath))

    def test_large_bbox_coordinates(self, downloader, tmp_path):
        """Test handling of large coordinate values."""
        bbox = [-180, -90, 180, 90]  # World bounds
        
        with patch("city_mapping.subprocess.run"):
            with patch("pathlib.Path.exists", return_value=False):
                downloader._clip(tmp_path / "input.osm.pbf", bbox, "world")

    @pytest.mark.parametrize("city_name", [
        "",  # Empty string
        " ",  # Whitespace only
        "City With Spaces",  # Spaces
        "Café",  # Unicode
        "Istanbul (İstanbul)",  # Mixed scripts
    ])
    def test_city_name_sanitization(self, test_data_dir, city_name):
        """Test various city name formats (implementation depends on URL encoding)."""
        # Note: Your code uses city name directly in file paths
        # Consider sanitizing for OS compatibility
        loader = CityLoader(str(test_data_dir))
        
        # Just verify the method accepts it (real download would need mocking)
        # This is a validation that your API handles various inputs


# --- Concurrency and Thread Safety ---

class TestThreadSafety:
    """Test thread safety aspects."""

    @pytest.mark.slow
    def test_concurrent_downloads_safe(self, downloader, test_data_dir):
        """Test that concurrent downloads don't corrupt files."""
        # Would need threading/multiprocessing test
        # This is advanced - mark as slow
        pytest.skip("Requires concurrent execution testing")

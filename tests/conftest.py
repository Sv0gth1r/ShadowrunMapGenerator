"""Shared pytest fixtures and configuration."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a temporary data directory for tests."""
    base = tmp_path_factory.mktemp("data")
    geo_dir = base / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    return geo_dir

@pytest.fixture
def downloader(test_data_dir):
    """Create a GeofabrikDownloader instance for mapping tests."""
    from city_mapping import GeofabrikDownloader
    return GeofabrikDownloader(str(test_data_dir))

@pytest.fixture(scope="session")
def sample_osm_pbf(test_data_dir):
    """Create a minimal valid OSM PBF file for testing."""
    # Note: This is a placeholder. For real tests, you'd need an actual OSM PBF.
    # You can download a small test file from BBBike or use osmium to extract one.
    pbf_path = test_data_dir / "test.osm.pbf"
    # Placeholder - in reality, you need real OSM data
    return pbf_path


@pytest.fixture
def mock_logger_config(tmp_path):
    """Create a minimal logger configuration file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "applogger.MyJSONFormatter"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": "DEBUG"
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "json",
                "filename": str(tmp_path / "test.log"),
                "mode": "w"
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "DEBUG"
        }
    }
    
    config_file = config_dir / "logger.json"
    config_file.write_text(json.dumps(config))
    return config_dir


@pytest.fixture
def mock_sr_tags_config(tmp_path):
    """Create a minimal ShadowRun tag configuration."""
    config = {
        "categories": {
            "medical": {
                "color": "#00ff00",
                "description": "Medical facilities",
                "osm_tags": [
                    "amenity=hospital",
                    "amenity=clinic",
                    "healthcare=doctor"
                ]
            },
            "runner_meet": {
                "color": "#ffaa00",
                "description": "Meeting places",
                "osm_tags": [
                    "amenity=pub",
                    "amenity=bar",
                    "amenity=cafe"
                ]
            }
        }
    }
    
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "SR_tags.json"
    config_file.write_text(json.dumps(config))
    return str(config_file)


@pytest.fixture(autouse=True)
def reset_logging_config(monkeypatch):
    """Reset logging configuration before each test."""
    monkeypatch.setenv("PYTHONLOGGINGRESET", "1")


@pytest.fixture
def mock_geocode_response():
    """Mock Nominatim API response."""
    return {
        "lat": "47.6062",
        "lon": "-122.3321",
        "display_name": "Seattle, King County, Washington, USA",
        "boundingbox": [
            "47.4810", "47.7341",
            "-122.4598", "-122.2244"
        ]
    }


@pytest.fixture
def mock_geofabrik_index():
    """Mock Geofabrik index with regions."""
    return {
        "features": [
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-123, 47], [-122, 47], [-122, 48], [-123, 48], [-123, 47]]]
                },
                "properties": {
                    "name": "Washington",
                    "pbf": {"url": "https://example.com/washington.pbf", "size": 100},
                    "poly": {"url": "https://example.com/washington.poly"}
                }
            },
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-122.5, 47.4], [-122.2, 47.4], [-122.2, 47.7], [-122.5, 47.7], [-122.5, 47.4]]]
                },
                "properties": {
                    "name": "Seattle Metro",
                    "urls":{
                        "pbf": "https://example.com/seattle.pbf",
                        "poly": "https://example.com/seattle.poly"
                    },
                    "pbf": {
                        "size": 50
                    }
                }
            }
        ]
    }


# --- Parametrized test fixtures ---

@pytest.fixture(params=["debug", "info", "warning", "error", "critical"])
def log_severity(request):
    """Parameterized log severity levels."""
    return request.param


@pytest.fixture
def sample_poi():
    """Sample POI for testing."""
    return {
        "osm_key": "amenity",
        "osm_value": "hospital",
        "osm_name": "Harborview Medical Center",
        "lat": 47.6050,
        "lon": -122.3200,
        "tags": {
            "amenity": "hospital",
            "name": "Harborview Medical Center"
        }
    }

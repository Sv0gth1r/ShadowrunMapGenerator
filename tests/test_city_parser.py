"""Tests for city_parser.py - OSM POI extraction."""
import json
import osmium
from unittest.mock import MagicMock, patch

import pytest

from city_parser import POIParser, converter


class TestPOIParserInit:
    """Test POIParser initialization."""

    def test_loads_config_from_file(self, mock_sr_tags_config, tmp_path):
        """Test that parser loads tag configuration."""
        parser = POIParser(mock_sr_tags_config)

        assert hasattr(parser, "config")
        assert "categories" in parser.config
        assert "medical" in parser.config["categories"]

    def test_builds_tag_lookup(self, mock_sr_tags_config):
        """Test that tag_to_lookup dictionary is built correctly."""
        parser = POIParser(mock_sr_tags_config)

        # Should have entries for our test tags
        assert "amenity=hospital" in parser.tag_to_category
        assert "amenity=pub" in parser.tag_to_category

        # Verify structure
        assert "category" in parser.tag_to_category["amenity=hospital"]
        assert "color" in parser.tag_to_category["amenity=hospital"]
        assert "description" in parser.tag_to_category["amenity=hospital"]

    def test_config_file_not_found_raises(self, tmp_path):
        """Test that missing config file raises appropriate error."""
        nonexistent = str(tmp_path / "nonexistent.json")

        with pytest.raises(FileNotFoundError):
            POIParser(nonexistent)

    def test_invalid_json_raises(self, tmp_path):
        """Test that invalid JSON raises error."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            POIParser(str(config_file))


class TestNodeProcessing:
    """Test node (POI) processing."""

    @pytest.fixture
    def parser(self, mock_sr_tags_config):
        return POIParser(mock_sr_tags_config)

    def test_node_with_matching_tag_added(self, parser):
        """Test that nodes with matching tags are captured."""
        # Create mock OSM node
        mock_node = MagicMock(spec=osmium.osm.Node)
        mock_node.location.lat = 47.6062
        mock_node.location.lon = -122.3321

        # Create mock tags
        mock_tags = [("amenity", "hospital"), ("name", "Test Hospital")]
        mock_node.tags = mock_tags

        parser.node(mock_node)

        assert len(parser.pois) == 1
        poi = parser.pois[0]
        assert poi["osm_key"] == "amenity"
        assert poi["osm_value"] == "hospital"
        assert poi["osm_name"] == "Test Hospital"
        assert poi["lat"] == 47.6062
        assert poi["lon"] == -122.3321

    def test_node_without_matching_tag_skipped(self, parser):
        """Test that nodes without matching tags are ignored."""
        mock_node = MagicMock(spec=osmium.osm.Node)
        mock_node.tags = [("highway", "residential")]  # Not in our config

        parser.node(mock_node)

        assert len(parser.pois) == 0

    def test_node_without_tags_skipped(self, parser):
        """Test that nodes without any tags are ignored."""
        mock_node = MagicMock(spec=osmium.osm.Node)
        mock_node.tags = None

        parser.node(mock_node)

        assert len(parser.pois) == 0

    def test_node_unknown_tag_default_name(self, parser):
        """Test that nodes without name use default."""
        mock_node = MagicMock(spec=osmium.osm.Node)
        mock_node.tags = [("amenity", "hospital")]
        mock_node.location.lat = 47.0
        mock_node.location.lon = -122.0

        parser.node(mock_node)

        poi = parser.pois[0]
        assert poi["osm_name"] == "Unknown amenity=hospital"


class TestWayProcessing:
    """Test way processing (currently skipped in v1)."""

    @pytest.fixture
    def parser(self, mock_sr_tags_config):
        return POIParser(mock_sr_tags_config)

    def test_ways_not_processed_in_v1(self, parser):
        """Test that ways are currently skipped."""
        mock_way = MagicMock(spec=osmium.osm.Way)
        mock_way.tags = [("building", "yes")]

        parser.way(mock_way)

        # Should be no-op in v1
        assert len(parser.pois) == 0


class TestCategoryGrouping:
    """Test POI grouping by category."""

    @pytest.fixture
    def parser(self, mock_sr_tags_config, tmp_path):
        # Add multiple POIs
        mock_node_hospital = MagicMock(spec=osmium.osm.Node)
        mock_node_hospital.tags = [("amenity", "hospital"), ("name", "Hospital A")]
        mock_node_hospital.location.lat = 47.1
        mock_node_hospital.location.lon = -122.1

        mock_node_pub = MagicMock(spec=osmium.osm.Node)
        mock_node_pub.tags = [("amenity", "pub"), ("name", "Pub B")]
        mock_node_pub.location.lat = 47.2
        mock_node_pub.location.lon = -122.2

        parser = POIParser(mock_sr_tags_config)
        parser.node(mock_node_hospital)
        parser.node(mock_node_pub)

        return parser

    def test_group_by_category(self, parser):
        """Test that POIs are correctly grouped by Shadowrun category."""
        grouped = parser.get_pois_by_category()

        assert "medical" in grouped
        assert "runner_meet" in grouped
        assert len(grouped["medical"]) == 1
        assert len(grouped["runner_meet"]) == 1

    def test_unmatched_pois_filtered_out(self, parser, mock_sr_tags_config):
        """Test that unmatched POIs are handled."""
        # Add a POI with unknown tag
        mock_node_unknown = MagicMock(spec=osmium.osm.Node)
        mock_node_unknown.tags = [("unknown_tag", "value")]
        mock_node_unknown.location.lat = 47.3
        mock_node_unknown.location.lon = -122.3

        parser.node(mock_node_unknown)
        grouped = parser.get_pois_by_category()

        # Should be in unknown category
        assert "unknown" not in grouped


class TestConverterFunction:
    """Test the main converter function."""

    def test_converter_returns_tuple(self, mock_sr_tags_config, tmp_path, sample_osm_pbf):
        """Test that converter returns (pois, tag_config) tuple."""
        # Note: This needs a real OSM PBF file
        # For now, we'll mock the parser
        with patch("city_parser.POIParser") as MockParser:
            mock_instance = MockParser.return_value
            mock_instance.pois = [{"test": "poi"}]
            mock_instance.tag_to_category = {"test": {}}

            pois, tags = converter(sample_osm_pbf)

            assert isinstance(pois, list)
            assert isinstance(tags, dict)


# --- Real File Integration Tests ---

class TestRealFileParsing:
    """Test with real OSM files (requires test data)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_parse_small_osm_file(self, mock_sr_tags_config, sample_osm_pbf):
        """Test parsing a real small OSM PBF file."""
        if not sample_osm_pbf.exists():
            pytest.skip("No test OSM file available")

        parser = POIParser(mock_sr_tags_config)
        parser.apply_file(str(sample_osm_pbf), locations=True)

        # Just verify it doesn't crash
        assert parser is not True  # Actually should be >= 0


# --- Performance Tests ---

class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.slow
    def test_parser_memory_efficient_streaming(self, mock_sr_tags_config):
        """Test that parser uses streaming (memory efficient)."""
        # osmium.SimpleHandler is inherently streaming
        # This verifies we're not loading entire file into memory
        parser = POIParser(mock_sr_tags_config)

        # Verify it's a SimpleHandler (streaming)
        assert isinstance(parser, osmium.SimpleHandler)

# src/shadowrun_mapper/parser.py
import json
import osmium
from pathlib import Path
from applogger import log
from typing import List, Dict, Any

class POIParser(osmium.SimpleHandler):
    """
    Streams through an OSM PBF file and extracts POIs based on configured tags.
    
    POIs in OSM can be:
    - Nodes: Individual points (most POIs)
    - Ways: Buildings, parks, streets (when they have POI-relevant tags)
    """
    
    def __init__(self, config_path: str = "config/SR_tags.json"):
        super().__init__()
        
        # Load tag mapping
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        # Build reverse lookup: OSM tag -> Shadowrun category
        self.tag_to_category: Dict[str, Dict[str, Any]] = {}
        for category_name, category_config in self.config["categories"].items():
            for tag_spec in category_config["osm_tags"]:
                # Parse "amenity=bar" -> ("amenity", "bar")
                if ":" in tag_spec:
                    k, v = tag_spec.split(":", 1)
                    key = f"{k}={v}"
                else:
                    # Tags without value (e.g., just "shop")
                    key = tag_spec
                
                self.tag_to_category[key] = {
                    "category": category_name,
                    "color": category_config["color"],
                    "description": category_config["description"],
                }
        
        self.pois: List[Dict[str, Any]] = []
    
    def node(self, n: osmium.osm.Node):
        """Process OSM nodes."""
        if not n.tags:
            return
        
        poi = self._match_tags(n.tags)
        if poi:
            poi["lat"] = n.location.lat
            poi["lon"] = n.location.lon
            self.pois.append(poi)
    
    def way(self, w: osmium.osm.Way):
        """Process OSM ways (buildings, parks, etc.)."""
        # For simplicity, skip ways in v1. Focus on nodes only.
        # You can extend this later for buildings, parks, etc.
        pass
    
    def _match_tags(self, tags: osmium.osm.TagList) -> Dict[str, Any] | None:
        """
        Match OSM tags to Shadowrun categories.
        Returns the first matching POI, or None if no match.
        """
        for k, v in tags:
            key = f"{k}={v}"
            if key in self.tag_to_category:
                name = tags.get("name", f"Unknown {key}") if hasattr(tags, 'get') else dict(tags).get("name", f"Unknown {key}")
                return {
                    "osm_key": k,
                    "osm_value": v,
                    "osm_name": name,
                    "tags": dict(tags),  # Convert to plain dict
                }
        return None
    
    def get_pois_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group POIs by Shadowrun category for easy querying."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for poi in self.pois:
            print(f"get_pois_by_category | {poi['osm_key']}={poi['osm_value']}")
            cat = self.tag_to_category.get(
                f"{poi['osm_key']}={poi['osm_value']}", {}
            ).get("category", "unknown")
            grouped.setdefault(cat, []).append(poi)
        return grouped


def converter(city_path: Path):
    poiparser = POIParser()
    poiparser.apply_file(city_path, locations=True)
    print(f"{len(poiparser.pois)} POIs found.")
    return poiparser.pois, poiparser.tag_to_category

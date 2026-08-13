
import folium
from pathlib import Path
from statistics import mean
from typing import List, Dict, Any

class MapGenerator:
    fmap: folium.Map = {}

    def __init__(self, pois: List[Dict[str, Any]], tag_config: Dict[str, Dict[str, Any]]):
        if pois == None:
            raise AttributeError("POI list is None")
        self.pois = pois
        self.tag_config = tag_config

    def _get_map_center(self):
        lats = [poi["lat"] for poi in self.pois]
        lons = [poi["lon"] for poi in self.pois]
        center_lat = mean(lats)
        center_lon = mean(lons)
        return center_lat, center_lon

    def _category_to_icon_color(self, category: str) -> str:
        """Map Shadowrun categories to Icon colors for markers."""
        color_map = {
            "runner_meet": "orange",
            "medical": "green",
            "weapons": "red",
            "tech": "blue",
            "food_and_drink": "beige",
            "law_enforcement": "purple",
            "accommodation": "darkpurple",
            "transportation": "cadetblue",
            "underground": "gray",
        }
        return color_map.get(category, "white") 

    def _add_pois(self):
        for poi in self.pois:
            cat_info = self.tag_config.get(
                f"{poi['osm_key']}={poi['osm_value']}", {}
            )
            popup_html = f"""
                <div style="font-family: monospace;">
                    <strong>{poi.get('osm_name', 'Unknown')}</strong><br>
                    <span style="color: {cat_info.get('color', '#fff')}">
                        ● {cat_info.get('category', 'Uncategorized')}
                    </span><br>
                    <small>{cat_info.get('description', '')}</small>
                </div>
            """
            folium.Marker(
                location = [poi['lat'], poi['lon']],
                popup = folium.Popup(popup_html, max_width=300),
                icon = folium.Icon(
                    icon = "bullseye",
                    color = self._category_to_icon_color(cat_info.get('category')),
                    prefix = "fa",
                ),
                tooltip = poi.get('osm_name', ''),
            ).add_to(self.fmap)

    def generate_map(self, output_path: Path):
        # get center of map
        center_lat, center_lon = self._get_map_center()
        
        self.fmap = folium.Map(
            location = [center_lat, center_lon],
            zoom_start=13,
            tiles="CartoDB dark_matter"
        )

        self._add_pois()
        
        self.fmap.save(output_path)


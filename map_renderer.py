from mapping import BBox
import folium

def render_map(bbox: BBox, pois, city_name):
    average_lat = (bbox.north + bbox.south) / 2
    average_lon = (bbox.west + bbox.east) / 2
    m = folium.Map(location=[average_lat, average_lon], tiles='CartoDB dark_matter')
    for poi in pois:
        name = poi["tags"]["name"]
        category = "bar"
        folium.Marker(
            location = [poi["lat"], poi["lon"]],
            popup = f"{name} ({category})",
            icon=folium.Icon(color='blue')
        ).add_to(m)
        m.save(f"{city_name}_sr.html")

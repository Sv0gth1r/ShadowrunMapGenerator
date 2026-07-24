#from mapping import BBox
import folium

def render_map(bbox, pois, city_name):
    average_lat = (bbox.north + bbox.south) / 2
    average_lon = (bbox.west + bbox.east) / 2
    m = folium.Map(location=[average_lat, average_lon], tiles='CartoDB dark_matter')
    for poi in pois:
#        print(f"{poi}")
        if "name" in poi["tags"]:
            name = poi["tags"]["name"]
        else:
            name = "Unknown name"
        category = poi["tags"]["amenity"]
        match category:
            case "hospital"|"clinic"|"pharmacy":
                color=folium.Icon(color='lightgreen')
            case "police"|"courthouse"|"prison":
                color=folium.Icon(color='darkred')
            case "bar"|"nightclud"|"casino":
                color=folium.Icon(color='pink')
            case "bank"|"atm":
                color=folium.Icon(color='orange')
            case "computer_club"|"internet_cafe":
                color=folium.Icon(color='blue')
            case _:
                color=folium.Icon(color='lightgray')

        folium.Marker(
            location = [poi["lat"], poi["lon"]],
            popup = f"{name} ({category})",
            icon=color
        ).add_to(m)
        m.save(f"{city_name}_sr.html")

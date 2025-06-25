import plotly.graph_objects as go 
from math import *
import geohash2
import requests 
from path_util import segment2coords, segment_info, node2coord, find_nearest_node, places
from path_finder import full_djikstra
import numpy as np


geohash_cell_size = {
        4: (39, 19.5),    # ~39 km x 19.5 km
        5: (4.9, 4.9),    # ~4.9 km x 4.9 km
        6: (1.2, 0.6),    # ~1.2 km x 0.6 km
        7: (0.15, 0.15),  # ~150 m x 150 m
        8: (0.038, 0.019) # ~38 m x 19 m
    }

def get_bounding_box(curr_location, r):
    # make sure its lat, lon, r in km

    for prec in geohash_cell_size:
        dlat, dlon = geohash_cell_size[prec]
        if r > dlat:
            prec-=1
            break
    # print(prec+1)
    print("search bounding box", prec, geohash_cell_size[prec])
    lat, lon = curr_location[0], curr_location[1]

    C = 40075
    dY = r / C * 360
    print(dY*cos(radians(lat)))
    dX = dY*cos(radians(lat))
    print(dX, dY)
    lat_min = lat - dX
    lat_max = lat + dX

    lon_min = lon - dY
    lon_max = lon + dY

    NW = geohash2.encode(lat_max, lon_min, precision=prec)
    NE = geohash2.encode(lat_max, lon_max, precision=prec)
    SW = geohash2.encode(lat_min, lon_min, precision=prec)
    SE = geohash2.encode(lat_min, lon_max, precision=prec)
    print(f"NW: {NW}{lat_max, lon_min}, NE: {NE}{lat_max, lon_max}, SW: {SW}{lat_min, lon_min}, SE: {SE}{lat_min, lon_max}")

    return  (lat_min, lat_max, lon_min, lon_max), prec

def visualize_path(coords, node_ids=None):
    fig = go.Figure()
    node_lats = []
    node_lons = []
    edge_lats = []
    edge_lons = []

    node_lats += [coords[1] for node in coords]
    node_lons += [coords[0] for node in coords]
    if not node_ids:
        node_ids = range(len(node_lats))
    
    # Create edges
    for i in range(1,len(coords)):
        A = coords[i-1]
        B = coords[i]
        lonA, latA = A
        lonB, latB = B
        edge_lats += [latA, latB, None] 
        edge_lons += [lonA, lonB, None]
    # Create the map

    # Add edges

    fig.add_trace(go.Scattermapbox(
        lat=edge_lats,
        lon=edge_lons,
        mode="lines",
        line=dict(width=5, color='red'),
        name=f"Path Edge"
    ))

    # Add nodes
    fig.add_trace(go.Scattermapbox(
        lat=node_lats,
        lon=node_lons,
        mode="markers+text",
        marker=dict(size=12, color='red'),
        text=[f"Node {node}" for node in node_ids],
        name=f"Path Node"
    ))

    # Set map layout
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=51.515, lon=-0.118),
            zoom=15
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    fig.show()


def visualize_paths(paths):
    # Create a scatter plot for nodes
    node_lats = []
    node_lons = []
    edge_lats = []
    edge_lons = []

    colors = ["green", "blue", "red", "orange", "purple", "cyan", "magenta"]
    fig = go.Figure()

    for idx, nodes in enumerate(paths):

        node_lats = []
        node_lons = []
        edge_lats = []
        edge_lons = []

        node_lats += [node2coord[node][1] for node in nodes]
        node_lons += [node2coord[node][0] for node in nodes]
        node_ids = list(node2coord.keys())

        # Create edges
        
        for i in range(1,len(nodes)):
            A = nodes[i-1]
            B = nodes[i]
            lonA, latA = node2coord[A]
            lonB, latB = node2coord[B]
            edge_lats += [latA, latB, None] 
            edge_lons += [lonA, lonB, None]
        # Create the map

        # Add edges

        fig.add_trace(go.Scattermapbox(
            lat=edge_lats,
            lon=edge_lons,
            mode="lines",
            line=dict(width=3, color=colors[idx % len(colors)]),
            name=f"Path {idx+1} Edge",
            hoverinfo="text"
        ))

        # Add nodes
        fig.add_trace(go.Scattermapbox(
            lat=node_lats,
            lon=node_lons,
            mode="markers",
            marker=dict(size=8, color=colors[idx % len(colors)]),
            text=[f"Node {node}" for node in nodes],
            name=f"Path {idx + 1} Node",
            hoverinfo="skip"
        ))

    # Set map layout
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=51.515, lon=-0.118),
            zoom=15
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    fig.show()

def show_places(fig, place_ids, idx=0, color='blue'):
    coords = [places[x]['coord'] for x in place_ids if x in places]
    names = [places[x]['name'] for x in place_ids if x in places]
    # print(", ".join(names))
    lats = [coord[1] for coord in coords]
    lons = [coord[0] for coord in coords]
    fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="markers",
                text=names,
                name=f"places on {idx} border",
                hoverinfo="text",
                showlegend=False,
                opacity=0.5,
                marker=dict(size=8, color="white"),
            ))
    fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="markers",
                text=names,
                name=f"places on {idx}",
                showlegend=False,
                opacity=0.6,
                hoverinfo="skip",
                marker=dict(size=6, color=color),
            ))

def draw_circle(fig, lat, lon, radius_km, num_points=100):
    """
    Calculate the coordinates of a circle's boundary given a center and radius.
    :param lat: Latitude of the center
    :param lon: Longitude of the center
    :param radius_km: Radius in kilometers
    :param num_points: Number of points to calculate for the circle boundary
    :return: List of latitude and longitude points
    """
    R = 6371  # Earth's radius in kilometers
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    d = radius_km / R  # Angular distance

    circle_lats = []
    circle_lons = []

    for angle in np.linspace(0, 2 * np.pi, num_points):
        lat_point = np.arcsin(np.sin(lat_rad) * np.cos(d) +
                              np.cos(lat_rad) * np.sin(d) * np.cos(angle))
        lon_point = lon_rad + np.arctan2(np.sin(angle) * np.sin(d) * np.cos(lat_rad),
                                         np.cos(d) - np.sin(lat_rad) * np.sin(lat_point))
        circle_lats.append(float(np.degrees(lat_point)))
        circle_lons.append(float(np.degrees(lon_point)))

    fig.add_trace(go.Scattermap(
        lat=circle_lats,
        lon=circle_lons,
        mode="lines",
        line=dict(width=4, color="red"),
        fill="toself",  # Fill the circle
        fillcolor="rgba(0, 0, 255, 0.2)",  # Semi-transparent fill
        name=f"Radius: {radius_km} km",
        showlegend=False
    ))

def calculate_neighborhood(lat, lon, radius_km):
    R = 6371  # Earth's radius in kilometers
    origin, _ = find_nearest_node(lon, lat)
    border_nodes = full_djikstra(origin, radius_km)
    border_dist = [border_nodes[x] for x in border_nodes]
    coords = [node2coord[x] for x in border_nodes]
    coords = sort_by_angle(coords, (lon, lat))
    lats = [x[1] for x in coords]
    lons = [x[0] for x in coords]
    lats += [lats[0]]
    lons += [lons[0]]
    return lats, lons

def sort_by_angle(border_coords, origin):
    """
    Sort border coordinates by angle relative to the origin point 
    """
    olat, olon = origin
    def polar_angle(point):
        lat, lon = point
        angle = np.arctan2(lat-olat, lon-olon)
        return angle

    sorted_points = sorted(border_coords, key=polar_angle)
    return sorted_points

def create_default_map(lat=51.515, lon=-0.118):
    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=[51.515],
        lon=[-0.118],
        marker=dict(size=2, color="red"),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=lat, lon=lon),
            zoom=14
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    # print("Default Map")
    return fig

def highlight_place(fig, place_id, color):
    if place_id not in places:
        return
    coord = places[place_id]["coord"]
    name = places[place_id]["name"]
    fig.add_trace(go.Scattermap(
        lat = [coord[1]], lon=[coord[0]],
        mode="markers",
        marker=dict(size=14, color="white"),
        name="highlited place border",
        opacity=0.7,
        showlegend=False
    ))
    fig.add_trace(go.Scattermap(
        lat = [coord[1]], lon=[coord[0]],
        mode="markers+text",
        text=[name],
        marker=dict(size=10, color=color, opacity=0.7),
        textfont=dict(color="white"),
        textposition="top right",
        name="highlited place",
        showlegend=False
    ))


if __name__=="__main__":
    lat, lon = 51.5225289,  -0.1141136
    fig = create_default_map(lat, lon)
    radius_km = 0.6
    circle_lats, circle_lons = calculate_neighborhood(lat, lon, radius_km)
    print(len(circle_lats), len(circle_lons))
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode="markers",
        marker=dict(size=10, color="red"),
        # fill="toself",  # Fill the circle
        # fillcolor="rgba(0, 0, 255, 0.2)",  # Semi-transparent fill
        name=f"Origin"
    ))
    fig.add_trace(go.Scattermap(
        lat=circle_lats,
        lon=circle_lons,
        mode="lines",
        line=dict(width=2, color="red"),
        fill="toself",  # Fill the circle
        fillcolor="rgba(0, 0, 255, 0.2)",  # Semi-transparent fill
        name=f"Radius: {radius_km} km"
    ))
    fig.show()
    # print(visualize_segment(segment2coords))
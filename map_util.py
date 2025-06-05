import plotly.graph_objects as go 
from math import *
import geohash2
import requests 
from path_util import segment2coords, segment_info, node2coord

def get_current_location():
    resp = requests.get("https://ipinfo.io/json")
    data = resp.json()
    location = data["loc"].split(",")
    lat, lon = float(location[0]), float(location[1])
    return lat, lon 


def visualize_segment(segment2coords, selected=None):
    fig = go.Figure()
    
    for segment_id, segment in segment2coords.items():
        # node, coords = segment
        # print(segment_id, coords)
        if segment_info[segment_id].get("underground"):
            continue
        lats = [coords[1] for node, coords in segment]
        lons = [coords[0] for node, coords in segment]
        # print(lats)
        color = "blue" if segment_info[segment_id]["foot"] else "red"
        width = 2 if segment_id!=selected else 4

        fig.add_trace(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=width, color=color),
            hoverinfo="text",
            text=segment_id,
            name=f"Segment {segment_id}",
            showlegend=False
        ))
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=51.515, lon=-0.118),
            zoom=14
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    fig.show()


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

def find_nearest_node(lon, lat, geohash2node, node2coord):
    geohash = geohash2.encode(lon, lat, precision=7)
    # print(geohash, geohash2node.get(geohash))
    # print(geohash2node)
    nearby_nodes = geohash2node.get(geohash)
    closest_node = None
    shortest = 1e10
    for node in nearby_nodes:
        coord2 = node2coord[node]
        dist = get_dist([lon,lat], coord2)
        if dist<shortest:
            shortest = dist
            closest_node = node
    return closest_node, dist


def get_dist(coord1, coord2):
    lon, lat = coord1
    lon2, lat2 = coord2
    R = 6471
    dlat = radians(lat2 - lat)
    dlon = radians(lon2 - lon)

    a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    return distance

if __name__=="__main__":
    
    print(visualize_segment(segment2coords))
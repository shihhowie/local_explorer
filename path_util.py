import geohash2
import json
from collections import defaultdict
from math import *
from consts import *


def interpolate_points(start, end, num_points):
    lon1, lat1 = start
    lon2, lat2 = end
    lons = [lon1 + (lon2-lon1)* i / (num_points-1) for i in range(num_points)]
    lats = [lat1 + (lat2-lat1)* i / (num_points-1) for i in range(num_points)]
    return list(zip(lons,lats))

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

def build_graph(connections):
    graph = defaultdict(dict)
    segment2coords = {}
    for connection in connections:
        segment_id = connection['properties']['id']
        path_coords = []
        if connection['properties']['subtype']!="road":
            # print(connection['properties']['subtype'])
            continue
        nodes = connection['properties']['connectors']
        for node in nodes:
            neighbors = {}
            node_id = node['connector_id']
            if node_id not in node2coord:
                continue
            node_coord = node2coord[node_id]
            path_coords.append((node_id, node_coord))
            for x in nodes:
                if x!=node:
                    neighbor = x["connector_id"]
                    if neighbor not in node2coord:
                        continue
                    nb_coord = node2coord[neighbor]
                    dist = get_dist(nb_coord, node_coord)
                    neighbors[neighbor] =  (dist, segment_id)
            graph[node_id].update(neighbors)
        segment2coords[segment_id] = path_coords
    # print(graph)
    return graph, segment2coords

def get_node_dist(A,B):
    if A not in node2coord or B not in node2coord:
        return None
    return get_dist(node2coord[A], node2coord[B])

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

def map_nodes_to_geohashes(nodes):
    # reduce nodes really close together in the to one node
    node2geohash = defaultdict()
    geohash2node = defaultdict(list)
    for node in nodes:
        lon, lat = node['geometry']['coordinates']
        id = node['properties']['id']
        geohash7 = geohash2.encode(lon, lat, precision=7)
        geohash8 = geohash2.encode(lon, lat, precision=8)
        node2geohash[id] = (geohash7,geohash8)
        geohash2node[geohash7].append(id)
        geohash2node[geohash8].append(id)
    
    for geohash in geohash2node:
        lat, lon, _, _ = geohash2.decode_exactly(geohash)
        node2coord[geohash] = [lat, lon]
    return node2geohash, geohash2node

def load_vertices():
    node2coord = {}
    with open('./local_data/test_connector.geojson') as f:
        nodes = json.load(f)
        nodes = nodes['features']
        for node in nodes:
            coord = node['geometry']['coordinates']
            id = node['properties']['id']
            node2coord[id] = coord
    return node2coord, nodes


def load_connections():
    with open("./local_data/test_segments.geojson") as f:
        data = json.load(f)
    data = data['features']
    
    return data

def load_maps():
    global node2coord, graph, segment2coords, node2geohash, geohash2node, segment2feat

    node2coord, nodes = load_vertices()
    connections = load_connections()
    graph, segment2coords = build_graph(connections)
    node2geohash, geohash2node = map_nodes_to_geohashes(nodes)
    return graph, segment2coords, node2geohash, geohash2node, node2coord

def get_places():
    with open("./local_data/test_places.geojson") as f:
        data = json.load(f)
    data = data['features']
    places = {}
    geohash2place = defaultdict(list)
    category_counter = defaultdict(int)
    for place in data:
        id = place['properties']['id']
        lon, lat = place['geometry']['coordinates']
        cat = place['properties']['categories']
        prim_cat = cat.get("primary")
        categories = []
        if prim_cat in valid_categories:
            categories.append(prim_cat)
        if cat["alternate"]:
            for cat in cat["alternate"]:
                if cat in valid_categories:
                    categories.append(cat)
        if not categories:
            continue
        name = place['properties']['names'].get("primary", "")
        geohash = geohash2.encode(lon, lat, precision=8)
        places[id] = {"name": name, "coord": (lon, lat), "categories": categories}
        geohash2place[geohash].append(id)
    # category_counter = sorted(category_counter.items(), key=lambda x: x[1])
    # print(json.dumps(category_counter, indent=2))
    return places, geohash2place


# Define the base32 characters used in geohashes
BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'

# Define the neighbor and border mappings
NEIGHBORS = {
    'n': ['p0r21436x8zb9dcf5h7kjnmqesgutwvy', 'bc01fg45238967deuvhjyznpkmstqrwx'],
    's': ['14365h7k9dcfesgujnmqp0r2twvyx8zb', '238967debc01fg45kmstqrwxuvhjyznp'],
    'e': ['bc01fg45238967deuvhjyznpkmstqrwx', 'p0r21436x8zb9dcf5h7kjnmqesgutwvy'],
    'w': ['238967debc01fg45kmstqrwxuvhjyznp', '14365h7k9dcfesgujnmqp0r2twvyx8zb']
}

BORDERS = {
    'n': ['prxz', 'bcfguvyz'],
    's': ['028b', '0145hjnp'],
    'e': ['bcfguvyz', 'prxz'],
    'w': ['0145hjnp', '028b']
}

def get_neighbors(geohash):
    neighbors = {}
    for direction in NEIGHBORS:
        neighbors[direction] = calculate_adj(geohash, direction)
    return neighbors

def calculate_adj(geohash, direction):
    geohash = geohash.lower()
    last_char = geohash[-1]
    type_index = len(geohash) % 2
    base = geohash[:-1]

    # print("geohash", geohash, "type_index", type_index, "base", base)
    if last_char in BORDERS[direction][type_index]:
        base = calculate_adj(base, direction)
    neighbor_char = BASE32[NEIGHBORS[direction][type_index].index(last_char)]
    return base + neighbor_char

graph, segment2coords, node2geohash, geohash2node, node2coord = load_maps()
places, geohash2place = get_places()


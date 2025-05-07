# map 
# sw: 51.515, -0.118 -> ws: -0.118,51.515
# ne: 51.527, -0.105 -> en: -0.105,51.527
# segments
# overturemaps download --bbox=-0.118,51.515,-0.105,51.527 -f geojson --type=segment -o test_segments.geojson
# connector 51.535, -0.102
# overturemaps download --bbox=-0.119,51.511,-0.102,51.535 -f geojson --type=connector -o test_connector.geojson
import json
from collections import defaultdict
from math import *
import heapq
from map_util import visualize_path
from numpy import random
import geohash2


def run_Astar(start, end, graph, k):
    paths = []
    i = 0
    for _ in range(k):
        heap = [(0,start,[])]
        path_len = {}
        
        while heap:
            dist_from, node, path = heapq.heappop(heap)
            if node in path_len:
                continue
            path_len[node] = dist_from
            if node == end:
                paths.append(path)
                break
            neighbors = graph[node]
            for id, dist in neighbors.items():
                if id not in path_len or id==end:
                    tmp = path.copy()
                    tmp.append(node)
                    dist_remain = get_dist(id, end)
                    rand_dist = random.normal(scale=0.07)
                    heapq.heappush(heap,(dist+dist_from+dist_remain+rand_dist, id, tmp))
            i += 1
    # print(path)
    # print(path_len[end])
    print("visited", i)
    # print(paths)
    return paths

def run_djikstra(start, end, graph):
    path = []
    heap = [(0,start,path)]
    path_len = {}
    
    i = 0
    while heap:
        dist1, node, path = heapq.heappop(heap)
        if node in path_len:
            continue
        path_len[node] = dist1
        if node == end:
            break
        neighbors = graph[node]
        for id, dist in neighbors.items():
            if id not in path_len:
                tmp = path.copy()
                tmp.append(node)
                heapq.heappush(heap,(dist+dist1, id, tmp))
        i += 1
    # print(path)
    # print(path_len[end])
    print("visited", i)
    return path, path_len[end]

def consolidate_nodes(nodes):
    # reduce nodes really close together in the to one node
    node2geohash = defaultdict()
    geohash2node = defaultdict(list)
    for node in nodes:
        lon, lat = node['geometry']['coordinates']
        id = node['properties']['id']
        geohash = geohash2.encode(lon, lat, precision=9)
        node2geohash[id] = geohash
        geohash2node[geohash].append(id)
    
    for geohash in geohash2node:
        avg_lon, avg_lat = 0, 0
        n = len( geohash2node[geohash])
        for id in geohash2node[geohash]:
            lon, lat = node2coord[id]
            avg_lon += lon
            avg_lat += lat
        node2coord[geohash] = [avg_lon/n, avg_lat/n]
    return node2geohash, geohash2node

def build_graph(connections):
    graph = defaultdict(dict)
    for connection in connections:
        if connection['properties']['subtype']!="road":
            # print(connection['properties']['subtype'])
            continue
        nodes = connection['properties']['connectors']
        for node in nodes:
            neighbors = {}
            node_id = node['connector_id']
            for x in nodes:
                if x!=node:
                    neighbor = x["connector_id"]
                    dist = get_dist(neighbor, node_id)
                    if dist is None:
                        continue
                    neighbors[neighbor] =  dist
            graph[node_id].update(neighbors)
    # print(graph)
    return graph

def build_graph_rough(connections):
    graph = defaultdict(dict)
    for connection in connections:
        if connection['properties']['subtype']!="road":
            # print(connection['properties']['subtype'])
            continue
        nodes = connection['properties']['connectors']
        for node in nodes:
            neighbors = {}
            if node['connector_id'] not in node2geohash:
                continue
            node_id = node2geohash[node['connector_id']]
            for x in nodes:
                if x!=node:
                    if x["connector_id"] not in node2geohash:
                        continue
                    neighbor = node2geohash[x["connector_id"]]
                    dist = get_dist(neighbor, node_id)
                    if dist is None:
                        continue
                    neighbors[neighbor] = dist
            graph[node_id].update(neighbors)
    # print(graph)
    return graph

node2coord = {}

with open('./local_data/test_connector.geojson') as f:
    nodes = json.load(f)
    nodes = nodes['features']
    for node in nodes:
        coord = node['geometry']['coordinates']
        id = node['properties']['id']
        node2coord[id] = coord
node2geohash, geohash2node = consolidate_nodes(nodes)


# print(node2coord)
def get_dist(A,B):
    if A not in node2coord or B not in node2coord:
        return None
    lon, lat = node2coord[A]
    lon2, lat2 = node2coord[B]
    R = 6471
    dlat = radians(lat2 - lat)
    dlon = radians(lon2 - lon)

    a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    return distance

def get_nodes(line):
    coords = line['geometry']['coordinates']
    for i,j in coords:
        print(j,i)

with open("./local_data/test_segments.geojson") as f:
    data = json.load(f)
data = data['features']
graph = build_graph(data)
graph_rough = build_graph_rough(data)

start = '08f194ad32cc83ac046bb8349e64ca81'
print(node2coord[start][::-1])

end = '08f194ad32d1490a046bf9687066af0a'
print(node2coord[end][::-1])
path, path_len = run_djikstra(node2geohash[start], node2geohash[end], graph_rough)
paths = run_Astar(node2geohash[start], node2geohash[end], graph_rough, 5)
print(paths)
visualize_path(paths, node2coord)

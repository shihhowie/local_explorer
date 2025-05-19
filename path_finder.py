# map 
# sw: 51.515, -0.118 -> ws: -0.118,51.515
# ne: 51.527, -0.105 -> en: -0.105,51.527
# segments
# overturemaps download --bbox=-0.118,51.515,-0.105,51.527 -f geojson --type=segment -o test_segments.geojson
# connector 51.535, -0.102
# overturemaps download --bbox=-0.119,51.511,-0.102,51.535 -f geojson --type=connector -o test_connector.geojson
# overturemaps download --bbox=-0.118,51.515,-0.105,51.527 -f geojson --type=place -o test_places.geojson
import json
from collections import defaultdict
import heapq
# from map_util import visualize_paths
from numpy import random
import geohash2
from path import Path
from consts import *

from path_util import graph, node2coord, segment2coords, node2geohash, geohash2node
from path_util import get_node_dist, find_nearest_node


def run_Yens(start, end, k=3, n_subpaths=3):
    # run A* first
    paths = []
    subpaths = [set() for _ in range(n_subpaths)]
    graph_copy = graph.copy()
    # blocked_path = set()
    for i in range(k):
        if i==0:
            shortest_path = run_Astar(start, end)
            shortest_path_len = shortest_path.length

        paths.append(shortest_path)
        print("shortest_path_len", shortest_path.length, len(shortest_path.connections))
        subpath_len = shortest_path_len/n_subpaths
        print("subpath_len", subpath_len)
        # print("shortest_path", shortest_path)
        curr_path_len = 0
        
        subpath_idx = 0
        for con in shortest_path.connections:
            curr_path_len += con.distance
            if curr_path_len>=subpath_len:
                subpath_idx+=1
                curr_path_len = 0
            subpaths[subpath_idx].add((con.node1, con.node2))

        print("subpaths", len(subpaths)) 
        shortest_path_len = 1e6
        shortest_path = []
        for j in range(len(subpaths)):
            print(f"path {i}-{j}")
            subpath = subpaths[j]
            blocked_path = subpath
            # blocked_path = set()
            # for x in subpaths[j:]:
            #     blocked_path.update(x)
            # print("subpath: ", subpath)
            print("blocked_path", len(blocked_path))
            path = run_Astar(start, end, blocked_path=blocked_path)
            path_len = path.length
            paths.append(path)
            print("path_len", path_len)

            # print(f"path {i}-{j}", path_len, [p[1] for p in path])
            if path_len<shortest_path_len:
                shortest_path_len = path_len
                shortest_path = path
                print(f"new shortest path {i}-{j}")
            print("\n")

    # block certain segments

    return paths

def run_Astar(start, end, blocked_path=set()):
    i = 0
    heap = [(0,0,start,[])]
    path_len = {}
    while heap:
        dist_so_far, prev_heuristic, node, nodes = heapq.heappop(heap)
        if node in path_len:
            continue
        path_len[node] = dist_so_far
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connection in neighbors.items():
            dist, segment_id = connection
            if nb_id not in path_len:
                tmp = nodes.copy()
                tmp.append(nb_id)
                dist_remain = get_node_dist(nb_id, end)
                dist_so_far = dist_so_far + dist + dist_remain - prev_heuristic
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    dist_so_far += 1e3
                heapq.heappush(heap,(dist_so_far, dist_remain, nb_id, tmp))
        i += 1

    print("visited", i)

    path = Path(nodes)

    return path

def run_djikstra(start, end, blocked_path=set()):
    heap = [(0,start,[])]
    path_len = {}
    
    i = 0
    while heap:
        dist_so_far, node, nodes = heapq.heappop(heap)
        if node in path_len:
            continue
        path_len[node] = dist_so_far
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connection in neighbors.items():
            dist, segment_id = connection
            if nb_id not in path_len:
                tmp = nodes.copy()
                tmp.append(nb_id)
                dist_so_far += dist
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    dist_so_far += 1e3
                heapq.heappush(heap,(dist_so_far, nb_id, tmp))
        i += 1

    print("visited", i)
    path = Path(nodes)
    # print(path)
    # print(path_len[end])
    return path

def build_path(nodes):
    prev = None
    path = []
    for node in nodes:
        if prev:
            path.append((prev, node))
        prev = node
    return path

def find_places_along_path(nodes):
    places, geohash2place = get_places()
    place_ids = set()
    prev_node = None
    for node in nodes:
        if prev_node:
            start_coord, end_coord = node2coord[prev_node], node2coord[node]
            place_ids_, _ = find_places_between_points(start_coord, end_coord, geohash2place)
            place_ids.update(place_ids_)
        prev_node = node
    category_cnt = defaultdict(int)
    places_in_path = [places[x] for x in place_ids]
    # print(json.dumps(places_in_path, indent=2))
    for place_id in place_ids:
        place = places[place_id]
        for cat in place['categories']:
            category_cnt[cat]+=1
    top_cat = sorted(category_cnt, key=lambda x: category_cnt[x], reverse=True)
    return {cat: category_cnt[cat] for cat in top_cat[:10]}

def find_places_between_points(start_coord, end_coord, geohash2place):
    lon_d = abs(start_coord[0]-end_coord[0])
    lat_d = abs(start_coord[1]-end_coord[1])
    dist = max(lat_d, lon_d)
    # print("dist", dist)
    num_points = max(2,int(dist/0.0001)) # lat delta 0.000085, lon delta 0.00017
    nodes = interpolate_points(start_coord, end_coord, num_points)
    geohashes = set()
    place_ids = set()
    for lon, lat in nodes:
        node_geohash8 = geohash2.encode(lon, lat, precision=8)
        geohashes.add(node_geohash8)
        pids = geohash2place.get(node_geohash8, [])
        place_ids.update(pids)
    return place_ids, geohashes 

def enrich_segment(segments):
    # use geohash instead of coordinates
    # a segment is now represented by its geohashes
    places, geohash2place = get_places()
    segment2geohash = {}
    segment2feat = {}
    for segment in segments:
        segment_id = segment['properties']['id']
        path_coords = []
        if segment['properties']['subtype']!="road":
            # print(connection['properties']['subtype'])
            continue
        road_type = segment['properties']['class']
        connectors = segment['properties']['connectors']
        category_cnt = defaultdict(int)

        start = connectors[0]['connector_id']
        end = connectors[-1]['connector_id']
        if start not in node2coord or end not in node2coord or start==end:
            nodes = segment['geometry']['coordinates']
            start_coord, end_coord = nodes[0], nodes[1]
        else:
            start_coord, end_coord = node2coord[start], node2coord[end]
        
        place_ids, geohashes = find_places_between_points(start_coord, end_coord, geohash2place)

        for place_id in place_ids:
            place = places[place_id]
            for cat in place['categories']:
                category_cnt[cat]+=1
        segment2feat[segment_id] = {"place_ids": list(place_ids), 
                                    "categories": category_cnt,
                                    "road_type": road_type}
        segment2geohash[segment_id] = list(geohashes)
    # print(graph)
    return segment2geohash, segment2feat

# segment2geohash, segment2feat = enrich_segment(connections)

if __name__=="__main__":
    # graph_rough = build_graph_rough(data)

    start = '08f194ad32cc83ac046bb8349e64ca81'
    print(node2coord[start], node2coord[start][::-1])
    print(node2geohash[start])

    # segment = "088194ad32dfffff046f79810232bdc4"
    # segment = "08a194ad32c8ffff046bbfc029da92d5"
    # seg_geo = segment2geohash[segment]
    # print(",".join(seg_geo))
    # feats = segment2feat[segment]
    # top_cats = sorted(feats['categories'].items(), key=lambda x: x[1], reverse=True)[:10]
    # print(len(feats['place_ids']), top_cats)
    # print(feats['road_type'])

    end = '08f194ad32d1490a046bf9687066af0a'
    print(node2coord[end], node2coord[end][::-1])
    path = run_djikstra(start, end)
    path = run_Astar(start, end)
    paths = run_Yens(start, end, k=3)
    for i, p in enumerate(paths):
        print(p.get_path_nodes())
    print(paths[1])
    # places = path.get_places()
    # print(places)
    path.summarize()
    # for path in paths:
    #     nodes = [p[1] for p in path]
    #     path_places = find_places_along_path(nodes)
        # print("path", dist, path_places)
    # i, j = 0, 0
    # while i<len(paths[0])-1 or j<len(paths[1])-1:
    #     print(i, paths[0][i][1], paths[1][j][1])
    #     if i<len(paths[0])-1:
    #         i+=1 
    #     if j<len(paths[1])-1:
    #         j+=1
    # for i in range(len(paths)):
    #     print(f"path {i}")
    #     print([p[1] for p in paths[i]])
        
    # print("top 3 paths", paths)
    # print(paths)
    # visualize_paths(paths, node2coord)

    # print(geohash2node.keys())
    # node, dist = find_nearest_node(-0.118, 51.515, geohash2node, node2coord)
    # print(node, dist)

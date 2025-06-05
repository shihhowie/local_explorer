# map 
# sw: 51.515, -0.118 -> ws: -0.118,51.515
# ne: 51.527, -0.105 -> en: -0.105,51.527
# segments
# overturemaps download --bbox=-0.118,51.515,-0.105,51.527 -f geojson --type=segment -o test_segments.geojson
# connector 51.535, -0.102
# overturemaps download --bbox=-0.119,51.511,-0.102,51.535 -f geojson --type=connector -o test_connector.geojson
# overturemaps download --bbox=-0.118,51.515,-0.105,51.527 -f geojson --type=place -o test_places.geojson
# overturemaps download --bbox=-0.118,51.515,-0.0535,51.549 -f geojson --type=place -o test_places_EC.geojson


import json
from collections import defaultdict
import heapq
# from map_util import visualize_paths
from numpy import random
import geohash2
from path import Path
from consts import *
import plotly.graph_objects as go 

from path_util import node2coord, segment2coords, node2geohash, geohash2node, segment_info
from path_util import get_node_dist, find_nearest_node

from graph_util import graph
from map_util import visualize_paths

colors = ["blue", "red", "orange", "purple", "cyan", "magenta"]

def run_Yens(start, end, method="Astar", k=3, subpath_len=0.1):
    # run A* first
    paths = []
    candidate_paths = []
    graph_copy = graph.copy()
    path_selection_tracker = []
    for i in range(k):
        if i==0:
            if method=="Astar":
                shortest_path = run_Astar2(start, end)
            if method=="djikstra":
                shortest_path = run_djikstra2(start, end)
        else:
            prev_path = paths[i-1]
            diff, dist_diff = prev_path - shortest_path
            print(f"path diff by {diff} nodes, {dist_diff:.2f} km")
        shortest_path_len = shortest_path.length

        paths.append(shortest_path)
        print("shortest_path_len", shortest_path.length, len(shortest_path.connections))
        
        if shortest_path_len < subpath_len :
            continue
        print("subpath_len", subpath_len)
        # print("shortest_path", shortest_path)

        subpaths = [0]
        subpath_idx = 0

        curr_path_len = 0
        for con in shortest_path.connections:
            curr_path_len += con.distance
            if curr_path_len>subpath_len:
                # print("subpath", subpath_idx, curr_path_len)
                subpaths.append(0)
                subpath_idx+=1
                curr_path_len = 0
            subpaths[subpath_idx] += 1
        
        print("subpaths len", subpaths) 
        # shortest_path_len = 1e6
        
        # debug-------------------------
        fig = go.Figure()
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=51.515, lon=-0.118),
                zoom=14
            ),
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        for path in paths:
            path.gen_path_simple(fig, f"shortest path {i}-{path.length:.2f}", "green")
        # debug-------------------------

        n_subpaths = len(subpaths)
        root_idx = 0
        for j in range(n_subpaths):
            print(f"path {i}-{j}")

            root_path = Path(shortest_path.connections[:root_idx])
            root_path.gen_path_simple(fig, f"root subpath{i}-{j}-{root_path.length:.2f}", "blue")

            root_link = shortest_path.connections[root_idx]
            # print("root_link", root_link)

            spur_link = (root_link.node1, root_link.node2)

            # visualize_paths([subpath])
            blocked_path = set()
            
            for path in paths:
                shared_idx = path & root_path
                print("shared idx", shared_idx)
                blocked_len = 0
                idx = 0
                while blocked_len < subpath_len and shared_idx+idx < len(path.connections):
                    # print("blocked link", path.connections[shared_idx+1].ends)
                    blocked_path.add(path.connections[shared_idx+idx].ends)
                    blocked_len += path.connections[shared_idx+idx].distance
                    idx += 1

            print("blocked_path len", len(blocked_path))
            if method=="Astar":
                spur_path = run_Astar2(spur_link[0], end, blocked_path)
            if method=="djikstra":
                spur_path = run_djikstra2(spur_link[0], end, blocked_path)
            if spur_path:
                root_path.merge_path(spur_path)
                # print("new link", root_path.connections[j+1].ends)
                diff, dist_diff = path - root_path
                print(f"path diff by {diff} nodes, {dist_diff:.2f} km")
                path = root_path
                path_len = path.length
                spur_path.gen_path_simple(fig, f"new subpath{i}-{j}-{root_path.length:.2f}", "orange")

                heapq.heappush(candidate_paths, (path_len, i, j, path))
                # paths.append(path)
                # print("path_len", path_len)
            

            root_idx += subpaths[j]
        # if i==0:
        #     fig.show()
            # print(f"path {i}-{j}", path_len, [p[1] for p in path])
        path_len, i_, j_, shortest_path = heapq.heappop(candidate_paths)
        path_selection_tracker.append((i_, j_))
        print("select deviated path", (i_, j_), path_len)
        print("\n")
    # block certain segments
    print("selected deviations:", path_selection_tracker)
    return paths

def run_Astar(start, end, blocked_path=set()):
    i = 0
    heap = [(0,0,start,[])]
    path_len = {}
    while heap:
        dist_so_far,prev_heuristic, node, path = heapq.heappop(heap)
        if node in path_len:
            # print("node visited", dist_so_far, path_len[node])
            continue
        path_len[node] = dist_so_far
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connections in neighbors.items():
            shortest = 1e6
            connection = None
            for con in connections:
                # find shortest path from one node to its neighbors
                distance = con.distance
                # if segment_info[con.segment_id]["motor_vehicle"]:
                #     distance += 1e2
                if distance < shortest:
                    shortest = distance
                    connection = con
                
            if not connection:
                continue
            dist = connection.distance
            if nb_id not in path_len:
                tmp = path.copy()
                tmp.append(connection)
                dist_remain = get_node_dist(nb_id, end)
                dist_so_far = dist_so_far + dist + dist_remain - prev_heuristic
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    dist_so_far += 1e3
                heapq.heappush(heap,(dist_so_far, dist_remain, nb_id, tmp))
        i += 1
    if node!=end:
        return None
    print("visited", i)

    path = Path(path)

    return path


def run_Astar2(start, end, blocked_path=set()):
    i = 0
    heap = [(get_node_dist(start,end),start,[])]
    path_len = {start:0}
    visited = set()
    while heap:
        try:
            priority, node, path = heapq.heappop(heap)
        except Exception as e:
            counter = defaultdict(list)
            for x,y,_ in heap:
                counter[y].append(x)
            print(json.dumps(counter, indent=4))
            break
        i += 1
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connections in neighbors.items():
            if nb_id in visited:
                continue
            shortest = 1e6
            connection = None
            for con in connections:
                # find shortest path from one node to its neighbors
                distance = con.distance
                # if segment_info[con.segment_id]["motor_vehicle"]:
                #     distance += 0.1
                if segment_info[con.segment_id].get("underground"):
                    distance += 0.1
                if distance < shortest:
                    shortest = distance
                    connection = con
                
            if not connection:
                continue
            dist = shortest
            dist_so_far = dist + path_len[node]
            # if nb_id in path_len and dist_so_far<path_len[nb_id]:
            #     print(nb_id, path_len[nb_id], dist_so_far)

            if nb_id not in path_len or (dist_so_far+0.001) < path_len[nb_id]:
                path_len[nb_id] = dist_so_far
                tmp = path.copy()
                tmp.append(connection)
                dist_remain = get_node_dist(nb_id, end)
                priority = dist_so_far + dist_remain
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    priority += 0.2
                # print("priority",priority)
                heapq.heappush(heap,(priority, nb_id, tmp))
    if node!=end:
        return None

    print("visited", i)

    path = Path(path)

    return path

def run_djikstra(start, end, blocked_path=set()):
    path_len = {}
    
    i = 0
    heap = [(0,start,i,[])]

    while heap:
        dist_so_far, node, _, path = heapq.heappop(heap)
        if node in path_len:
            if dist_so_far<path_len[node]:
                print("node visited", dist_so_far, path_len[node])
            continue
        path_len[node] = dist_so_far
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connections in neighbors.items():
            shortest = 1e6
            connection = None
            for con in connections:
                # find shortest path from one node to its neighbors
                if con.distance < shortest:
                    shortest = con.distance
                    connection = con
            if not connection:
                continue
            dist = connection.distance
            if nb_id not in path_len:
                tmp = path.copy()
                tmp.append(connection)
                dist_so_far += dist
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    dist_so_far += 1e3
                heapq.heappush(heap,(dist_so_far, nb_id, i, tmp))
        i += 1
    if node!=end:
        return None

    print("visited", i)
    path = Path(path)
    # print(path)
    # print(path_len[end])
    return path

def run_djikstra2(start, end, blocked_path=set()):
    heap = [(0,start,[])]
    path_len = {start: 0}
    
    i = 0
    while heap:
        priority, node, path = heapq.heappop(heap)
        
        if node == end:
            break
        neighbors = graph[node]
        for nb_id, connections in neighbors.items():
            shortest = 1e6
            connection = None
            for con in connections:
                # find shortest path from one node to its neighbors
                if con.distance < shortest:
                    shortest = con.distance
                    connection = con
            if not connection:
                continue
            
            dist = connection.distance
            dist_so_far = path_len[node] + dist
            if nb_id not in path_len or dist_so_far<path_len[nb_id]:
                path_len[nb_id] = dist_so_far
                tmp = path.copy()
                tmp.append(connection)
                if (node, nb_id) in blocked_path or (nb_id, node) in blocked_path:
                    dist_so_far += 1e3
                heapq.heappush(heap,(dist_so_far, nb_id, tmp))
        i += 1

    print("visited", i)
    path = Path(path)
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
    print(path.length)
    path = run_djikstra2(start, end)
    print(path.length)
    path = run_Astar(start, end)
    print(path.length)
    path = run_Astar2(start, end)
    print(path.length)
    
    start, end = '08f194ad32cc83ac046bb8349e64ca81', '08f194ad32d1490a046bf9687066af0a'
    
    paths = run_Yens(start, end, "Astar", 2, 0.5)

    path = paths[0]
    path = path.to_json()
    path = Path.from_json(path)
    # for i, p in enumerate(paths):
    #     print(p.get_path_nodes())
    # print(paths[1])
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

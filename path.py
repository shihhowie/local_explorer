from path_util import graph, node2coord, segment2coords, node2geohash, geohash2node
from path_util import places, geohash2place
from path_util import get_node_dist, interpolate_points, get_neighbors
from collections import defaultdict

import geohash2

class Connection:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2
        self.coord1 = node2coord[node1]
        self.coord2 = node2coord[node2]
        distance, segment_id = graph[node1][node2]
        self.distance = distance
        self.segment_id = segment_id
        self.coords = []
        self.geohashes = set()
    
    def get_segment_nodes(self):
        # given two end points, and the segment id, find the nodes between the two points within that segment
        segment_nodes = segment2coords[self.segment_id]
        flag = False
        reverse = False
        contained_id = []

        for id, coord in segment_nodes:
            if id==self.node1 or id==self.node2:
                if not flag:
                    flag = True
                    if id==self.node2:
                        reverse=True
                else:
                    contained_id.append(id)
                    break
            if flag:
                contained_id.append(id)
        if reverse:
            contained_id = contained_id[::-1]
        return contained_id

    def interpolate(self):
        # return interpolated points within a connection
        lon_d = abs(self.coord1[0]-self.coord2[0])
        lat_d = abs(self.coord1[1]-self.coord2[1])
        dist = max(lat_d, lon_d)
        num_points = max(2,int(dist/0.0001))
        coords = interpolate_points(self.coord1, self.coord2, num_points)
        self.coords = coords
        return coords

    def get_geohashes(self):
        # get the geohashes that covers the connection
        if not self.coords:
            self.interpolate()
        geohashes = set()
        for lon, lat in self.coords:
            geohash8 = geohash2.encode(lon, lat, precision=8)
            geohashes.add(geohash8)
            neighbors = get_neighbors(geohash8)
            geohashes.add(neighbors['w'])
            geohashes.add(neighbors['e'])
        self.geohashes = geohashes
        return geohashes

    def get_places(self):
        if not self.geohashes:
            self.get_geohashes()
        place_ids = set()
        for node_geohash8 in self.geohashes:
            place_ids.update(geohash2place.get(node_geohash8, []))
        return place_ids

    

    

class Path:
    def __init__(self, path):
        # path should be a tuple of (node, segment_id)
        self.connections = []
        self.length = 0
        self.build_path(path)

    # def __len__(self):
    #     return len(self.connections)
    
    # def __repr__(self):
    #     return self.connections

    def build_path(self, nodes):
        prev_node = None
        for node in nodes:
            if prev_node is not None:
                connection = Connection(prev_node, node)
                self.connections.append(connection)
                self.length += connection.distance
            prev_node = node

    def get_path_nodes(self):
        nodes = []
        for con in self.connections:
            nodes += con.get_segment_nodes()
        return nodes
    
    def get_path_coords(self):
        nodes = self.get_path_nodes()
        coords = [node2coord[node] for node in nodes]
        return coords

    def get_geohashes(self):
        geohashes = set()
        for con in self.connections:
            geohashes.update(con.get_geohashes())
        return geohashes

    def get_places(self):
        place_ids = set()
        for con in self.connections:
            place_ids.update(con.get_places())
        return place_ids
    
    def get_place_coords(self):
        place_ids = self.get_places()
        coords = [places[x]['coord'] for x in place_ids]
        return coords

    def summarize(self):
        category_cnt = defaultdict(int)
        place_ids = self.get_places()
        for place_id in place_ids:
            place = places[place_id]
            for cat in place['categories']:
                category_cnt[cat]+=1
        top_cats = sorted(category_cnt, key=lambda x: x[1], reverse=True)[:5]
        cat_summary = ", ".join([f"{category_cnt[cat]} {cat.replace("_"," ")}s" for cat in top_cats])
        print(f"this path is {self.length:.2f} km long. along this path, there are {cat_summary}")
        
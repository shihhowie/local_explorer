from path_util import node2coord, segment2coords, node2geohash, geohash2node, segment_info
from path_util import places, geohash2place
from path_util import get_node_dist, interpolate_points, get_neighbors
from collections import defaultdict
import plotly.graph_objects as go 

import geohash2

class Connection:
    def __init__(self, node1, node2, segment_id):
        self.node1 = node1
        self.node2 = node2
        self.ends = (node1, node2)
        self.coord1 = node2coord[node1]
        self.coord2 = node2coord[node2]
        self.segment_id = segment_id
        self.distance = self.get_distance()
        self.coords = []
        self.geohashes = set()

    def to_json(self):
        return {"node1": self.node1, "node2": self.node2, "segment_id": self.segment_id}

    def __eq__(self, other):
        return (self.node1, self.node2) == (other.node1, other.node2)
    
    def get_distance(self):
        nodes = self.get_segment_nodes()
        prev = None
        dist = 0
        for node in nodes:
            if prev is not None:
                dist += get_node_dist(node, prev)
            prev = node
        return dist

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

    def add_to_fig(self, fig, name):
        nodes = self.get_segment_nodes()
        coords = [node2coord[node] for node in nodes]

        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]
        road_info = segment_info[self.segment_id]
        if road_info["foot"]:
            node_type = "foot"
        elif road_info["bicycle"]:
            node_type = "bicycle"
        else:
            node_type = "motor_vehicle"

        color_map = {
            "foot": "green",
            "bicycle": "blue",
            "motor_vehicle": "red"
        }

        fig.add_trace(go.Scattermap(
            lat=lats,
            lon=lons,
            mode="lines",
            hoverinfo='skip',
            line=dict(width=4, color=color_map[node_type]),
            opacity=0.8,
            
            # marker=dict(size=8, color="red"),
            name=f"Path {name}"
        ))

        fig.add_trace(go.Scattermap(
            lat=[lats[0],lats[-1]],
            lon=[lons[0],lons[-1]],
            mode="markers",
            hoverinfo='text',
            marker=dict(size=4, color="white"),
            opacity=0.8,
            text=f'seg {name}: {self.distance:.2f}km',
            # marker=dict(size=8, color="red"),
            name=f"Path {name}"
        ))
        

class Path:
    def __init__(self, connections):
        # path should be a tuple of (node, segment_id)
        self.connections = []
        self.length = 0
        self.add_path(connections)

    @classmethod
    def from_json(cls, json):
        connections = []
        for item in json:
            con = Connection(item["node1"], item["node2"], item["segment_id"])
            connections.append(con)
        return cls(connections)

    def to_json(self):
        rsp = []
        for con in self.connections:
            rsp.append(con.to_json())
        return rsp

    def __and__(self, other):
        i = 0
        shared_roots = []
        while i<len(self.connections) and i<len(other.connections):
            if self.connections[i]==other.connections[i]:
                i+=1
            else:
                break
        return i

    def __sub__(self, other):
        # return nodes in self not in other
        nodes_seq1 = self.get_path_nodes()
        nodes_seq2 = other.get_path_nodes()

        m,n = len(nodes_seq1)+1, len(nodes_seq2)+1
        diff = [[None] * m for _ in range(n)]
        dist = [[0]* m for _ in range(n)]
        for i in range(n):
            for j in range(m):
                if i==0 and j==0:
                    diff[i][j] = 0
                    dist[i][j] = 0
                elif i==0:
                    diff[i][j] = j
                    dist[i][j] = dist[i][j-1]+get_node_dist(nodes_seq1[max(j-1,0)], nodes_seq1[max(j-2,0)])
                elif j==0:
                    diff[i][j] = i
                    dist[i][j] = 0
                else:
                    if nodes_seq1[j-1]==nodes_seq2[i-1]:
                        diff[i][j] = diff[i-1][j-1]
                        dist[i][j] = dist[i-1][j-1]
                    else:
                        diff[i][j] = min(diff[i-1][j], diff[i][j-1], diff[i-1][j-1])+1
                        seq1_len = get_node_dist(nodes_seq1[max(j-1,0)], nodes_seq1[max(j-2,0)])
                        dist[i][j] = min(dist[i-1][j], dist[i][j-1], dist[i-1][j-1])+seq1_len
        # print(dist[10])
        return diff[n-1][m-1], dist[n-1][m-1]

    def get_segments_ids(self):
        segment_ids = [con.segment_id for con in self.connections]
        return segment_ids 

    def add_path(self, connections):
        for connection in connections:
            self.connections.append(connection)
            self.length += connection.distance

    def merge_path(self, path):
        for connection in path.connections:
            self.connections.append(connection)
            self.length += connection.distance

    def get_path_nodes(self):
        nodes = []
        for con in self.connections:
            nodes += con.get_segment_nodes()
        return nodes
    
    def get_path_coords(self):
        nodes = self.get_path_nodes()
        coords = [node2coord[node] for node in nodes]
        return coords

    def gen_path_simple(self, fig, name, color="red"):
        coords = self.get_path_coords()
        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]
        fig.add_trace(go.Scattermap(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=4, color=color),
            opacity=0.8,
            # marker=dict(size=8, color="red"),
            name=f"Path {name}"
        ))

    def gen_path(self, fig, name):
        for i, con in enumerate(self.connections):
            con.add_to_fig(fig, f"{name}-{i}")

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

    def get_top_cat(self, k=5):
        category_cnt = defaultdict(int)
        place_ids = self.get_places()
        for place_id in place_ids:
            place = places[place_id]
            for cat in place['categories']:
                category_cnt[cat]+=1
        top_cats = sorted(category_cnt, key=lambda x: category_cnt[x], reverse=True)[:k]
        top_cats = {x: category_cnt[x] for x in top_cats}
        # print(top_cats)
        return top_cats

    def summarize(self):
        road_type_len = defaultdict(float)
        for i, con in enumerate(self.connections):
            road_info = segment_info[con.segment_id]
            if road_info["foot"]:
                road_type_len["foot"] += con.distance
            elif road_info["bicycle"]:
                road_type_len["bicycle"] += con.distance
            else:
                road_type_len["motor vehicle"] += con.distance
        
        road_condition = ", ".join([f"{len:.2f} km of which are for {road} traffic" for road, len in road_type_len.items()])
        top_cats = self.get_top_cat(5)
        cat_summary = ", ".join([f"{cnt} {cat.replace("_"," ")}s" for cat, cnt in top_cats.items()])
        summary = f"This path is {self.length:.2f} km long, {road_condition}.\n"
        summary += f"Along this path, there are {cat_summary}.\n"
        return summary

    
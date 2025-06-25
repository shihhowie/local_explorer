from collections import defaultdict
from path_util import process_road_info, get_dist, load_connections
from path_util import node2coord

from path import Connection

def build_graph(segments):
    graph = {}
    for segment_id, nodes in segments.items():
        for node_id in nodes:
            graph[node_id] = graph.get(node_id, defaultdict(list))
            if node_id not in node2coord:
                continue
            for neighbor in nodes:
                if neighbor!=node_id:
                    if neighbor not in node2coord:
                        continue
                    connection = Connection(node_id, neighbor, segment_id)
                    graph[node_id][neighbor].append(connection)
    # print(graph)
    return graph

def consolidate_segments(segments):
    # for connectors that are only along one path, and not connected to any other paths
    # we can ignore them
    node2segment = defaultdict(list)
    segment2node = defaultdict(list)
    for segment in segments:
        if segment['properties']['subtype']!="road":
            # print(segment['properties']['subtype'])
            continue
        nodes = segment['properties']['connectors']
        segment_id = segment['properties']['id']
        for node in nodes:
            node_id = node["connector_id"]
            node2segment[node_id].append(segment_id)
            segment2node[segment_id].append(node_id)
    valid_nodes = [node for node, seg_list in node2segment.items() if len(seg_list) > 1]
    consolidated_segments = defaultdict(list)
    for node in valid_nodes:
        segment_ids = node2segment[node]
        for segment_id in segment_ids:
            consolidated_segments[segment_id].append(node)
    return consolidated_segments, segment2node

segments = load_connections()
segments_compact, segments = consolidate_segments(segments)
graph = build_graph(segments_compact)
full_graph = build_graph(segments)
import dash
from dash import dcc, html, Input, Output, State
from dash.dependencies import ALL
import plotly.graph_objects as go 
from path_util import find_nearest_node
from path_finder import run_Astar, run_Yens
import geohash2

app = dash.Dash(__name__)

def create_default_map():
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
            center=dict(lat=51.515, lon=-0.118),
            zoom=14
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    # print("Default Map")
    return fig

app.layout = html.Div([
    # html.H1("Interactive Path Visualizer", style={"textAlign": "center"}),

    # Search bar for segment ID
    html.Div([
        html.Div([
            html.H3("Search Segments and Connectors", style={"textAlign": "center"}),
            html.Div([
                dcc.Input(
                    id="segment-id-input",
                    type="text",
                    placeholder="Enter Segment ID",
                    style={"width": "200px", "margin-right": "5px"}
                ),
                html.Button("Search", id="search-segment-button", n_clicks=0),
            ], style={"display": "flex", "alignItems": "center", "margin-bottom": "10px"}),
            html.Div([
                dcc.Input(
                    id="connector-id-input",
                    type="text",
                    placeholder="Enter Connector ID",
                    style={"width": "200px", "margin-right": "5px"}
                ),
                html.Button("Search", id="search-connector-button", n_clicks=0),
            ], style={"display": "flex", "alignItems": "center", "margin-bottom": "10px"}),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"}),
        html.Div([
            html.H3("Search Geohash", style={"textAlign": "center"}),
            html.Div([
                dcc.Input(
                    id="geohash-id-input",
                    type="text",
                    placeholder="Enter Geohash ID",
                    style={"width": "200px", "margin-right": "5px"}
                ),
                html.Button("Search", id="search-geohash-button", n_clicks=0),
            ], style={"display": "flex", "alignItems": "center", "margin-bottom": "10px"}),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"}),
        html.Div([
            html.H3("Find Path", style={"textAlign": "center"}),
            html.Div([
                dcc.Input(
                    id="start-coord-input",
                    type="text",
                    placeholder="Enter Start (lon, lat)",
                    style={"width": "150px", "margin-right": "10px"}
                ),
                dcc.Input(
                    id="finish-coord-input",
                    type="text",
                    placeholder="Enter Finish (lon, lat)",
                    style={"width": "150px"}
                )
            ], style={"display": "flex", "alignItems": "center", "margin-bottom": "10px"}),
            html.Div([
                html.Button("Search", id="find-path-button", n_clicks=0)
            ]),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"})
    ], style={"display": "flex", "justifyContent": "space-around", "margin-bottom": "20px"}),
    dcc.Store(id="current-map", data=create_default_map().to_plotly_json()),
    html.Div([
        dcc.Graph(id="map-visualization",
            figure=create_default_map(),
            style={"height": "80vh", "width": "80%"}
        ),
        html.Div(
            id="path-panel",
            children=[
                html.Button("X", id="close-path-panel-button", n_clicks=0, 
                    style={"position": "absolute",
                            "top": "5px",
                            "right": "5px",
                            "border": "none",
                            "text-align": "center",
                            "cursor": "pointer",}),
                html.H3("Path Details", style={"textAlign": "left"}),
                html.Div(id="path-legends", style={"textAlign": "left"}),
            ],
            style={"display":"none", 
                    "border": "1px solid #ccc", 
                    "padding": "10px", 
                    "margin-right": "10px", 
                    "width": "20%", 
                    "position": "relative"}
        )
        ], style={"display": "flex", "alignItems": "flex-start"}
    ),
    # Map visualization
    dcc.Store(id="path-panel-state", data=False),
    dcc.Store(id="path-data", data={}),
    dcc.Store(id="geohash-grid-state", data={}),
    dcc.Store(id="places-show-state", data={}),
    dcc.Store(id="show-path-state", data={})
])

@app.callback(
    [
        Output("map-visualization", "figure"),
        Output("path-panel", "style"),
        Output("path-legends", "children"),
        Output("path-data", "data"),
        Output("current-map", "data"),
        Output("path-panel-state", "data"),
        Output("geohash-grid-state", "data"),
        Output("places-show-state", "data"),
        Output("show-path-state", "data")
    ],
    [
        Input("find-path-button", "n_clicks"),
        Input("search-segment-button", "n_clicks"),
        Input("search-connector-button", "n_clicks"),
        Input("search-geohash-button", "n_clicks"),
        Input({"type": "show-geohash-button", "index": ALL}, "n_clicks"),
        Input({"type": "show-places-button", "index": ALL}, "n_clicks"),
        Input("close-path-panel-button", "n_clicks"),
        Input({"type": "show-path-button", "index": ALL}, "n_clicks"),
    ],
    [
        State("start-coord-input", "value"),
        State("finish-coord-input", "value"),
        State("segment-id-input", "value"),
        State("connector-id-input", "value"),
        State("geohash-id-input", "value"),
        State("path-data", "data"),
        State("current-map", "data"),
        State("path-panel-state", "data"),
        State("geohash-grid-state", "data"),
        State("places-show-state", "data"),
        State("show-path-state", "data")
    ]
)
def update_map_and_panel(find_path_clicks, segment_clicks, connector_clicks, 
                        geohash_clicks, geohash_button_clicks, place_button_clicks,
                        close_panel_clicks, show_path_click, start_coord, finish_coord, segment_id, 
                        connector_id, geohashes, path_data, current_map, 
                        path_panel_state, geohash_grid_state, places_show_state, show_path_state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return create_default_map(), \
                {"display": "none"},  \
                "No paths available", \
                {}, \
                create_default_map().to_plotly_json(), \
                path_panel_state, \
                geohash_grid_state, \
                places_show_state, \
                show_path_state

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("triggered_id:",triggered_id)
    fig = go.Figure(current_map) if current_map else create_default_map()
    panel_style = {"display": "none"}
    legend_items = "No paths available"

    if geohash_grid_state is None:
        geohash_grid_state = {}
    if places_show_state is None:
        places_show_state = {}
    if show_path_state is None:
        show_path_state = defaultdict(dict)

    if triggered_id == "find-path-button":
        fig, paths = find_shortest_paths(start_coord, finish_coord)
        path_data = paths
        # print(path_data)
        path_panel_state = True
    elif triggered_id == "close-path-panel-button":
        path_panel_state = False
        panel_style = {"display": "none"}
        fig = create_default_map()
    elif triggered_id == "search-segment-button":
        fig = show_segment(segment_id)
    elif triggered_id == "search-connector-button":
        fig = show_connector(connector_id)
    elif triggered_id=="search-geohash-button":
        fig = show_geohash(geohashes)
    elif "show-geohash-button" in triggered_id:
        path_id = eval(triggered_id)["index"]
        # print("path_data", path_data)
        
        if geohash_grid_state.get(str(path_id), False):
            geohash_grid_state[str(path_id)] = False
            fig.data = [trace for trace in fig.data if trace.name != f"geohashes {path_id}"]
        else:
            geohashes = path_data[str(path_id)]["geohashes"]
            get_geohash_corners(fig, geohashes, path_id)
            geohash_grid_state[str(path_id)] = True
    elif "show-places-button" in triggered_id:
        path_id = eval(triggered_id)["index"]
        # print("path_data", path_data)
        if places_show_state.get(str(path_id), False):
            places_show_state[str(path_id)] = False
            fig.data = [trace for trace in fig.data if trace.name != f"places on {path_id}"]
        else:
            places_show_state[str(path_id)] = True
            place_ids = path_data[str(path_id)]["place_ids"]
            show_places(fig, place_ids, path_id)
    elif "show-path-button" in triggered_id:
        path_id = eval(triggered_id)["index"]
        # print("path_data", path_data)
        if str(path_id) not in show_path_state:
            show_path_state[str(path_id)] = {"show": True}
        if show_path_state[str(path_id)]["show"]:
            show_path_state[str(path_id)]["show"] = False
            if show_path_state[str(path_id)].get("saved_state") is None:
                show_path_state[str(path_id)]["saved_state"] = [trace for trace in fig.data if trace.name == f"Path {path_id}"]
            fig.data = [trace for trace in fig.data if trace.name is None or trace.name.find(str(path_id))==-1]
        else:
            show_path_state[str(path_id)]["show"] = True
            for trace in show_path_state[str(path_id)]["saved_state"]:
                fig.add_trace(go.Scattermap(**trace) )
            

    if path_panel_state:
        panel_style = {"display": "block", 
                        # "border": "1px solid #ccc", 
                        "padding": "10px", 
                        # "margin-top": "20px",
                        "margin-left": "5px",
                        "position": "relative"}
        legend_items = show_path_panel(path_data) 
    fig.update_layout(
        showlegend=False
    )
    # print(fig.to_plotly_json())
    return fig, \
            panel_style, \
            legend_items, \
            path_data, \
            fig.to_plotly_json(), \
            path_panel_state, \
            geohash_grid_state, \
            places_show_state, \
            show_path_state

def show_path_panel(path_data):
    legend_items = []
    for path_id, path_info in path_data.items():
        legend_items.append(html.Div([
            html.Button(
                id={"type": "show-path-button", "index": path_id},
                style={"display": "inline-block", 
                        "background-color": path_info['color'], 
                        "width": "5px", 
                        "height": "10px",
                        "margin-right": "10px",
                        "cursor": "pointer",
                        "border": "none",},
                        n_clicks=0,
                        ),
            html.Span(f"Path {path_id}: {path_info["length"]:.2f} km", style={"margin-right": "10px"}),
            html.Button(f"Geohash", id={"type": "show-geohash-button", "index": path_id}, n_clicks=0),
            html.Button(f"Places", id={"type": "show-places-button", "index": path_id}, n_clicks=0),
        ], style={"margin-bottom": "5px", "position": "relative"}))
    return legend_items

def show_segment(segment_id):
    # Create a new figure
    if not show_segment:
        return create_default_map()

    fig = go.Figure()
    # Check if the segment ID exists
    if segment_id in segment2coords:
        coords = segment2coords[segment_id]
        lats = [coord[1] for node_id, coord in coords]
        lons = [coord[0] for node_id, coord in coords]

        # Add the selected segment to the map
        fig.add_trace(go.Scattermap(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=4, color="red"),
            name=f"Segment {segment_id}"
        ))
        # Center the map on the segment
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=14
            )
        )
    else:
        # If the segment ID is not found, display a message
        fig = create_default_map()
        fig.add_annotation(
            text="Segment ID not found",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20),
            xref="paper", yref="paper"
        )
    # Set map layout
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    return fig


def show_connector(connector_id):
    # Create a new figure
    if not connector_id:
        return create_default_map()
    # print("show connector ", connector_id)
    fig = go.Figure()

    # Check if the segment ID exists
    if connector_id in node2coord:
        coords = [node2coord[connector_id]]
        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]

        # Add the selected segment to the map
        fig.add_trace(go.Scattermap(
            lat=lats,
            lon=lons,
            mode="markers+text",
            marker=dict(size=8, color="red"),
            name=f"Node {connector_id}"
        ))
        # Center the map on the segment
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=14
            )
        )
    else:
        # If the segment ID is not found, display a message
        fig = create_default_map()
        print("connector id not found")
        fig.add_annotation(
            text="Connector ID not found",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20),
            xref="paper", yref="paper"
        )
    # Set map layout
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    return fig


def find_shortest_paths(start_coord='x', finish_coord='x'):
    # Create a new figure
    fig = create_default_map()

    # Check if start and finish coordinates are provided
    if not start_coord or not finish_coord:
        return fig
    colors = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'pink', 'brown', 'gray']
    path_data = {}
    try:
        # Parse the input coordinates
        if start_coord=='x' or finish_coord=='x':
            start_lon, start_lat = -0.1154402, 51.515024
            finish_lon, finish_lat = -0.1141136, 51.5225289
        else:
            start_lon, start_lat = map(float, start_coord.split(","))
            finish_lon, finish_lat = map(float, finish_coord.split(","))

        # Find the nearest nodes to the start and finish coordinates
        start_node, _ = find_nearest_node(start_lon, start_lat, geohash2node, node2coord)
        finish_node, _ = find_nearest_node(finish_lon, finish_lat, geohash2node, node2coord)
        
        start_lon, start_lat = node2coord[start_node]
        finish_lon, finish_lat = node2coord[finish_node]
        
        print(start_node,finish_node)
        # Find the shortest path using A* algorithm
        # path, path_len = run_Astar(start_node, finish_node, graph)
        paths = run_Yens(start_node, finish_node, 1)
        print("ran Yens")
        for j, path in enumerate(paths):
            path_len = path.length
            print("path length", path_len)
            path_coords = path.get_path_coords()
            node_ids = path.get_path_nodes()
            # geohashes = path.get_geohashes()
            print(f"show path {j}")
            # print("places", path.get_places())
            # get_geohash_corners(fig, geohashes)
            # for geohash in geohashes:
            #     get_geohash_corners(fig, geohash)
            lats = [coord[1] for coord in path_coords]+[finish_lat]
            lons = [coord[0] for coord in path_coords]+[finish_lon]

            # print(lats, lons)
            # print(f"path {j}", node_ids)
            # Add the path to the map
            fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines",
                hoverinfo='skip',
                line=dict(width=4, color=colors[j]),
                # marker=dict(size=8, color="red"),
                name=f"Path {j}"
            ))

            # fig.add_trace(go.Scattermap(
            #     lat=lats,
            #     lon=lons,
            #     mode="markers",
            #     line=dict(width=4, color=colors[j]),
            #     text=node_ids,
            #     # marker=dict(size=8, color="red"),
            # ))
            path_data[j] = {
                "length": path_len,
                "color": colors[j],
                "geohashes": list(path.get_geohashes()),
                "place_ids": list(path.get_places())
            }

        fig.add_trace(go.Scattermap(
            lat=[start_lat, finish_lat],
            lon=[start_lon, finish_lon],
            mode="markers+text",
            marker=dict(symbol="star"),
            text=["start", "end"],
            name=f"End point",
        ))
        # Center the map on the start point
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=start_lat, lon=start_lon),
                zoom=14
            )
        )
    except Exception as e:
        # Handle errors (e.g., invalid input or no path found)
        print(f"Error: {e}")
        fig.add_annotation(
            text="Error: Could not find path. Check inputs.",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20),
            xref="paper", yref="paper"
        )

    return fig, path_data

def show_geohash(geohashes):
    fig = create_default_map()
    geohashes = geohashes.split(",")
    get_geohash_corners(fig, geohashes)
    
    return fig

def get_geohash_corners(fig, geohashes, idx=0):
    lats = []
    lons = []
    geohashes = sorted(geohashes)
    for geohash in geohashes:
        try:
            lat, lon, elat, elon = geohash2.decode_exactly(geohash)
        except Exception as e:
            print(f"Error: {e}")
            fig.add_annotation(
                text=f"Error: Could not find geohash {geohash}. Check inputs.",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20),
                xref="paper", yref="paper"
            )
            return fig

        sw = (lat-elat, lon-elon)
        ne = (lat+elat, lon+elon)
        nw = (lat+elat, lon-elon)
        se = (lat-elat, lon+elon)
        corners  = [sw, nw, ne, se, sw]
        # print(corners)
        lats += [float(corner[1]) for corner in corners]+[None]
        lons += [float(corner[0]) for corner in corners]+[None]
    fig.add_trace(go.Scattermap(
        lat=lats,
        lon=lons,
        mode="lines",
        line=dict(width=1, color="blue"),
        name=f"geohashes {idx}",
        showlegend=False
        )
    )

def show_places(fig, place_ids, idx=0):
    coords = [places[x]['coord'] for x in place_ids]
    names = [places[x]['name'] for x in place_ids]
    # print(names)
    lats = [coord[1] for coord in coords]
    lons = [coord[0] for coord in coords]
    fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="markers",
                text=names,
                name=f"places on {idx}"
                # marker=dict(size=8, color="red"),
            ))
    

from path_util import graph, segment2coords, node2geohash, geohash2node, node2coord
from path_util import places

if __name__=="__main__":
    app.run(debug=True)
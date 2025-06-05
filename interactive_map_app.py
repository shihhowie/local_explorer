import dash
from dash import dcc, html, Input, Output, State
from dash.dependencies import ALL, MATCH
from dash_extensions import EventListener

import plotly.graph_objects as go 
from path_util import find_nearest_node
import requests

from collections import defaultdict
import re
import geohash2
from path import Path

app = dash.Dash(__name__)
 
path_cache = {}

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

app.layout = html.Div([
    # html.H1("Interactive Path Visualizer", style={"textAlign": "center"}),

    # Search bar for segment ID
    html.Div([
        dcc.Graph(id="map-visualization",
            figure=create_default_map(),
            style={"height": "100vh", 
                    "width": "100%",
                    "position": "absolute",
                    "top": "0",
                    "left": "0",
                    "z-index": "1"}
        ),
        EventListener(
            id="location-listener",
            events=[{"event": "geolocation", "props": ["coords.latitude", "coords.longitude"]}],
            children=[],
        ),
        html.Div([
            html.Div(
                id = "search-overlay",
                children=[
                    html.Div([
                        html.H3("Search Segments and Connectors", style={"textAlign": "center"}),
                        html.Div([
                            dcc.Input(
                                id="segment-id-input",
                                type="text",
                                placeholder="Enter Segment ID",
                                style={"width": "150px", "margin-right": "5px"}
                            ),
                            html.Button("Search", id="search-segment-button", n_clicks=0),
                        ], style={"display": "flex", "alignItems": "center", "margin-bottom": "10px"}),
                        html.Div([
                            dcc.Input(
                                id="connector-id-input",
                                type="text",
                                placeholder="Enter Connector ID",
                                style={"width": "150px", "margin-right": "5px"}
                            ),
                            html.Button("Search", id="search-connector-button", n_clicks=0),
                        ], style={"display": "flex", "alignItems": "center", "margin-bottom": "5px"}),
                    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"}),
                    html.Div([
                        html.H3("Search Geohash", style={"textAlign": "center"}),
                        html.Div([
                            dcc.Input(
                                id="geohash-id-input",
                                type="text",
                                placeholder="Enter Geohash ID",
                                style={"width": "150px", "margin-right": "5px"}
                            ),
                            html.Button("Search", id="search-geohash-button", n_clicks=0),
                        ], style={"display": "flex", "alignItems": "center", "margin-bottom": "5px"}),
                    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"}),
                    html.Div([
                        html.H3("Find Path", style={"textAlign": "center"}),
                        dcc.Input(
                            id="start-coord-input",
                            type="text",
                            placeholder="Enter Start (lon, lat)",
                            style={"width": "150px",  "margin-bottom": "10px"}
                        ),
                        dcc.Input(
                            id="finish-coord-input",
                            type="text",
                            placeholder="Enter Finish (lon, lat)",
                            style={"width": "150px", "margin-bottom": "10px"}
                        ),
                        html.Div([
                            html.Button("Search", id="find-path-button", n_clicks=0)
                        ]),
                    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "flex": "1"})
                ], style={"position": "absolute",  # Position the search buttons as an overlay
                        "top": "10px",  # Adjust the position from the top
                        "left": "10px",  # Adjust the position from the left
                        "background-color": "rgba(0, 0, 0, 0.7)",  # Semi-transparent background
                        "padding": "10px",
                        "border-radius": "10px",
                        "height": "50vh",
                        "width": "15%",
                        "z-index": "2",  # Place the search buttons above the map
                        "color": "white",  # Text color for better visibility}),
                },
            ),
            html.Div(
                id="path-panel",
                children=[
                    html.Button("X", id="close-path-panel-button", n_clicks=0, 
                        style={"position": "absolute",
                                "top": "5px",
                                "right": "5px",
                                "text-align": "center",
                                "cursor": "pointer",}),
                    html.H3("Path Details", style={"textAlign": "center"}),
                    html.Div(id="path-legends", style={"textAlign": "center"}),
                ],
                style={"display":"none", 
                        "border": "1px solid #ccc", 
                        "top": "45px",
                        "left": "10px",
                        "padding": "10px", 
                        "margin-right": "10px", 
                        "width": "20%", 
                        # "height": "100%",
                        "position": "absolute"}
                )
        ])
    ]),
    html.Div(
        id="path-detail-modal",
        children=[
            html.Div(
                id="path-detail-content",
                children=[
                    html.Button("X", id="close-detail-button", n_clicks=0, 
                        style={ "position": "absolute",
                            "float": "right",
                                "top": "5px",
                                "right": "5px",
                                "text-align": "center",
                                "cursor": "pointer",}),
                    html.H3("Path Detail", style={"textAlign": "center"}),
                    html.Div(id="summary-text", style={"padding": "10px", "whiteSpace": "pre-wrap"}),
                    html.Div(id="categories-section", style={"padding": "10px", "whatSpace": "pre-wrap"}),
                    html.Div(
                        children=[
                            html.Button(f"Geohash", id="show-geohash-button", n_clicks=0 ,style={"margin-right": "5px"}),
                            html.Button(f"Places", id="show-places-button", n_clicks=0),
                    ], style={"padding": "10px"})
                    
                ]
            )
        ],
        style={
            "display": "none",  # Initially hidden
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "20%",
            "height": "100%",
            "background-color": "white",
            "z-index": "1000",
            "justify-content": "center",
            "align-items": "center",
            "overflow-y": "auto",
        },
    ),
    dcc.Tooltip(id="hover-tooltip"),
    # Map visualization
    dcc.Store(id="current-map", data=create_default_map().to_plotly_json()),
    dcc.Store(id="paths-panel-state", data={}),
    dcc.Store(id="path-data", data={}),
    dcc.Store(id="geohash-grid-state", data=defaultdict(bool)),
    dcc.Store(id="show-place-state", data=defaultdict(bool)),
    dcc.Store(id="show-path-state", data={}),
    dcc.Store(id="show-segment-state", data={}),
    dcc.Store(id="show-cat-place-state", data={}),
    dcc.Store(id="path-detail-state", data={"visible": False, "text": ""}),
    dcc.Store(id="highlight-place-state", data={}),
    dcc.Store(id="user-location", data=None)
])

@app.callback(
    [
        Output("path-data", "data"),
        Output("paths-panel-state", "data"),
        Output("geohash-grid-state", "data"),
        Output("show-place-state", "data"),
        Output("show-path-state", "data"),
        Output("path-detail-state", "data"),
        Output("show-segment-state", "data"),
    ],
    [
        Input("find-path-button", "n_clicks"),
        Input("search-segment-button", "n_clicks"),
        Input("search-connector-button", "n_clicks"),
        Input("search-geohash-button", "n_clicks"),
        Input("show-geohash-button", "n_clicks"),
        Input("show-places-button", "n_clicks"),
        Input("close-path-panel-button", "n_clicks"),
        Input({"type": "show-path-button", "index": ALL}, "n_clicks"),
        Input({"type": "path-detail-button", "index": ALL}, "n_clicks"),
        Input("close-detail-button", "n_clicks"),
    ],
    [
        State("start-coord-input", "value"),
        State("finish-coord-input", "value"),
        State("segment-id-input", "value"),
        State("connector-id-input", "value"),
        State("geohash-id-input", "value"),
        State("path-data", "data"),
        State("paths-panel-state", "data"),
        State("geohash-grid-state", "data"),
        State("show-place-state", "data"),
        State("show-path-state", "data"),
        State("path-detail-state", "data"),
        State("show-segment-state", "data")
    ]
)
def update_states(find_path_clicks, segment_clicks, connector_clicks, 
                        geohash_clicks, geohash_button_clicks, place_button_clicks,
                        close_panel_clicks, show_path_click, path_detail_clicks, close_path_detail_clicks,
                        start_coord, finish_coord, segment_id, connector_id, geohashes, path_data, 
                        paths_panel_state, geohash_grid_state, show_places_state, show_path_state,
                        path_detail_state, show_segment_state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return  ( path_data, 
                paths_panel_state, 
                geohash_grid_state, 
                show_places_state, 
                show_path_state, 
                path_detail_state,
                show_segment_state)

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("triggered_id:",triggered_id)

    if triggered_id == "find-path-button":
        if not start_coord and not finish_coord:
            start_coord, finish_coord = "x", "x"
        fig, path_data = find_shortest_paths(start_coord, finish_coord)
        paths_panel_state = {"show": True, "fig": fig.to_plotly_json()}
    elif triggered_id == "close-path-panel-button":
        paths_panel_state = {"show": False}
    elif triggered_id == "search-segment-button":
        show_segment_state["segment_id"] = segment_id
    elif triggered_id == "search-connector-button":
        fig = show_connector(connector_id)
    elif triggered_id=="search-geohash-button":
        fig = show_geohash(geohashes)
    elif "show-geohash-button" in triggered_id:
        path_id = path_detail_state["path_id"]
        geohash_grid_state[path_id] = not geohash_grid_state.get(path_id)
    elif "show-places-button" in triggered_id:
        path_id = path_detail_state["path_id"]
        show_places_state[path_id] = not show_places_state.get(path_id)
    elif "show-path-button" in triggered_id:
        path_id = str(eval(triggered_id)["index"])
        show_path_state[path_id] = not show_path_state.get(path_id, True)
    elif "path-detail-button" in triggered_id:
        fig = go.Figure(paths_panel_state["fig"])
        path_id = str(eval(triggered_id)["index"])
        path_detail_state = {"visible": True, "path_id": path_id}
    elif "close-detail-button" in triggered_id:
        path_detail_state = {"visible": False}

    return  (
            path_data, 
            paths_panel_state, 
            geohash_grid_state, 
            show_places_state, 
            show_path_state, 
            path_detail_state,
            show_segment_state)


@app.callback(
    Output("map-visualization", "figure"),
    [Input("paths-panel-state", "data"),
     Input("geohash-grid-state", "data"),
     Input("show-place-state", "data"),
     Input("show-path-state", "data"),
     Input("path-detail-state", "data"),
     Input("show-cat-place-state", "data"),
     Input("highlight-place-state", "data"),
     Input("show-segment-state", "data"),
     Input("user-location", "data")],
    [State("path-data", "data")]
)
def update_map(paths_panel_state, geohash_grid_state, show_place_state, 
                show_path_state, path_detail_state, show_cat_place_state,
                highlight_place_state, show_segment_state, user_location, path_data):
    print("update_map")
    # print(map_state)

    print("paths_panel_state", paths_panel_state.get("show"))
    # retrieved paths
    if paths_panel_state.get("show", False):
        fig = go.Figure(paths_panel_state["fig"])
    else:
        if path_data:
            start_lat, start_lon = path_data["0"]["center"]
            fig = create_default_map(start_lat, start_lon)
        else: 
            if user_location is None:
                fig = create_default_map()
            else:
                print("location")
                lat, lon = user_location["lat"], user_location["lon"] 
                fig = create_default_map
        if show_segment_state.get("segment_id"):
            fig = show_segment(show_segment_state["segment_id"])

    hide_paths_ids = [f"{p}" for p in show_path_state if not show_path_state[p]]
    print("hide_paths_ids", hide_paths_ids)
    # fig.data = [trace for trace in fig.data if trace.name not in hide_paths_ids]
   
    print("path_detail_state", path_detail_state)
    if not path_detail_state["visible"]:
        fig.data = [trace for trace in fig.data if trace.name is None or not
                                                any(re.search(p, trace.name) for p in hide_paths_ids)]
    else:
        path_id = path_detail_state["path_id"]
        fig.data = [trace for trace in fig.data if trace.name == f"Path {path_id}"]
        path = path_cache[path_id]
        path.gen_path(fig, path_id)

    if path_detail_state["visible"]:
        print("geohash_grid_state", geohash_grid_state)
        if geohash_grid_state.get(path_id, False):
            geohashes = path_data[path_id]["geohashes"]
            color = path_data[path_id]['color']
            get_geohash_corners(fig, geohashes, path_id, color)

        print("show_place_state", show_place_state)
        if show_place_state.get(path_id, False):
            place_ids = path_data[path_id]["place_ids"]
            color = path_data[path_id]['color']
            show_places(fig, place_ids, path_id, color)

        print("show_cat_place_state", show_cat_place_state.keys())
        if show_cat_place_state.get(path_id, False):
            place_ids = show_cat_place_state[path_id]
            color = path_data[path_id]['color']
            show_places(fig, place_ids, f"{path_id} cat", color)

            if highlight_place_state.get("place_id") is not None:
                place_id = highlight_place_state["place_id"]
                highlight_place(fig, place_id, color)
    
    print("show figs", set([trace.name for trace in fig.data]))
    for trace in fig.data:
        if not trace.lat or not trace.lon:
            print(f"Empty trace: {trace.name}")
    return fig


@app.callback(
    [Output("path-detail-modal", "style"),
     Output("summary-text", "children"),
     Output("categories-section", "children")],
    [Input("path-detail-state", "data")],
    [State("path-data", "data")]
)
def show_path_detail_modal(path_detail_state, path_data):    
    # print("toggle_path_detail_modal triggered", path_detail_state["visible"])
    style = {"display": "none"}
    summary = ""
    categories_items = []
    if path_detail_state["visible"]:
        path_id = path_detail_state["path_id"]
        summary_text = path_data[path_id]["summary"]
        place_ids = path_data[path_id]["place_ids"]

        style = {"display": "flex", 
            "position": "absolute", 
            "top": "10px", 
            "left": "10px", 
            "width": "20%", 
            "height": "80%",
            "background-color": "white",
            "overflow-y": "auto",
            "min-height": "80vh",
            "height": "auto",
            "z-index": "3"}
        summary = summary_text
        
        top_cats = path_data[path_id]["top_cats"]
        for idx, cat in enumerate(top_cats):
            categories_items.append(html.Div([
                html.Button([
                    html.Span(f"{cat.replace("_", " ")}", style={"flex": "1", "text-align": "left"}),
                    html.Span("+", id={"type": "cat-expand", "index": cat}, 
                            style={"text-align": "right",
                                    "font-size": "14px"}) 
                    ],
                    id={"type": "categories-button", "index": cat}, n_clicks=0,
                    style={"width": "100%",
                        "padding": "15px", 
                        "cursor": "pointer",
                        "display": "flex",
                        "justify-content": "space-between",
                        "background-color": "rgba(0, 0, 0, 0.01)",
                        "border": "none",
                        "align-items": "center"}),
                html.Div(
                    id={"type": "category-content", "index": cat},
                    children=[],
                    style={"display": "none", "padding-left": "20px",
                            "border": "1px solid #ccc",
                            "overflow-y": "auto",
                            "background-color": "rgba(0, 0, 0, 0.01)"}
                )
            ], 
            id={"type": "category-container", "index": cat},  
            style={"margin-bottom": "5px", 
                   "border": "1px solid #ccc",
                   "background-color": "rgba(0, 0, 0, 0.01)",
                   "overflow": "hidden"}))
        
    return style, summary, categories_items

@app.callback(
    [Output("path-panel", "style"), Output("path-legends", "children")],
    [Input("paths-panel-state", "data")],
    [State("path-data", "data")]
)
def show_path_panel(paths_panel_state, path_data):
    panel_style = {"display": "none"}
    legend_items = []
    if paths_panel_state.get("show", False):
        panel_style = {"position": "absolute",  # Position the search buttons as an overlay
                    "top": "calc(20px + 50vh + 20px)",  # Adjust the position from the top
                    "left": "10px",  # Adjust the position from the left
                    "background-color": "rgba(0, 0, 0, 0.7)",  # Semi-transparent background
                    "padding": "10px",
                    "border-radius": "10px",
                    "width": "15%",
                    "z-index": "2",  # Place the search buttons above the map
                    "color": "white",  # Text color for better visibility}),
            }
        for path_id, path_info in path_data.items():
            legend_items.append(html.Div([
                html.Button(
                    id={"type": "show-path-button", "index": path_id},
                    style={"display": "inline-block", 
                            "background-color": path_info['color'], 
                            "width": "5px", 
                            "height": "10px",
                            "margin-right": "5px",
                            "cursor": "pointer",
                            "border": "none",},
                            n_clicks=0,
                            ),
                html.Span(f"{path_info["length"]:.2f} km", style={"margin-right": "5px"}),
                html.Button(f"Path Detail", id={"type": "path-detail-button", "index": path_id}, n_clicks=0)
            ], 
            style={"margin-bottom": "5px", "position": "relative"}))
    
    return panel_style, legend_items

@app.callback(Output("show-cat-place-state", "data"),
            [Input({"type": "categories-button", "index": ALL}, "n_clicks")],
            [
                State("path-detail-state", "data"),
                State("path-data", "data"),
                State("show-cat-place-state", "data")
            ],
)
def show_category_places(n_clicks_list, path_detail_state, path_data, show_cat_place_state):
    print("show_category_places", n_clicks_list)

    ctx = dash.callback_context
    if not ctx.triggered or sum(n_clicks_list)==0:
        return show_cat_place_state

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("triggered_id:", triggered_id)

    # Extract the category and path ID
    # cat = eval(triggered_id)["index"]
    path_id = path_detail_state["path_id"]
    cats = list(path_data[path_id]["top_cats"].keys())
    place_ids = []
    for idx, n_clicks in enumerate(n_clicks_list):
        if n_clicks%2==0:
            continue
        cat = cats[idx]
        place_ids += [p for p in path_data[path_id]["place_ids"] if cat in places[p].get("categories", [])]

    show_cat_place_state[path_id] = place_ids
    return show_cat_place_state


@app.callback(
    [Output({"type": "category-content", "index": MATCH}, "children"),
    Output({"type": "category-content", "index": MATCH}, "style"),
    Output({"type": "cat-expand", "index": MATCH}, "children")
    ],
    [Input({"type": "categories-button", "index": MATCH}, "n_clicks")],
    [State("path-detail-state", "data"), 
     State("path-data", "data"),
     State("show-cat-place-state", "data")]
)
def toggle_category_content(n_clicks, path_detail_state, path_data, show_cat_place_state):
    print("toggle_category_content", n_clicks)
    if n_clicks%2==0:
        expand_sign = "+"
    else:
        expand_sign = "-"

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(triggered_id)
    if not triggered_id or n_clicks%2==0:
        return [], {"display": "none"}, expand_sign
    cat = eval(triggered_id)["index"]
    path_id = path_detail_state["path_id"]
    place_ids = path_data[path_id]["place_ids"]

    place_names = {
        place_id: places[place_id]["name"].replace("_", " ") 
        for place_id in place_ids
        if cat in places[place_id].get("categories", [])
    }

    place_items = []
    for place_id, name in place_names.items():
        place_items.append(html.Button(name, 
                id={"type": "place-button", "index": place_id},
                style={"padding": "5px 0", "font-size": "12px", 
                        "cursor": "pointer", "width": "100%",
                        "background-color": "none",
                        "padding": "10px",
                        "border": "none", "textAlign": "left"}))
    style = {"display": "block", "padding-left": "20px", "overflow-y": "auto", "max-height": "200px"}
    return place_items, style, expand_sign

@app.callback(
    Output("highlight-place-state", "data"),
    [Input({"type": "place-button", "index": ALL}, "n_clicks")],
    State("highlight-place-state", "data")
)
def highlight_place_on_map(n_clicks_list, highlighted_place):
    ctx = dash.callback_context
    print("place clicks", n_clicks_list)
    if not ctx.triggered:
        return {}
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if not triggered_id:
        return {}
    print("highlight_place_on_map", triggered_id)
    place_id = eval(triggered_id)["index"]
    # print([button_id["id"]["index"] for button_id in ctx.inputs_list[0]])
    button_idx = [button_id["id"]["index"] for button_id in ctx.inputs_list[0]].index(place_id)
    print("button_idx", button_idx)
    if n_clicks_list[button_idx] is not None and n_clicks_list[button_idx] > 0:
        print("highlited place id", place_id)
        highlighted_place["place_id"] = place_id
    return highlighted_place


def show_segment(segment_id):
    # Create a new figure
    if not show_segment:
        return create_default_map()

    fig = go.Figure()
    road_info = segment_info[segment_id]
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
            line=dict(width=4, color=color_map[node_type]),
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
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False
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
            ),
            showlegend=False
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
        url = "http://127.0.0.1:9997/find_paths"

        params = {
            "start": f"{start_node}",
            "end": f"{finish_node}",
            "subpath_len": 0.4
        }
        response = requests.get(url, params=params)
        paths = []
        if response.status_code == 200:
            data = response.json()
            for path in data["paths"]:
                paths.append(Path.from_json(path))
        else:
            raise RuntimeError(f"failed to fetch pthats: {response.status_code} - {response.text}")
        # paths = run_Yens(start_node, finish_node, "Astar", 5, 0.3)
        # paths = run_Yens(start_node, finish_node, "djikstra", 1, 3)
        print("ran Yens")
        for j, path in enumerate(paths):
            path_len = path.length
            print("path length", path_len)
            path_coords = path.get_path_coords()
            # print(f"show path {j}")
            # print(path.get_segments_ids())
            # print(f"show noes {j}")
            # print(path.get_path_nodes())
            lats = [coord[1] for coord in path_coords]+[finish_lat]
            lons = [coord[0] for coord in path_coords]+[finish_lon]

            # print(lats, lons)
            # print(f"path {j}", node_ids)
            # Add the path to the map
            # print("add path")
            fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines",
                hoverinfo='skip',
                line=dict(width=4, color=colors[j]),
                opacity=0.8,
                # marker=dict(size=8, color="red"),
                name=f"Path {j}"
            ))
            # path.gen_path(fig, j)

            path_data[j] = {
                "length": path_len,
                "color": colors[j],
                "geohashes": list(path.get_geohashes()),
                "place_ids": list(path.get_places()),
                "summary": path.summarize(),
                "center": [start_lat, start_lon],
                "top_cats": path.get_top_cat()
            }
            path_cache[str(j)] = path
            
        fig.add_trace(go.Scattermap(
            lat=[start_lat, finish_lat],
            lon=[start_lon, finish_lon],
            mode="markers+text",
            marker=dict(color="black", size=12),
            hoverinfo="skip",
            name=f"End point",
        ))
        
        fig.add_trace(go.Scattermap(
            lat=[start_lat, finish_lat],
            lon=[start_lon, finish_lon],
            mode="markers",
            marker=dict(color="white", size=9),
            text=["start", "end"],
            hoverinfo="text",
            name=f"End point",
        ))
        
        # Center the map on the start point
        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=start_lat, lon=start_lon),
                zoom=14
            ),
            showlegend=False
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

@app.callback(
    Output("user-location", "data"),
    [Input("location-listener", "event")]
)
def update_user_location(event):
    print("update user location")
    if event is None:
        return None
    lat = event["coords.latitude"]
    lon = even["coords.longitude"]
    return {"lat": lat, "lon": lon}

def show_geohash(geohashes):
    fig = create_default_map()
    geohashes = geohashes.split(",")
    get_geohash_corners(fig, geohashes)
    
    return fig

def get_geohash_corners(fig, geohashes, idx=0, color='blue'):
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
        line=dict(width=1, color=color),
        name=f"geohashes {idx}",
        showlegend=False
        )
    )

def show_places(fig, place_ids, idx=0, color='blue'):
    coords = [places[x]['coord'] for x in place_ids]
    names = [places[x]['name'] for x in place_ids]
    print(", ".join(names))
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

def highlight_place(fig, place_id, color):
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
        textfont=dict(color=color),
        textposition="top right",
        name="highlited place",
        showlegend=False
    ))

from path_util import segment2coords, node2geohash, geohash2node, node2coord, segment_info
from path_util import places

if __name__=="__main__":
    app.run(debug=True)
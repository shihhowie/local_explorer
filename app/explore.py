from dash import html, dcc, Output, Input, State

import sys
import os
import dash

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from map_util import create_default_map, draw_circle, show_places, highlight_place
from place_retriever import get_places, find_similar_places
from profile import profile_explore_button_style

explore_layout = html.Div([
    dcc.Graph(id="map-visualization-explore",
        figure=create_default_map(),
        style={"height": "100vh", 
                "width": "100%",
                "position": "absolute",
                "top": "0",
                "left": "0"}
    ),
    html.Div([
        html.H3("Explore Page", style={"textAlign": "center"}),
        html.H4("Find similar places", style={"textAlign": "center"}),
        dcc.Input(id="radius-input-explore", placeholder="Enter radius (km)", style={"width": "120px", "margin-bottom": "5px"}),
        html.Button("Search", id="search-radius-button", n_clicks=0),
        html.Br(),
        dcc.Input(id="place-input", placeholder="Place name", style={"width": "120px", "margin-bottom": "5px"}),
        html.Button("Search", id="find-similar-button", n_clicks=0),
        html.Br(),
        dcc.Link("Go to Home Page", href="/"),
    ], style={"position": "absolute",
                "top": "50px",
                "left": "50px",
                "background-color": "rgba(255, 255, 255, 0.9)",
                "padding": "10px",
                "border-radius": "10px",
                "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                "z-index": "2",
                "width": "300px",
                "textAlign": "center"}),
    html.Div(
        id="shop-names-panel-explore",
        children=[ html.H3("Coffee Shops Nearby:", style={"textAlign": "center", "margin-bottom": "10px", "z-index": "2"}),
          html.Div(
            id="shop-names-list-explore",
            children=[],
            style={
                "position": "relative",
                "background-color": "rgba(255, 255, 255, 0.9)",
                "padding": "10px",
                "border-radius": "10px",
                "z-index": "2",
                "width": "280px",
                "textAlign": "center",
                "overflow-y": "auto",  # Scrollable content
                "max-height": "200px",
            })
        ], style={
            "position": "absolute",
            "top": "250px",
            "left": "50px",
            "width": "300px",
            "background-color": "rgba(255, 255, 255, 0.9)",
            "padding": "10px",
            "border-radius": "10px",
            "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
            "z-index": "2",
            "textAlign": "center",
            "display": "none"})
    ])


def explore_callbacks(app):
    @app.callback(
        Output("map-visualization-explore", "figure"),
        [Input("explore-state-explore", "data"),
        Input("highlight-place-state", "data")],
        [State("user-location", "data")]
    )
    def update_map_explore(explore_state, highlight_place_state, user_location):
        print("callback update_map_explore")
        lat, lon = user_location["lat"], user_location["lon"]
        fig = create_default_map(lat, lon)
        print(explore_state)
        if explore_state.get("show"):    
            radius_km = explore_state["radius"]
            draw_circle(fig, lat, lon, radius_km)
            places = explore_state["places"]
            place_ids = [x['id'] for x in places]
            print(len(place_ids))
            show_places(fig, place_ids, "places in area", color="red")
            if highlight_place_state.get("place_id"):
                place_id = highlight_place_state["place_id"]
                highlight_place(fig, place_id, "blue")
        return fig


    @app.callback(
        Output("explore-state-explore", "data"),
        [Input("search-radius-button", "n_clicks"),
         Input("find-similar-button", "n_clicks")],
        [State("place-input", "value"),
         State("radius-input-explore", "value"),
         State("explore-state-explore", "data"),
         State("user-location", "data"),
         State("place-input", "value")]
    )
    def update_search(radius_clicks, find_place_clicks, query_place, radius, explore_state, user_location, place_input):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        lat, lon = user_location["lat"], user_location["lon"]
        places = []
        if radius_clicks > 0 and radius is not None:
            explore_state["radius"] = float(radius)
            explore_state["show"] = True
            places = get_places((lat, lon), explore_state["radius"])
            explore_state["places"] = places
        
        if triggered_id=="find-similar-button" and find_place_clicks>0:
            print("find-similar-button")
            if not places:
                places = get_places((lat, lon))
            places = {x['id']: x for x in places}
            filtered_ids = places.keys()
            similar_place_ids = find_similar_places(query_place, filtered_ids)
            similar_places = [places[x[1]] for x in similar_place_ids if x[1] in places]
            explore_state["places"] = similar_places

        return explore_state

    @app.callback(
       [ Output("shop-names-list-explore", "children"),
        Output("shop-names-list-explore", "style"),
        Output("shop-names-panel-explore", "style")],
        [Input("explore-state-explore", "data")],
        [State("shop-names-panel-explore", "style"),
        State("shop-names-list-explore", "style")]
    )
    def show_place_panel(explore_state, shop_name_panel_style, shop_name_list_style):
        print("callback: show_place_panel explore page")
        children = []
        # style = {"display": "none"}

        # profile_overlay_top = int(profile_overlay_style.get("top", "50px").replace("px", ""))

        if explore_state.get("show"):  
            places = explore_state["places"] 
            children = []
            children += [html.Div([
                            html.Button(x['name'], 
                            id={"type": "place-detail-button", "index": x['id']},
                            style=profile_explore_button_style),
                            html.Div(
                                id={"type": "place-detail-content", "index": x["id"]},
                                children=[],
                                style={"display": "none", "padding-left": "20px"}
                            )]) for x in places]
            shop_name_list_style["display"] = "block"
            shop_name_panel_style["display"] = "block"
        else:
            shop_name_list_style["display"] = "none"
            shop_name_panel_style["display"] = "none"

        return children, shop_name_list_style, shop_name_panel_style
    
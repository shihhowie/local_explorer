from dash import html, dcc, Output, Input, State
from dash.dependencies import ALL, MATCH
import dash
from pymongo import MongoClient
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from map_util import create_default_map 
from place_retriever import get_places

client = MongoClient("mongodb://localhost:27017/")
db = client.localexplorer
user_profiles = db.user_profiles
places_details = db.places

profile_layout = html.Div([
    html.H1("Create New Profile", style={"textAlign": "center"}),
    html.Div([
        dcc.Graph(id="map-visualization",
            figure=create_default_map(),
            style={"height": "100vh", 
                    "width": "100%",
                    "position": "absolute",
                    "top": "0",
                    "left": "0"}
        ),
        html.Div(
            id="profile-overlay",
            children=[
                html.Div(children=[], id="username-display", style={"textAlign": "center"}),
                html.Div(
                    id="profile-panel",
                    children=[],
                    style={
                        "display": "none",  # Initially hidden,
                        "background-color": "rgba(50, 50, 50, 0.1)",
                        "border-radius": "10px",
                        "overflow-y": "auto",
                        "max-height": "100px",
                        "padding": "20px",
                    }
                ),
                html.H3("Select some coffee shops you like", style={"textAlign": "center"}),
                dcc.Input(
                    id="radius-input",
                    type="text",
                    placeholder="radius (km)",
                    style={"width": "200px", "margin-bottom": "10px"}
                ),
                html.Button("Search", id="search-nearby-button", n_clicks=0),
                html.Br(),
                dcc.Link("Go to Home Page", href="/"),
                html.Br(),
                dcc.Link("Go to Explore Page", href="/explore"),
            ],
            style={
                "position": "absolute",
                "top": "50px",
                "left": "50px",
                "background-color": "rgba(255, 255, 255, 0.9)",
                "padding": "20px",
                "border-radius": "10px",
                "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                "z-index": "2",
                "width": "300px",
                "textAlign": "center"
            }           
            ),
        html.Div(
            id="shop-names-panel",
            children=[],
            style={
                "position": "absolute",
                "top": "300px",
                "left": "50px",
                "background-color": "rgba(255, 255, 255, 0.9)",
                "padding": "20px",
                "border-radius": "10px",
                "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                "z-index": "2",
                "width": "300px",
                "textAlign": "center",
                "overflow-y": "auto",
                "max-height": "200px",
                "display": "none"
            }
        ),
        
    ], style={"textAlign": "center"})
])

profile_explore_style = {
              # Make it visible
        }

profile_explore_button_style = {"textAlign": "center",
                                "width": "100%",
                                "border": "none",
                                "margin-bottom": "5px",
                                "border-radius": "5px",
                                "padding": "5px"}


def register_profile_callbacks(app):
    @app.callback(
        Output("username-display", "children"),
        Input("session-user", "data"))
    def show_username(session_user):
        print("callback: show_username")
        if session_user.get("username"):
            return [html.H3(f"Welcome {session_user["username"]}")]
        else:   
            return [html.H3(f"Welcome")]

    @app.callback(
        [Output("profile-panel", "children"),
        Output("profile-panel", "style")],
        [Input("session-user", "data")],
        State("profile-panel", "style"),
        
    )
    def show_profile(session_user, profile_panel_style):
        print("callback: show_profile")
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

        show = False
        # if triggered_id=="close-modal-button" and close_clicks > 0:
        #     show = True 
        # if triggered_id == "save-profile-button" and save_clicks>0:
        #     show = True

        if not session_user.get("username"):
            profile_panel_style["display"] = "none"
            return [], profile_panel_style
        username = session_user["username"]
        user_profile = user_profiles.find_one({"username": username})
        places = user_profile.get("places", [])
        children = [html.H3("Places liked by user", style={"textAlign": "center", "margin": "5px"})]
        for place_id in places:
            place = places_details.find_one({"id": place_id})
            name = place["name"]
            children.append(html.P(name, style={"textAlign": "left", "margin": "2px"}))
        profile_panel_style["display"] = "block"
        profile_panel_style["padding"] = "10px"
        return children, profile_panel_style

    @app.callback(
       Output({"type": "add-place", "index": MATCH}, "children"),
        [Input({"type": "add-place-button", "index": MATCH}, "n_clicks")],
        [State("session-user", "data"),
         State("explore-state", "data")]
    )
    def add_place_to_profile(n_clicks, session_user, explore_state):
        print("callback: add_place_to_profile")
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if not triggered_id or n_clicks%2==0:
            return "Add"

        if not session_user.get("username"):
            return "Missing username"
        
        place_id = eval(triggered_id)["index"]
        username = session_user["username"]
        user_profile = user_profiles.find_one({"username": username})
        if user_profile:
            if place_id not in user_profile.get("places", []):
                user_profiles.update_one(
                    {"username": username},
                    {"$push": {"places": place_id}}
                )
        else:
            user_profiles.insert_one({
                "username": username,
                "places": [place_id]
            })
        return "Added"

    @app.callback(
        Output("explore-state", "data"),
        [Input("search-nearby-button", "n_clicks")],
        [State("radius-input", "value"),
            State("explore-state", "data"),
        State("user-location", "data")]
    )
    def update_nearby_radius(n_clicks, radius, explore_state, user_location):
        lat, lon = user_location["lat"], user_location["lon"]
        if n_clicks > 0 and radius is not None:
            explore_state["radius"] = float(radius)
            explore_state["show"] = True
            places = get_places((lat, lon), explore_state["radius"])
            explore_state["places"] = places
        return explore_state

    @app.callback(
       [ Output("shop-names-panel", "children"),
        Output("shop-names-panel", "style")],
        [Input("explore-state", "data"),
        Input("profile-overlay", "style"),
        Input("profile-panel", "children"),
        Input("profile-panel", "style")],
        [State("shop-names-panel", "style")]
    )
    def show_place_panel(explore_state, profile_overlay_style, profile_panel, profile_panel_style, shope_name_style):
        print("callback: show_place_panel")
        children = []
        # style = {"display": "none"}

        # profile_overlay_top = int(profile_overlay_style.get("top", "50px").replace("px", ""))
        profile_overlay_height = int(profile_overlay_style.get("height", "300px").replace("px", ""))
        profile_panel_show = int(profile_panel_style["display"]!="none")
        profile_panel_height = 60*(len(profile_panel)>1)*profile_panel_show + 40*profile_panel_show
        shop_names_panel_top = profile_overlay_height + profile_panel_height + 10

        print("profile_panel_height", profile_panel_height, len(profile_panel))
        print(profile_panel)
        print("shop_names_panel_top", shop_names_panel_top)

        if explore_state.get("show"):  
            places = explore_state["places"] 
            children = [html.H3("Coffee Shops Nearby:", style={"textAlign": "center"})]
            children += [html.Div([
                            html.Button(x['name'], 
                            id={"type": "place-detail-button", "index": x['id']},
                            style=profile_explore_button_style),
                            html.Div(
                                id={"type": "place-detail-content", "index": x["id"]},
                                children=[],
                                style={"display": "none", "padding-left": "20px"}
                            )]) for x in places]
            shope_name_style["display"] = "block"
            shope_name_style["top"] = f"{shop_names_panel_top}px"
        else:
            shope_name_style["display"] = "none"
        return children, shope_name_style

    @app.callback(
        [Output({"type": "place-detail-content", "index": MATCH}, "children"),
        Output({"type": "place-detail-content", "index": MATCH}, "style")
        ],
        [Input({"type": "place-detail-button", "index": MATCH}, "n_clicks")],
        [State("explore-state", "data")]
    )
    def toggle_place_content(n_clicks, explore_state):
        # print("toggle_category_content", n_clicks)
        
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        # print(triggered_id)
        if not triggered_id or n_clicks%2==0:
            return [], {"display": "none"}

        place_id = eval(triggered_id)["index"]

        place_details = [html.Button(
                    html.Span("Add", id={"type": "add-place", "index": place_id}), 
                    id={"type": "add-place-button", "index": place_id},
                    style={"font-size": "12px", 
                            "cursor": "pointer", 
                            "padding": "5px",
                             "textAlign": "center"})]
        style = {"display": "block", "padding": "10px",
                "border": "1px solid #ccc",
                "background-color": "rgba(0, 0, 0, 0.01)"}
        return place_details, style


    @app.callback(
        Output("highlight-place-state", "data"),
        [Input({"type": "place-detail-button", "index": ALL}, "n_clicks")],
        [State("explore-state", "data"),
         State("highlight-place-state", "data")]
    )
    def highlight_place_on_map(n_clicks_list, explore_state, highlight_place_state):
        ctx = dash.callback_context
        # print("place clicks", n_clicks_list)
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
            # print("highlited place id", place_id)
            highlight_place_state["place_id"] = place_id
        else:
            highlight_place_state = {}
        return highlight_place_state



    

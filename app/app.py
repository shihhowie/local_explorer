import dash
from dash import dcc, html, Input, Output, State
from home import home_layout, register_home_callbacks
from explore import explore_layout, explore_callbacks
from routing import path_layout
from profile import profile_layout, register_profile_callbacks, profile_explore_button_style, profile_explore_style
from map_util import draw_circle, create_default_map, show_places, highlight_place
from place_retriever import get_places

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Local Explorer"

# Shared layout with URL routing
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Store(id="explore-state", data={}),
    dcc.Store(id="explore-state-explore", data={}),
    dcc.Store(id="user-location", data={"lat": 51.515, "lon":-0.118}),
    dcc.Store(id="highlight-place-state", data={}),
    dcc.Store(id="session-user", data={}),
    dcc.Store(id="username-exists-state", data={}),
])

@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    print("path", pathname)
    if pathname == "/explore":
        return explore_layout
    elif pathname == "/path":
        return path_layout
    elif pathname =="/profile":
        return profile_layout
    else:
        return home_layout  # Default to Home Page

@app.callback(
    Output("map-visualization", "figure"),
    [Input("explore-state", "data"),
    Input("highlight-place-state", "data")],
    [State("user-location", "data")]
)
def update_map(explore_state, highlight_place_state, user_location):
    lat, lon = user_location["lat"], user_location["lon"]
    fig = create_default_map(lat, lon)
    
    if explore_state.get("show"):    
        radius_km = explore_state["radius"]
        draw_circle(fig, lat, lon, radius_km)
        places = explore_state["places"]
        place_ids = [x['id'] for x in places]
        show_places(fig, place_ids, "places in area")
        if highlight_place_state.get("place_id"):
            place_id = highlight_place_state["place_id"]
            highlight_place(fig, place_id, "blue")
    return fig



register_profile_callbacks(app)
register_home_callbacks(app)
explore_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
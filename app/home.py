from dash import html, dcc, Input, Output, State
import dash

from pymongo import MongoClient


home_layout = html.Div([
    html.H1("Home Page", style={"textAlign": "center"}),
    html.Div([
        html.Div([
            html.H3("Enter your username:", style={"textAlign": "center"}),
            dcc.Input(id="username-input", type="text", placeholder="Username", style={"width": "200px"}),
            html.Button(
                html.Span("Submit", id="save-username"), id="save-profile-button", n_clicks=0),
        ], style={"textAlign": "center", "margin-bottom": "50px"}),
        dcc.Link("Go to Explore Page", href="/explore"),
        html.Br(),
        dcc.Link("Go to Path Page", href="/path"),
        html.Div(
        id="username-exists-panel",
        children=[
            html.Div([
                html.H3("Username doesn't exist! creating new profile", style={"textAlign": "center"}),
                html.Button("X", id="close-modal-button", n_clicks=0, 
                            style={"position": "absolute",
                                    "top": "15px",
                                    "right": "15px",})
            ], style={
                "background-color": "white",
                "padding": "20px",
                "border-radius": "5px",
                "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                "textAlign": "center"
            }),
        ], style={
                "position": "fixed",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "background-color": "rgba(0, 0, 0, 0.5)",
                "padding": "10px",
                "border-radius": "10px",
                "z-index": "1000",
                "display": "none"  # Show modal
                }
        )
    ], style={"textAlign": "center"})
    
])

client = MongoClient("mongodb://localhost:27017/")
db = client.localexplorer
user_profiles = db.user_profiles
    
def register_home_callbacks(app):
    @app.callback(
        Output("username-exists-panel", "style"),
        [Input("username-exists-state", "data")],
        State("username-exists-panel", "style"),
    )
    def display_username_exist_panel(username_exists_state, current_style):
        print("callback: display_username_exist_panel")
        print("username_exists_state",username_exists_state)
        if username_exists_state.get("show"):
             current_style["display"] = "block"  # Show modal
        else:
            current_style["display"] = "none"
        return current_style

    @app.callback(
        Output("url", "pathname"),
        Input("session-user", "data")
    )
    def navigate_to_profile_page(session_user):
        print("callback: navigate_to_profile_page")
        print("session_user", session_user)
        if session_user.get("username"):
            return "/profile"
        else:
            return "/"

    @app.callback(
        [Output("session-user", "data"), 
         Output("save-username", "children"),
         Output("username-exists-state", "data")
        ],
        [
         Input("save-profile-button", "n_clicks"),
         Input("close-modal-button", "n_clicks")
        ],
        [State("username-input", "value"),
        State("session-user", "data"),
        State("username-exists-state", "data")]
    )
    def register_user(n_clicks, close_clicks, username, session_user, username_exists_state):
        print("callback: register_user")
        save_status = "Submit"
        modal_style = {"display": "none"}
        print("session_user", session_user)
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        print("triggered_id:",triggered_id)
        print("username", username)
        # print("close clicks", close_clicks)

        if triggered_id=="close-modal-button" and close_clicks and close_clicks > 0:
            username_exists_state["show"] = False
            session_user["username"] = username
        print("username", username)

        if triggered_id=="save-profile-button": 
            if username is not None:
                session_user["username"] = username
                exist_user = user_profiles.find_one({"username": username})
                save_status = "Submitted"
                if not exist_user:
                    username_exists_state["show"] = True
                    return session_user, save_status, username_exists_state

                user_profiles.insert_one({
                    "username": username,
                    "places": []
                })
        print("session_user", session_user)
        return session_user, save_status, username_exists_state


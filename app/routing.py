from dash import html, dcc

path_layout = html.Div([
    html.H1("Path Page", style={"textAlign": "center"}),
    html.Div([
        dcc.Input(id="start-coord-input", placeholder="Enter Start (lon, lat)", style={"width": "150px"}),
        dcc.Input(id="finish-coord-input", placeholder="Enter Finish (lon, lat)", style={"width": "150px"}),
        html.Button("Find Path", id="find-path-button", n_clicks=0),
        html.Br(),
        dcc.Link("Go to Home Page", href="/"),
    ], style={"textAlign": "center"})
])
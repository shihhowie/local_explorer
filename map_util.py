import plotly.graph_objects as go 

def visualize_path(paths, node2coord):
    # Create a scatter plot for nodes
    node_lats = []
    node_lons = []
    edge_lats = []
    edge_lons = []

    colors = ["green", "blue", "red", "orange", "purple", "cyan", "magenta"]
    fig = go.Figure()

    for idx, nodes in enumerate(paths):

        node_lats = []
        node_lons = []
        edge_lats = []
        edge_lons = []

        node_lats += [node2coord[node][1] for node in nodes]
        node_lons += [node2coord[node][0] for node in nodes]
        node_ids = list(node2coord.keys())

        # Create edges
        
        for i in range(1,len(nodes)):
            A = nodes[i-1]
            B = nodes[i]
            lonA, latA = node2coord[A]
            lonB, latB = node2coord[B]
            edge_lats += [latA, latB, None] 
            edge_lons += [lonA, lonB, None]
        # Create the map

        # Add edges

        fig.add_trace(go.Scattermapbox(
            lat=edge_lats,
            lon=edge_lons,
            mode="lines",
            line=dict(width=3, color=colors[idx % len(colors)]),
            name=f"Path {idx+1} Edge"
        ))

        # Add nodes
        fig.add_trace(go.Scattermapbox(
            lat=node_lats,
            lon=node_lons,
            mode="markers+text",
            marker=dict(size=8, color=colors[idx % len(colors)]),
            text=[f"Node {node}" for node in nodes],
            name=f"Path {idx + 1} Node"
        ))

    # Set map layout
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=51.515, lon=-0.118),
            zoom=15
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    fig.show()
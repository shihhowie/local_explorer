from flask import Flask, request, jsonify
from path_finder import run_Yens
from path_util import find_nearest_node
app = Flask(__name__)

@app.route('/find_paths', methods=['GET'])
def find_path():
    start = request.args.get('start')
    end = request.args.get('end')
    method = request.args.get('method', 'Astar')
    k = int(request.args.get('k', 3))
    subpath_len = float(request.args.get("subpath_len", 0.3))

    if not start or not end:
        return jsonify({"error": "Missing required parameters"}), 400
    try:
        # start_lon, start_lat = list(map(float,start.split(",")))
        # finish_lon, finish_lat = list(map(float,start.split(",")))
        # start_node, _ = find_nearest_node(start_lon, start_lat, geohash2node, node2coord)
        # finish_node, _ = find_nearest_node(finish_lon, finish_lat, geohash2node, node2coord)

        paths = run_Yens(start,end,method, k, subpath_len)
        resp = []
        for path in paths:
            resp.append(path.to_json())
        return jsonify({"paths": resp}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 200

if __name__=="__main__":
    app.run(host="0.0.0.0", debug=True, port=9997)
"""
app.py
======
Flask backend for the California Intelligent Search Visualizer.

Routes:
    GET  /             -> map UI (templates/index.html)
    GET  /api/map      -> locations + graph from map_data.json
    GET  /api/algorithms -> list of algorithms and their concept notes
    POST /api/search   -> run one algorithm. JSON body: {"start", "goal", "algorithm"}
"""

import json
import os
import time

from flask import Flask, jsonify, render_template, request

from informed import astar, greedy_best_first, heuristic
from uninformed_search import bfs, dfs, ids, ucs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_DATA_FILE = os.path.join(BASE_DIR, "map_data.json")

app = Flask(__name__)


def load_map_data():
    """Load graph and location data produced by data_fetcher.py."""
    if os.path.exists(MAP_DATA_FILE):
        try:
            with open(MAP_DATA_FILE, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading {MAP_DATA_FILE}: {e}")
    return {"region": "California, USA", "total_cities": 0, "total_edges": 0,
            "locations": {}, "graph": {}}


MAP_DATA = load_map_data()

ALGORITHMS = {
    "bfs": {
        "name": "Breadth-First Search (BFS)",
        "type": "uninformed",
        "run": lambda g, s, t, loc: bfs(g, s, t),
        "concept": {
            "main": "Explores the map in layers: every city 1 road away, then every city 2 roads away, and so on, using a FIFO queue.",
            "selection": "Takes the oldest node in the queue, which is always the shallowest (fewest roads from the start).",
            "info": "Depth only (number of road segments). It ignores miles and has no heuristic, so it finds the path with the fewest hops, not the shortest drive.",
        },
    },
    "dfs": {
        "name": "Depth-First Search (DFS)",
        "type": "uninformed",
        "run": lambda g, s, t, loc: dfs(g, s, t),
        "concept": {
            "main": "Follows one road as far as it can before backtracking, using a LIFO stack and an explored set to avoid loops.",
            "selection": "Takes the newest node pushed on the stack, which is always the deepest one on the current branch.",
            "info": "Depth/order only. No path cost and no heuristic, so the route it returns can be long and winding.",
        },
    },
    "ucs": {
        "name": "Uniform Cost Search (UCS)",
        "type": "uninformed",
        "run": lambda g, s, t, loc: ucs(g, s, t),
        "concept": {
            "main": "Grows outward in order of total miles driven, using a priority queue. Like Dijkstra's algorithm, stopping once the goal is popped.",
            "selection": "Takes the frontier node with the lowest path cost g(n), the road miles from the start.",
            "info": "Path cost g(n) only (OSRM road miles). No heuristic, so it is optimal but explores in every direction.",
        },
    },
    "ids": {
        "name": "Iterative Deepening Search (IDS)",
        "type": "uninformed",
        "run": lambda g, s, t, loc: ids(g, s, t),
        "concept": {
            "main": "Runs depth-limited DFS with limit 0, then 1, then 2, and so on until the goal appears. Gets BFS's shallowest-path result with DFS's small memory.",
            "selection": "Within each iteration it picks the deepest node first (DFS order) but never goes past the current depth limit L.",
            "info": "Depth and the depth limit only. No path cost or heuristic. Shallow nodes are re-expanded every iteration.",
        },
    },
    "greedy": {
        "name": "Greedy Best-First Search",
        "type": "informed",
        "run": lambda g, s, t, loc: greedy_best_first(g, s, t, loc),
        "concept": {
            "main": "Heads straight for whatever city looks closest to the destination, using a priority queue ordered by the heuristic.",
            "selection": "Takes the frontier node with the lowest h(n), the straight-line miles to the goal.",
            "info": "Heuristic h(n) only (haversine distance from Nominatim coordinates). It ignores miles already driven, so it is fast but not optimal.",
        },
    },
    "astar": {
        "name": "A* Search",
        "type": "informed",
        "run": lambda g, s, t, loc: astar(g, s, t, loc),
        "concept": {
            "main": "Combines UCS and Greedy: expands the city whose total estimated trip, driven so far plus straight-line remaining, is smallest.",
            "selection": "Takes the frontier node with the lowest f(n) = g(n) + h(n).",
            "info": "Both path cost g(n) (OSRM road miles) and heuristic h(n) (straight-line miles). Since h never overestimates, A* returns the optimal route while expanding fewer nodes than UCS.",
        },
    },
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/map", methods=["GET"])
def get_map():
    return jsonify(MAP_DATA)


@app.route("/api/algorithms", methods=["GET"])
def get_algorithms():
    return jsonify({k: {"name": v["name"], "type": v["type"], "concept": v["concept"]}
                    for k, v in ALGORITHMS.items()})


@app.route("/api/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    start = payload.get("start", "")
    goal = payload.get("goal", "")
    algo_key = payload.get("algorithm", "")

    graph = MAP_DATA.get("graph", {})
    locations = MAP_DATA.get("locations", {})

    if algo_key not in ALGORITHMS:
        return jsonify({"status": "error", "message": f"Unknown algorithm '{algo_key}'.",
                        "path": [], "cost": 0, "nodes_expanded": 0}), 400
    if start not in graph or goal not in graph:
        return jsonify({"status": "error", "message": "Start and destination must be cities on the map.",
                        "path": [], "cost": 0, "nodes_expanded": 0}), 400

    algo = ALGORITHMS[algo_key]
    t0 = time.perf_counter()
    result = algo["run"](graph, start, goal, locations)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return jsonify({
        "status": "ok" if result["path"] else "no_path",
        "algorithm": algo_key,
        "algorithm_name": algo["name"],
        "start": start,
        "goal": goal,
        "path": result["path"],
        "cost": result["cost"],
        "hops": max(len(result["path"]) - 1, 0),
        "nodes_expanded": result["nodes_expanded"],
        "expanded_order": result["expanded_order"][:500],
        "depth_limit": result.get("depth_limit"),
        "straight_line_miles": round(heuristic(start, goal, locations), 2) if locations else None,
        "time_ms": round(elapsed_ms, 3),
        "concept": algo["concept"],
        "message": "" if result["path"] else "No path found.",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
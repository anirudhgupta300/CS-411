
import heapq
import math

from uninformed import _check, _reconstruct, _result

EARTH_RADIUS_MILES = 3958.8


def haversine(loc1, loc2):
    """Great-circle distance in miles between two {"lat", "lon"} dicts."""
    phi1, phi2 = math.radians(loc1["lat"]), math.radians(loc2["lat"])
    dphi = phi2 - phi1
    dlmb = math.radians(loc2["lon"] - loc1["lon"])
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return EARTH_RADIUS_MILES * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def heuristic(node, goal, locations):
    """h(n) = straight-line miles from node to goal."""
    return haversine(locations[node], locations[goal])


# ---------------------------------------------------------------------------
# 5. Greedy Best-First Search
# ---------------------------------------------------------------------------
def greedy_best_first(graph, start, goal, locations):
    """Always expand the frontier node that LOOKS closest to the goal (lowest h).
    Ignores the miles already driven, so it is fast but not optimal."""
    _check(graph, start, goal)
    counter = 0                                    
    frontier = [(heuristic(start, goal, locations), counter, start)]
    parent = {start: None}
    explored = set()
    expanded = []

    while frontier:
        _, _, node = heapq.heappop(frontier)
        if node in explored:
            continue
        explored.add(node)
        expanded.append(node)
        if node == goal:
            return _result(graph, _reconstruct(parent, goal), expanded)
        for nb in graph[node]:
            if nb not in explored and nb not in parent:
                parent[nb] = node
                counter += 1
                heapq.heappush(frontier, (heuristic(nb, goal, locations), counter, nb))
    return _result(graph, [], expanded)


# ---------------------------------------------------------------------------
# 6. A* Search
# ---------------------------------------------------------------------------
def astar(graph, start, goal, locations):
    """Expand the node with the lowest f(n) = g(n) + h(n).
    g(n) = road miles driven so far, h(n) = straight-line miles left.
    Optimal because h is admissible and consistent."""
    _check(graph, start, goal)
    counter = 0
    h0 = heuristic(start, goal, locations)
    frontier = [(h0, counter, 0.0, start)]         
    best_g = {start: 0.0}
    parent = {start: None}
    explored = set()
    expanded = []

    while frontier:
        f, _, g, node = heapq.heappop(frontier)
        if node in explored:
            continue
        explored.add(node)
        expanded.append(node)
        if node == goal:
            return _result(graph, _reconstruct(parent, goal), expanded)
        for nb, w in graph[node].items():
            new_g = g + w
            if nb not in explored and new_g < best_g.get(nb, float("inf")):
                best_g[nb] = new_g
                parent[nb] = node
                counter += 1
                heapq.heappush(frontier, (new_g + heuristic(nb, goal, locations), counter, new_g, nb))
    return _result(graph, [], expanded)


# Alias so either name works
a_star = astar
greedy = greedy_best_first
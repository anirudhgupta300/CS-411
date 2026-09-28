

import heapq
from collections import deque


def path_cost(graph, path):
    """Sum of edge weights along a path."""
    return round(sum(graph[a][b] for a, b in zip(path, path[1:])), 2)


def _result(graph, path, expanded_order):
    return {
        "path": path,
        "cost": path_cost(graph, path) if path else 0,
        "nodes_expanded": len(expanded_order),
        "expanded_order": expanded_order,
    }


def _reconstruct(parent, goal):
    path = [goal]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]


def _check(graph, start, goal):
    if start not in graph or goal not in graph:
        raise ValueError(f"Unknown city: {start if start not in graph else goal}")


# ---------------------------------------------------------------------------
# 1. Breadth-First Search
# ---------------------------------------------------------------------------
def bfs(graph, start, goal):
    """FIFO queue. Finds the path with the fewest edges (not fewest miles).
    Goal test is applied when a node is generated (early goal test, as in AIMA)."""
    _check(graph, start, goal)
    if start == goal:
        return _result(graph, [start], [start])

    frontier = deque([start])
    parent = {start: None}          # doubles as the reached set
    expanded = []

    while frontier:
        node = frontier.popleft()
        expanded.append(node)
        for nb in sorted(graph[node]):
            if nb not in parent:
                parent[nb] = node
                if nb == goal:
                    return _result(graph, _reconstruct(parent, goal), expanded)
                frontier.append(nb)
    return _result(graph, [], expanded)


# ---------------------------------------------------------------------------
# 2. Depth-First Search
# ---------------------------------------------------------------------------
def dfs(graph, start, goal):
    """LIFO stack, graph-search version (keeps an explored set so it cannot loop).
    Complete on this finite graph but not optimal."""
    _check(graph, start, goal)
    stack = [(start, [start])]
    explored = set()
    expanded = []

    while stack:
        node, path = stack.pop()
        if node in explored:
            continue
        explored.add(node)
        expanded.append(node)
        if node == goal:
            return _result(graph, path, expanded)
        # push in reverse alphabetical order so neighbours are explored alphabetically
        for nb in sorted(graph[node], reverse=True):
            if nb not in explored:
                stack.append((nb, path + [nb]))
    return _result(graph, [], expanded)


# ---------------------------------------------------------------------------
# 3. Uniform-Cost Search
# ---------------------------------------------------------------------------
def ucs(graph, start, goal):
    """Priority queue ordered by path cost g(n). Optimal because all edge
    costs (road miles) are positive. Goal test when a node is popped."""
    _check(graph, start, goal)
    frontier = [(0.0, start)]
    best_g = {start: 0.0}
    parent = {start: None}
    explored = set()
    expanded = []

    while frontier:
        g, node = heapq.heappop(frontier)
        if node in explored:
            continue                     # stale queue entry
        explored.add(node)
        expanded.append(node)
        if node == goal:
            return _result(graph, _reconstruct(parent, goal), expanded)
        for nb, w in graph[node].items():
            new_g = g + w
            if nb not in explored and new_g < best_g.get(nb, float("inf")):
                best_g[nb] = new_g
                parent[nb] = node
                heapq.heappush(frontier, (new_g, nb))
    return _result(graph, [], expanded)


# ---------------------------------------------------------------------------
# 4. Iterative Deepening Search
# ---------------------------------------------------------------------------
def _depth_limited(graph, node, goal, limit, path, on_path, expanded):
    """Recursive depth-limited DFS. Returns (path or None, cutoff_occurred)."""
    expanded.append(node)
    if node == goal:
        return list(path), False
    if limit == 0:
        return None, True
    cutoff = False
    for nb in sorted(graph[node]):
        if nb in on_path:                # avoid cycles along the current path
            continue
        path.append(nb)
        on_path.add(nb)
        found, cut = _depth_limited(graph, nb, goal, limit - 1, path, on_path, expanded)
        path.pop()
        on_path.discard(nb)
        if found is not None:
            return found, False
        cutoff = cutoff or cut
    return None, cutoff


def ids(graph, start, goal, max_depth=None):
    """Run depth-limited search with limit 0, 1, 2, ... until the goal is found.
    Returns the shallowest (fewest-edge) path, like BFS, using DFS-sized memory.
    nodes_expanded counts expansions across ALL iterations (the re-expansion
    overhead is the price IDS pays for its low memory)."""
    _check(graph, start, goal)
    max_depth = len(graph) if max_depth is None else max_depth
    expanded = []
    for limit in range(max_depth + 1):
        found, cutoff = _depth_limited(graph, start, goal, limit, [start], {start}, expanded)
        if found is not None:
            res = _result(graph, found, expanded)
            res["depth_limit"] = limit
            return res
        if not cutoff:                   # whole graph searched, goal unreachable
            break
    return _result(graph, [], expanded)
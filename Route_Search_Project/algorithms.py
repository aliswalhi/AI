"""Manual searches. Steps count each valid removal, including the goal."""

from collections import deque
import heapq

from map_utils import alphabetical, heuristic, route_cost

ALGORITHMS = ("BFS", "DFS", "UCS", "Greedy Best-First", "A*")


def check_endpoints(graph, start, goal):
    if start not in graph or goal not in graph:
        raise ValueError("Start and goal must both be cities in the map.")


def search_result(graph, path, expanded):
    return {
        "path": path,
        "cost": route_cost(graph, path) if path else None,
        "steps": len(expanded),
        "expanded": expanded,
    }


def bfs(graph, start, goal):
    """FIFO queue: visit the shallowest routes first."""
    check_endpoints(graph, start, goal)
    frontier = deque([(start, [start])])
    discovered = {start}
    expanded = []
    while frontier:
        city, path = frontier.popleft()
        expanded.append(city)
        if city == goal:
            return search_result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            if neighbor not in discovered:
                discovered.add(neighbor)
                frontier.append((neighbor, path + [neighbor]))
    return search_result(graph, [], expanded)


def dfs(graph, start, goal):
    """LIFO stack: reverse insertion visits alphabetical neighbors first."""
    check_endpoints(graph, start, goal)
    frontier = [(start, [start])]
    explored = set()
    expanded = []
    while frontier:
        city, path = frontier.pop()
        if city in explored:
            continue
        explored.add(city)
        expanded.append(city)
        if city == goal:
            return search_result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical, reverse=True):
            if neighbor not in explored:
                frontier.append((neighbor, path + [neighbor]))
    return search_result(graph, [], expanded)


def ucs(graph, start, goal):
    """Choose the lowest cost so far; city names break equal priorities."""
    check_endpoints(graph, start, goal)
    frontier = [(0, alphabetical(start), start, [start])]
    best_cost = {start: 0}
    explored = set()
    expanded = []
    while frontier:
        cost, _, city, path = heapq.heappop(frontier)
        # Skip duplicate and outdated entries without counting another step.
        if city in explored or cost != best_cost[city]:
            continue
        explored.add(city)
        expanded.append(city)
        if city == goal:
            return search_result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            new_cost = cost + graph[city][neighbor]
            if neighbor not in explored and new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                heapq.heappush(frontier, (new_cost, alphabetical(neighbor), neighbor, path + [neighbor]))
    return search_result(graph, [], expanded)


def greedy_best_first(graph, coordinates, start, goal):
    """Choose h(n), keeping the path that first discovered each city."""
    check_endpoints(graph, start, goal)
    frontier = [(heuristic(coordinates, start, goal), alphabetical(start), start, [start])]
    discovered = {start}
    expanded = []
    while frontier:
        _, _, city, path = heapq.heappop(frontier)
        expanded.append(city)
        if city == goal:
            return search_result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            if neighbor not in discovered:
                discovered.add(neighbor)
                priority = heuristic(coordinates, neighbor, goal)
                heapq.heappush(frontier, (priority, alphabetical(neighbor), neighbor, path + [neighbor]))
    return search_result(graph, [], expanded)


def a_star(graph, coordinates, start, goal):
    """Choose g(n) + h(n). Expanded cities stay closed."""
    check_endpoints(graph, start, goal)
    frontier = [(heuristic(coordinates, start, goal), alphabetical(start), 0, start, [start])]
    best_cost = {start: 0}
    explored = set()
    expanded = []
    while frontier:
        _, _, cost, city, path = heapq.heappop(frontier)
        if city in explored or cost != best_cost[city]:
            continue
        explored.add(city)
        expanded.append(city)
        if city == goal:
            return search_result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            new_cost = cost + graph[city][neighbor]
            if neighbor not in explored and new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                priority = new_cost + heuristic(coordinates, neighbor, goal)
                # Name comes before g, so equal f values use alphabetical order.
                heapq.heappush(frontier, (priority, alphabetical(neighbor), new_cost, neighbor, path + [neighbor]))
    return search_result(graph, [], expanded)


def run_search(algorithm, road_map, start, goal):
    graph = road_map["graph"]
    if algorithm == "Greedy Best-First":
        return greedy_best_first(graph, road_map["coordinates"], start, goal)
    if algorithm == "A*":
        return a_star(graph, road_map["coordinates"], start, goal)
    functions = {"BFS": bfs, "DFS": dfs, "UCS": ucs}
    if algorithm not in functions:
        raise ValueError(f"Unknown algorithm: {algorithm}.")
    return functions[algorithm](graph, start, goal)


def compare_all(road_map, start, goal):
    results = {}
    for name in ALGORITHMS:
        results[name] = run_search(name, road_map, start, goal)
    return results


def comparison_rows(results):
    costs = [result["cost"] for result in results.values() if result["path"]]
    lowest = min(costs) if costs else None
    rows = []
    for name, result in results.items():
        rows.append({
            "Algorithm": name,
            "Path": " → ".join(result["path"]) if result["path"] else "No route",
            "Cost (km)": result["cost"],
            "Steps": result["steps"],
            "Optimal": "Yes" if result["path"] and result["cost"] == lowest else "—",
        })
    return rows

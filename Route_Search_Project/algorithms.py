"""Five manually implemented graph searches; only Python standard libraries.

Steps count unique, valid frontier removals INCLUDING the goal. Stale entries
and already-expanded cities do not count. Goal tests happen only after removal.
No search reopens an expanded city, as required by the official assignment.
"""

from collections import deque
from dataclasses import dataclass
import heapq
import math

from map_utils import Graph, Coordinates, RoadMap, alphabetical, heuristic, route_cost


ALGORITHMS = ("BFS", "DFS", "UCS", "Greedy Best-First", "A*")


@dataclass
class SearchResult:
    path: list[str]
    cost: float | None
    steps: int
    expanded: list[str]

    @property
    def found(self) -> bool:
        return bool(self.path)


def _check_endpoints(graph: Graph, start: str, goal: str) -> None:
    if start not in graph or goal not in graph:
        raise ValueError("Start and goal must both be cities in the map.")


def _result(graph: Graph, path: list[str], expanded: list[str]) -> SearchResult:
    return SearchResult(path, route_cost(graph, path) if path else None, len(expanded), expanded)


def bfs(graph: Graph, start: str, goal: str) -> SearchResult:
    """FIFO search; sort each expansion's neighbors alphabetically."""
    _check_endpoints(graph, start, goal)
    frontier = deque([(start, [start])])
    discovered = {start}
    expanded: list[str] = []
    while frontier:
        city, path = frontier.popleft()
        expanded.append(city)
        if city == goal:
            return _result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            if neighbor not in discovered:
                discovered.add(neighbor)
                frontier.append((neighbor, path + [neighbor]))
    return _result(graph, [], expanded)


def dfs(graph: Graph, start: str, goal: str) -> SearchResult:
    """LIFO search; reverse-push so the alphabetical first city is popped first.

    Cities close on removal. Duplicate stack entries are possible when another
    branch reaches a queued city; each entry retains its own path copy.
    Once the city has expanded, all later entries for it are skipped.
    """
    _check_endpoints(graph, start, goal)
    frontier = [(start, [start])]
    explored: set[str] = set()
    expanded: list[str] = []
    while frontier:
        city, path = frontier.pop()
        if city in explored:
            continue
        explored.add(city)
        expanded.append(city)
        if city == goal:
            return _result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical, reverse=True):
            if neighbor not in explored:
                frontier.append((neighbor, path + [neighbor]))
    return _result(graph, [], expanded)


def ucs(graph: Graph, start: str, goal: str) -> SearchResult:
    """Dijkstra / uniform-cost search, with priority g(n)."""
    return _cost_search(graph, start, goal, None)


def greedy_best_first(graph: Graph, coordinates: Coordinates, start: str, goal: str) -> SearchResult:
    """Select h(n) only. A city keeps the path by which it was first found."""
    _check_endpoints(graph, start, goal)
    frontier = [(heuristic(coordinates, start, goal), alphabetical(start), start, [start])]
    discovered = {start}
    expanded: list[str] = []
    while frontier:
        _, _, city, path = heapq.heappop(frontier)
        expanded.append(city)
        if city == goal:
            return _result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            if neighbor not in discovered:
                discovered.add(neighbor)
                heapq.heappush(frontier, (
                    heuristic(coordinates, neighbor, goal), alphabetical(neighbor),
                    neighbor, path + [neighbor],
                ))
    return _result(graph, [], expanded)


def a_star(graph: Graph, coordinates: Coordinates, start: str, goal: str) -> SearchResult:
    """Select g(n)+h(n). Optimal with a consistent heuristic and nonnegative costs.

    Expanded cities stay closed to follow the assignment. Inconsistent uploaded
    heuristics can need reopening for optimality; the UI documents that limit.
    """
    return _cost_search(graph, start, goal, coordinates)


def _cost_search(graph: Graph, start: str, goal: str, coordinates: Coordinates | None) -> SearchResult:
    """Shared hand-written heap mechanics for UCS and A*.

    A better open path is inserted with its new g; the old heap entry becomes
    stale. Each entry owns its path, so later updates cannot corrupt a result.
    Equal priorities compare city names BEFORE any g-cost or path field.
    """
    _check_endpoints(graph, start, goal)
    initial_h = heuristic(coordinates, start, goal) if coordinates is not None else 0
    frontier = [(initial_h, alphabetical(start), 0.0, start, [start])]
    best_cost = {start: 0.0}
    explored: set[str] = set()
    expanded: list[str] = []
    while frontier:
        _, _, cost, city, path = heapq.heappop(frontier)
        if city in explored or cost != best_cost[city]:
            continue
        explored.add(city)
        expanded.append(city)
        if city == goal:
            return _result(graph, path, expanded)
        for neighbor in sorted(graph[city], key=alphabetical):
            if neighbor in explored:
                continue
            new_cost = cost + graph[city][neighbor]
            if new_cost < best_cost.get(neighbor, math.inf):
                best_cost[neighbor] = new_cost
                estimate = heuristic(coordinates, neighbor, goal) if coordinates is not None else 0
                heapq.heappush(frontier, (
                    new_cost + estimate, alphabetical(neighbor), new_cost,
                    neighbor, path + [neighbor],
                ))
    return _result(graph, [], expanded)


def run_search(algorithm: str, road_map: RoadMap, start: str, goal: str) -> SearchResult:
    if algorithm == "Greedy Best-First":
        return greedy_best_first(road_map.graph, road_map.coordinates, start, goal)
    if algorithm == "A*":
        return a_star(road_map.graph, road_map.coordinates, start, goal)
    functions = {"BFS": bfs, "DFS": dfs, "UCS": ucs}
    if algorithm not in functions:
        raise ValueError(f"Unknown algorithm: {algorithm}.")
    return functions[algorithm](road_map.graph, start, goal)


def compare_all(road_map: RoadMap, start: str, goal: str) -> dict[str, SearchResult]:
    return {name: run_search(name, road_map, start, goal) for name in ALGORITHMS}


def comparison_rows(results: dict[str, SearchResult]) -> list[dict]:
    successful_costs = [result.cost for result in results.values() if result.found]
    lowest = min(successful_costs) if successful_costs else None
    return [{
        "Algorithm": name,
        "Path": " → ".join(result.path) if result.found else "No route",
        "Cost (km)": result.cost,
        "Steps": result.steps,
        "Optimal": "Yes" if result.found and result.cost == lowest else "—",
    } for name, result in results.items()]

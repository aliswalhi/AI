"""Validate map files and build a small, undirected adjacency-list graph."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


Graph = dict[str, dict[str, float]]
Coordinates = dict[str, tuple[float, float]]


class MapValidationError(ValueError):
    """A readable error that can be shown beside the upload control."""


@dataclass
class RoadMap:
    name: str
    unit: str
    coordinates: Coordinates
    graph: Graph
    roads: list[tuple[str, str, float]]


def alphabetical(name: str) -> tuple[str, str]:
    """Case-insensitive alphabetical order, with a deterministic final tie."""
    return name.casefold(), name


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapValidationError(f"{label} must be a finite number.")
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise MapValidationError(f"{label} must be a finite number.") from None
    # Bounds keep coordinate differences, cumulative costs and plotting finite.
    if not math.isfinite(number) or abs(number) > 1e100:
        raise MapValidationError(f"{label} must be finite and at most 1e100 in magnitude.")
    return number


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MapValidationError(f"{label} must be a non-empty string.")
    if value != value.strip() or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise MapValidationError(f"{label} cannot contain control characters, invalid Unicode or outer whitespace.")
    return value


def validate_map(data: Any) -> RoadMap:
    """Check the assignment schema. Zero-cost roads and isolated cities are valid.

    A repeated undirected road is rejected rather than silently choosing a weight.
    Names are unique without regard to case; road references must match exactly.
    """
    if not isinstance(data, dict):
        raise MapValidationError("The JSON root must be an object containing cities and roads.")
    name = _name(data.get("name", "Uploaded road map"), "Map name")
    if data.get("unit", "km") != "km":
        raise MapValidationError("Map unit must be 'km'; coordinates and road distances use kilometres.")
    cities, roads = data.get("cities"), data.get("roads")
    if not isinstance(cities, list) or not cities:
        raise MapValidationError("'cities' must be a non-empty list.")
    if not isinstance(roads, list):
        raise MapValidationError("'roads' must be a list (it may be empty).")

    coordinates: Coordinates = {}
    used_names: set[str] = set()
    for index, city in enumerate(cities, 1):
        if not isinstance(city, dict):
            raise MapValidationError(f"City {index} must be an object with name, x and y.")
        city_name = _name(city.get("name"), f"City {index} name")
        if city_name.casefold() in used_names:
            raise MapValidationError(f"Duplicate city name: {city_name}.")
        used_names.add(city_name.casefold())
        coordinates[city_name] = (
            _number(city.get("x"), f"City {city_name} x"),
            _number(city.get("y"), f"City {city_name} y"),
        )

    graph: Graph = {city: {} for city in coordinates}
    validated_roads: list[tuple[str, str, float]] = []
    used_roads: set[frozenset[str]] = set()
    for index, road in enumerate(roads, 1):
        if not isinstance(road, dict):
            raise MapValidationError(f"Road {index} must be an object with from, to and km.")
        source = _name(road.get("from"), f"Road {index} 'from'")
        target = _name(road.get("to"), f"Road {index} 'to'")
        for city in (source, target):
            if city not in coordinates:
                raise MapValidationError(f"Road {index} references unknown city: {city}.")
        distance = _number(road.get("km"), f"Road {index} km")
        if distance < 0:
            raise MapValidationError(f"Road {index} distance cannot be negative.")
        edge = frozenset((source, target))
        if edge in used_roads:
            raise MapValidationError(f"Duplicate two-way road: {source} / {target}.")
        used_roads.add(edge)
        graph[source][target] = distance
        graph[target][source] = distance
        validated_roads.append((source, target, distance))
    return RoadMap(name, "km", coordinates, graph, validated_roads)


def parse_map(content: str | bytes) -> RoadMap:
    """Decode UTF-8 JSON from an upload, accepting an optional UTF-8 BOM."""
    try:
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        data = json.loads(content.lstrip("\ufeff"))
    except UnicodeDecodeError:
        raise MapValidationError("Save the map as UTF-8 JSON.") from None
    except (ValueError, RecursionError) as error:
        if isinstance(error, json.JSONDecodeError):
            detail = f"line {error.lineno}, column {error.colno}"
        else:
            detail = "excessive nesting or an unsupported numeric value"
        raise MapValidationError(f"Invalid JSON ({detail}). Check commas, quotes and brackets.") from None
    return validate_map(data)


def load_map(path: str | Path) -> RoadMap:
    try:
        return parse_map(Path(path).read_bytes())
    except OSError as error:
        raise MapValidationError(f"Cannot read map file: {error.strerror}.") from None


def heuristic(coordinates: Coordinates, city: str, goal: str) -> int:
    """The assignment's floor of Euclidean distance, in kilometres."""
    x, y = coordinates[city]
    goal_x, goal_y = coordinates[goal]
    return math.floor(math.hypot(x - goal_x, y - goal_y))


def heuristic_is_consistent(road_map: RoadMap, goal: str) -> bool:
    """A closed-set A* guarantee requires h(u) <= w(u,v) + h(v)."""
    estimates = {city: heuristic(road_map.coordinates, city, goal) for city in road_map.graph}
    return all(
        estimates[city] <= distance + estimates[neighbor]
        for city, neighbors in road_map.graph.items()
        for neighbor, distance in neighbors.items()
    )


def route_cost(graph: Graph, path: list[str]) -> float:
    if not path:
        raise ValueError("An empty route has no cost.")
    if any(city not in graph for city in path):
        raise ValueError("The route contains an unknown city.")
    try:
        return math.fsum(graph[source][target] for source, target in zip(path, path[1:]))
    except KeyError:
        raise ValueError("The route contains a missing road.") from None


def map_to_dict(road_map: RoadMap) -> dict:
    return {
        "name": road_map.name,
        "unit": road_map.unit,
        "cities": [{"name": city, "x": x, "y": y} for city, (x, y) in road_map.coordinates.items()],
        "roads": [{"from": source, "to": target, "km": km} for source, target, km in road_map.roads],
    }


def format_distance(distance: float | None) -> str:
    return "—" if distance is None else f"{distance:,.10g}"

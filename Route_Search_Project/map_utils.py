"""Read and validate maps, then build two-way adjacency lists."""

import json
import math
from pathlib import Path


class MapValidationError(ValueError):
    pass


def alphabetical(name):
    return name.casefold(), name


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapValidationError(f"{label} must be a finite number.")
    try:
        value = float(value)
    except OverflowError:
        raise MapValidationError(f"{label} must be a finite number.")
    if not math.isfinite(value):
        raise MapValidationError(f"{label} must be a finite number.")
    return value


def name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise MapValidationError(f"{label} must be a non-empty string.")
    if value != value.strip() or not value.isprintable():
        raise MapValidationError(f"{label} cannot contain control characters, invalid Unicode or outer whitespace.")
    return value


def validate_map(data):
    if not isinstance(data, dict):
        raise MapValidationError("The JSON root must be an object containing cities and roads.")
    map_name = name(data.get("name", "Uploaded road map"), "Map name")
    if data.get("unit", "km") != "km":
        raise MapValidationError("Map unit must be 'km'; coordinates and road distances use kilometres.")
    cities = data.get("cities")
    roads = data.get("roads")
    if not isinstance(cities, list) or not cities:
        raise MapValidationError("'cities' must be a non-empty list.")
    if not isinstance(roads, list):
        raise MapValidationError("'roads' must be a list (it may be empty).")

    coordinates = {}
    used_names = set()
    for index, city in enumerate(cities, 1):
        if not isinstance(city, dict):
            raise MapValidationError(f"City {index} must be an object with name, x and y.")
        city_name = name(city.get("name"), f"City {index} name")
        if city_name.casefold() in used_names:
            raise MapValidationError(f"Duplicate city name: {city_name}.")
        used_names.add(city_name.casefold())
        x = number(city.get("x"), f"City {city_name} x")
        y = number(city.get("y"), f"City {city_name} y")
        coordinates[city_name] = (x, y)

    graph = {city: {} for city in coordinates}
    road_list = []
    for index, road in enumerate(roads, 1):
        if not isinstance(road, dict):
            raise MapValidationError(f"Road {index} must be an object with from, to and km.")
        source = name(road.get("from"), f"Road {index} 'from'")
        target = name(road.get("to"), f"Road {index} 'to'")
        for city in (source, target):
            if city not in graph:
                raise MapValidationError(f"Road {index} references unknown city: {city}.")
        distance = number(road.get("km"), f"Road {index} km")
        if distance < 0:
            raise MapValidationError(f"Road {index} distance cannot be negative.")
        if target in graph[source]:
            raise MapValidationError(f"Duplicate two-way road: {source} / {target}.")
        graph[source][target] = distance
        graph[target][source] = distance
        road_list.append((source, target, distance))
    return {"name": map_name, "unit": "km", "coordinates": coordinates, "graph": graph, "roads": road_list}


def parse_map(content):
    try:
        # json.loads handles UTF-8 bytes and an optional BOM for uploads.
        if isinstance(content, str):
            content = content.encode()
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise MapValidationError(f"Invalid JSON (line {error.lineno}, column {error.colno}). Check commas, quotes and brackets.")
    except UnicodeError:
        raise MapValidationError("Save the map as UTF-8 JSON.")
    except (ValueError, RecursionError):
        raise MapValidationError("Invalid JSON (excessive nesting or an unsupported numeric value). Check commas, quotes and brackets.")
    return validate_map(data)


def load_map(path):
    try:
        return parse_map(Path(path).read_bytes())
    except OSError as error:
        raise MapValidationError(f"Cannot read map file: {error.strerror}.")


def heuristic(coordinates, city, goal):
    x, y = coordinates[city]
    goal_x, goal_y = coordinates[goal]
    return math.floor(math.hypot(x - goal_x, y - goal_y))


def heuristic_is_consistent(road_map, goal):
    estimates = {}
    for city in road_map["graph"]:
        estimates[city] = heuristic(road_map["coordinates"], city, goal)
    for city, neighbors in road_map["graph"].items():
        for neighbor, distance in neighbors.items():
            if estimates[city] > distance + estimates[neighbor]:
                return False
    return True


def route_cost(graph, path):
    if not path:
        raise ValueError("An empty route has no cost.")
    for city in path:
        if city not in graph:
            raise ValueError("The route contains an unknown city.")
    costs = []
    for source, target in zip(path, path[1:]):
        if target not in graph[source]:
            raise ValueError("The route contains a missing road.")
        costs.append(graph[source][target])
    return math.fsum(costs)


def map_to_dict(road_map):
    cities = []
    for city, (x, y) in road_map["coordinates"].items():
        cities.append({"name": city, "x": x, "y": y})
    roads = []
    for source, target, distance in road_map["roads"]:
        roads.append({"from": source, "to": target, "km": distance})
    return {"name": road_map["name"], "unit": road_map["unit"], "cities": cities, "roads": roads}


def format_distance(distance):
    return "—" if distance is None else f"{distance:,.10g}"

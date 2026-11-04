import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from map_utils import MapValidationError, load_map, map_to_dict, parse_map, route_cost, validate_map
from test_search import make_map
from algorithms import ALGORITHMS, run_search


BASE = {
    "name": "Uploaded example", "unit": "km",
    "cities": [{"name": "Alpha", "x": 0, "y": 0}, {"name": "Beta", "x": 3, "y": 4}],
    "roads": [{"from": "Alpha", "to": "Beta", "km": 6}],
}


class MapTests(unittest.TestCase):
    def test_default_map_matches_assignment_size(self):
        road_map = load_map(Path(__file__).resolve().parents[1] / "westbank_map.json")
        self.assertEqual((len(road_map.coordinates), len(road_map.roads)), (11, 19))
        self.assertEqual(sum(len(neighbors) for neighbors in road_map.graph.values()), 38)

    def test_valid_upload_works_in_every_search_and_both_directions(self):
        road_map = parse_map(json.dumps(BASE).encode())
        for name in ALGORITHMS:
            for start, goal in [("Alpha", "Beta"), ("Beta", "Alpha")]:
                result = run_search(name, road_map, start, goal)
                self.assertEqual((result.path, result.cost, result.steps), ([start, goal], 6, 2))

    def test_one_city_empty_road_map(self):
        road_map = make_map(["Only"], [])
        for name in ALGORITHMS:
            self.assertEqual(run_search(name, road_map, "Only", "Only").steps, 1)

    def test_missing_optional_metadata_uses_defaults(self):
        data = copy.deepcopy(BASE)
        del data["name"], data["unit"]
        self.assertEqual(validate_map(data).unit, "km")

    def test_invalid_structures(self):
        invalid = [None, [], "map", {}, {"cities": [], "roads": []}, {"cities": {}, "roads": []}, {"cities": [None], "roads": []}, {"cities": BASE["cities"], "roads": None}, {"cities": BASE["cities"], "roads": [42]}]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(MapValidationError):
                validate_map(data)

    def test_invalid_names(self):
        for name in [None, "", " ", " Alpha", "Alpha ", "A\nB", "\ud800", 1, True]:
            data = copy.deepcopy(BASE)
            data["cities"][0]["name"] = name
            with self.subTest(name=name), self.assertRaises(MapValidationError):
                validate_map(data)

    def test_duplicate_names_including_case(self):
        for name in ["Alpha", "alpha"]:
            data = copy.deepcopy(BASE)
            data["cities"][1]["name"] = name
            with self.assertRaisesRegex(MapValidationError, "Duplicate city"):
                validate_map(data)

    def test_unknown_road_reference(self):
        data = copy.deepcopy(BASE)
        data["roads"][0]["to"] = "Unknown"
        with self.assertRaisesRegex(MapValidationError, "unknown city"):
            validate_map(data)

    def test_duplicate_undirected_road(self):
        data = copy.deepcopy(BASE)
        data["roads"].append({"from": "Beta", "to": "Alpha", "km": 99})
        with self.assertRaisesRegex(MapValidationError, "Duplicate two-way road"):
            validate_map(data)

    def test_negative_road_rejected(self):
        data = copy.deepcopy(BASE)
        data["roads"][0]["km"] = -0.5
        with self.assertRaisesRegex(MapValidationError, "negative"):
            validate_map(data)

    def test_non_numeric_non_finite_and_oversized_values(self):
        for value in [None, "3", True, [], float("nan"), float("inf"), -float("inf"), 10 ** 400, 1e101]:
            for target in ["x", "y", "km"]:
                data = copy.deepcopy(BASE)
                item = data["roads"][0] if target == "km" else data["cities"][0]
                item[target] = value
                with self.subTest(value=str(value), field=target), self.assertRaises(MapValidationError):
                    validate_map(data)

    def test_negative_coordinates_are_valid(self):
        data = copy.deepcopy(BASE)
        data["cities"][0]["x"] = -123.4
        self.assertEqual(validate_map(data).coordinates["Alpha"][0], -123.4)

    def test_wrong_units_rejected(self):
        data = copy.deepcopy(BASE)
        data["unit"] = "miles"
        with self.assertRaisesRegex(MapValidationError, "unit"):
            validate_map(data)

    def test_malformed_json_and_encoding(self):
        for content in [b"not json", b'{"cities": }', b"\xff\xfe", "[" * 2000, '{"number":' + "1" * 5000 + '}']:
            with self.assertRaises(MapValidationError):
                parse_map(content)

    def test_utf8_bom_and_unicode_names(self):
        data = copy.deepcopy(BASE)
        data["name"] = "خريطة"
        road_map = parse_map(b"\xef\xbb\xbf" + json.dumps(data, ensure_ascii=False).encode())
        self.assertEqual(road_map.name, "خريطة")

    def test_json_round_trip(self):
        road_map = validate_map(BASE)
        self.assertEqual(map_to_dict(parse_map(json.dumps(map_to_dict(road_map)))), map_to_dict(road_map))

    def test_load_file_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            path.write_text(json.dumps(BASE), encoding="utf-8")
            self.assertEqual(load_map(path).graph["Alpha"]["Beta"], 6)
            with self.assertRaisesRegex(MapValidationError, "Cannot read"):
                load_map(Path(directory) / "missing.json")

    def test_invalid_route_rejected(self):
        road_map = make_map(["S", "A", "G"], [("S", "A", 1)])
        for path in [[], ["Unknown"], ["S", "G"]]:
            with self.assertRaises(ValueError):
                route_cost(road_map.graph, path)


if __name__ == "__main__":
    unittest.main()

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import compare_all
from map_utils import MapValidationError, map_to_dict, parse_map, validate_map

BASE = {
    "name": "Other map", "cities": [{"name": "A", "x": 0, "y": 0}, {"name": "B", "x": 3, "y": 4}],
    "roads": [{"from": "A", "to": "B", "km": 6}],
}


class MapTests(unittest.TestCase):
    def test_upload_and_bidirectional_roads(self):
        m = parse_map(json.dumps(BASE).encode())
        self.assertEqual(m["graph"]["A"]["B"], m["graph"]["B"]["A"])
        for result in compare_all(m, "B", "A").values():
            self.assertEqual((result["path"], result["cost"]), (["B", "A"], 6))
        self.assertEqual(map_to_dict(parse_map(json.dumps(map_to_dict(m)))), map_to_dict(m))

    def test_invalid_json_and_structure(self):
        for content in [b"not json", b"\xff", b"[]", b"{}", b'{"cities": [], "roads": []}']:
            with self.assertRaises(MapValidationError):
                parse_map(content)

    def test_names_roads_and_distances(self):
        changes = [
            ("cities", 0, "name", ""), ("cities", 1, "name", "a"),
            ("roads", 0, "to", "Unknown"), ("roads", 0, "km", -1),
        ]
        for section, index, key, value in changes:
            data = copy.deepcopy(BASE)
            data[section][index][key] = value
            with self.assertRaises(MapValidationError):
                validate_map(data)

    def test_finite_numbers(self):
        for field in ("x", "y", "km"):
            for value in [True, "3", None, float("inf"), float("nan")]:
                data = copy.deepcopy(BASE)
                item = data["roads"][0] if field == "km" else data["cities"][0]
                item[field] = value
                with self.assertRaises(MapValidationError):
                    validate_map(data)
        data = copy.deepcopy(BASE)
        data["cities"][0]["x"] = 1e101
        self.assertEqual(validate_map(data)["coordinates"]["A"][0], 1e101)


if __name__ == "__main__":
    unittest.main()

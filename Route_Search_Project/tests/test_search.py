"""Small examples for the five searches and assignment rules."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import ALGORITHMS, compare_all, comparison_rows, run_search
from map_utils import heuristic, heuristic_is_consistent, load_map, route_cost, validate_map


def make_map(names, roads, coordinates=None):
    coordinates = coordinates or {}
    cities = []
    for name in names:
        x, y = coordinates.get(name, (0, 0))
        cities.append({"name": name, "x": x, "y": y})
    return validate_map({"cities": cities, "roads": [
        {"from": a, "to": b, "km": km} for a, b, km in roads
    ]})


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.map = load_map(Path(__file__).resolve().parents[1] / "westbank_map.json")

    def test_five_routes_costs_and_steps(self):
        expected = {
            "BFS": (["Nablus", "Jericho", "Jerusalem"], 108, 10),
            "DFS": (["Nablus", "Jenin", "Tubas", "Jericho", "Bethlehem", "Jerusalem"], 194, 7),
            "UCS": (["Nablus", "Ramallah", "Jerusalem"], 64, 8),
            "Greedy Best-First": (["Nablus", "Ramallah", "Jerusalem"], 64, 3),
            "A*": (["Nablus", "Ramallah", "Jerusalem"], 64, 4),
        }
        for name, result in compare_all(self.map, "Nablus", "Jerusalem").items():
            self.assertEqual((result["path"], result["cost"], result["steps"]), expected[name])

    def test_all_city_pairs(self):
        for start in self.map["graph"]:
            for goal in self.map["graph"]:
                results = compare_all(self.map, start, goal)
                for name, result in results.items():
                    with self.subTest(start=start, goal=goal, algorithm=name):
                        self.assertEqual((result["path"][0], result["path"][-1]), (start, goal))
                        self.assertEqual(result["cost"], route_cost(self.map["graph"], result["path"]))
                        self.assertEqual(result["steps"], len(set(result["expanded"])))
                        self.assertEqual(result["steps"], len(result["expanded"]))
                self.assertEqual(results["UCS"]["cost"], results["A*"]["cost"])

    def test_other_required_routes(self):
        for start, goal, cost in [("Jenin", "Hebron", 144), ("Ramallah", "Jericho", 40), ("Bethlehem", "Nablus", 74)]:
            for name in ("UCS", "A*"):
                self.assertEqual(run_search(name, self.map, start, goal)["cost"], cost)

    def test_same_city(self):
        for result in compare_all(self.map, "Jenin", "Jenin").values():
            self.assertEqual(result, {"path": ["Jenin"], "cost": 0, "steps": 1, "expanded": ["Jenin"]})

    def test_unreachable(self):
        m = make_map(["S", "A", "G"], [("S", "A", 1)])
        for result in compare_all(m, "S", "G").values():
            self.assertEqual((result["path"], result["cost"], result["expanded"]), ([], None, ["S", "A"]))

    def test_alphabetical_ties(self):
        m = make_map(["S", "B", "A", "G"], [("S", "B", 1), ("S", "A", 1), ("B", "G", 1), ("A", "G", 1)])
        for result in compare_all(m, "S", "G").values():
            self.assertEqual(result["path"], ["S", "A", "G"])

    def test_goal_on_removal(self):
        m = make_map(["S", "G", "A"], [("S", "G", 9), ("S", "A", 1)])
        for result in compare_all(m, "S", "G").values():
            self.assertEqual(result["expanded"], ["S", "A", "G"])

    def test_better_paths_and_stale_entries(self):
        m = make_map(["S", "A", "B", "G", "T"], [("S", "A", 10), ("S", "B", 1), ("B", "A", 1), ("A", "G", 1)])
        for name in ("UCS", "A*"):
            r = run_search(name, m, "S", "G")
            self.assertEqual((r["path"], r["cost"], r["steps"]), (["S", "B", "A", "G"], 3, 4))
            self.assertEqual(run_search(name, m, "S", "T")["steps"], 4)
        self.assertEqual(run_search("DFS", m, "S", "T")["steps"], 4)

    def test_heuristic_and_closed_cities(self):
        self.assertEqual(heuristic({"S": (0, 0), "G": (2, 2)}, "S", "G"), 2)
        m = make_map(["S", "A", "B", "C", "G"], [("S", "A", 2), ("S", "B", 2), ("A", "C", 2), ("B", "C", 1), ("C", "G", 2)], {"B": (3, 0)})
        self.assertFalse(heuristic_is_consistent(m, "G"))
        self.assertEqual(run_search("A*", m, "S", "G")["cost"], 6)
        self.assertEqual(run_search("UCS", m, "S", "G")["cost"], 5)

    def test_compare_all_optimal_and_failed(self):
        rows = comparison_rows(compare_all(self.map, "Nablus", "Jerusalem"))
        self.assertEqual([r["Algorithm"] for r in rows if r["Optimal"] == "Yes"], ["UCS", "Greedy Best-First", "A*"])
        rows = comparison_rows(compare_all(make_map(["S", "G"], []), "S", "G"))
        self.assertTrue(all(r["Optimal"] != "Yes" for r in rows))


if __name__ == "__main__":
    unittest.main()

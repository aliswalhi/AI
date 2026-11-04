"""Algorithm checks with a separate Floyd-Warshall shortest-distance oracle."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms import ALGORITHMS, SearchResult, compare_all, comparison_rows, run_search
from map_utils import heuristic, heuristic_is_consistent, load_map, route_cost, validate_map


def make_map(names, edges, coordinates=None):
    coordinates = coordinates or {}
    return validate_map({
        "name": "Test map", "unit": "km",
        "cities": [{"name": name, "x": coordinates.get(name, (0, 0))[0], "y": coordinates.get(name, (0, 0))[1]} for name in names],
        "roads": [{"from": a, "to": b, "km": cost} for a, b, cost in edges],
    })


def floyd_warshall(road_map):
    """Independent all-pairs reference; no priority queue or search code reused."""
    names = list(road_map.graph)
    distance = {(a, b): 0 if a == b else math.inf for a in names for b in names}
    for a, b, cost in road_map.roads:
        distance[a, b] = distance[b, a] = min(distance[a, b], cost)
    for middle in names:
        for a in names:
            for b in names:
                distance[a, b] = min(distance[a, b], distance[a, middle] + distance[middle, b])
    return distance


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default_map = load_map(Path(__file__).resolve().parents[1] / "westbank_map.json")

    def assert_valid_result(self, road_map, result, start, goal):
        self.assertEqual(result.steps, len(result.expanded))
        self.assertEqual(result.steps, len(set(result.expanded)), "A city expanded twice")
        self.assertLessEqual(result.steps, len(road_map.graph))
        if result.found:
            self.assertEqual(result.path[0], start)
            self.assertEqual(result.path[-1], goal)
            self.assertEqual(len(result.path), len(set(result.path)))
            self.assertEqual(result.expanded[-1], goal)
            self.assertEqual(result.cost, route_cost(road_map.graph, result.path))
        else:
            self.assertEqual(result.path, [])
            self.assertIsNone(result.cost)

    def test_all_121_default_pairs_and_all_five_algorithms(self):
        oracle = floyd_warshall(self.default_map)
        for start in self.default_map.graph:
            for goal in self.default_map.graph:
                for name, result in compare_all(self.default_map, start, goal).items():
                    with self.subTest(start=start, goal=goal, algorithm=name):
                        self.assertTrue(result.found)
                        self.assert_valid_result(self.default_map, result, start, goal)
                        if name in ("UCS", "A*"):
                            self.assertEqual(result.cost, oracle[start, goal])

    def test_required_reference_routes(self):
        cases = [
            ("Nablus", "Jerusalem", ["Nablus", "Ramallah", "Jerusalem"], 64),
            ("Jenin", "Hebron", ["Jenin", "Nablus", "Ramallah", "Jerusalem", "Bethlehem", "Hebron"], 144),
            ("Ramallah", "Jericho", ["Ramallah", "Jericho"], 40),
            ("Bethlehem", "Nablus", ["Bethlehem", "Jerusalem", "Ramallah", "Nablus"], 74),
        ]
        for start, goal, expected_path, expected_cost in cases:
            for algorithm in ("UCS", "A*"):
                with self.subTest(algorithm=algorithm, start=start):
                    result = run_search(algorithm, self.default_map, start, goal)
                    self.assertEqual(result.path, expected_path)
                    self.assertEqual(result.cost, expected_cost)

    def test_exact_nablus_jerusalem_steps(self):
        expected = {"BFS": 10, "DFS": 7, "UCS": 8, "Greedy Best-First": 3, "A*": 4}
        for name, result in compare_all(self.default_map, "Nablus", "Jerusalem").items():
            self.assertEqual(result.steps, expected[name], name)

    def test_default_heuristic_consistent_for_every_goal(self):
        for goal in self.default_map.graph:
            self.assertTrue(heuristic_is_consistent(self.default_map, goal), goal)

    def test_start_equals_goal_all_algorithms(self):
        for name in ALGORITHMS:
            result = run_search(name, self.default_map, "Jenin", "Jenin")
            self.assertEqual((result.path, result.cost, result.steps, result.expanded), (["Jenin"], 0, 1, ["Jenin"]))

    def test_unreachable_all_algorithms(self):
        road_map = make_map(["S", "A", "G"], [("S", "A", 2)])
        for name in ALGORITHMS:
            result = run_search(name, road_map, "S", "G")
            self.assert_valid_result(road_map, result, "S", "G")
            self.assertFalse(result.found)
            self.assertEqual(result.expanded, ["S", "A"])

    def test_goal_is_checked_on_pop_not_generation(self):
        # G is generated immediately, but A has priority over it in every search.
        road_map = make_map(["S", "G", "A"], [("S", "G", 9), ("S", "A", 1)])
        for name in ALGORITHMS:
            result = run_search(name, road_map, "S", "G")
            self.assertEqual(result.expanded, ["S", "A", "G"], name)
            self.assertEqual(result.steps, 3)

    def test_alphabetical_equal_cost_routes(self):
        road_map = make_map(["S", "B", "A", "G"], [("S", "B", 1), ("S", "A", 1), ("B", "G", 1), ("A", "G", 1)])
        for name in ALGORITHMS:
            result = run_search(name, road_map, "S", "G")
            self.assertEqual(result.path, ["S", "A", "G"], name)

    def test_case_insensitive_alphabetical_order(self):
        road_map = make_map(["S", "Beta", "alpha", "G"], [("S", "Beta", 1), ("S", "alpha", 1)])
        for name in ALGORITHMS:
            self.assertEqual(run_search(name, road_map, "S", "G").expanded, ["S", "alpha", "Beta"])

    def test_bfs_preserves_fifo_between_parents(self):
        road_map = make_map(["S", "A", "Z", "B", "Y"], [("S", "Z", 1), ("S", "A", 1), ("A", "Y", 1), ("Z", "B", 1)])
        result = run_search("BFS", road_map, "S", "Y")
        self.assertEqual(result.expanded, ["S", "A", "Z", "Y"])

    def test_dfs_follows_alphabetical_branch_through_queued_city(self):
        road_map = make_map(["S", "A", "B", "G"], [("S", "B", 1), ("S", "A", 1), ("A", "B", 1), ("B", "G", 1)])
        result = run_search("DFS", road_map, "S", "G")
        self.assertEqual(result.path, ["S", "A", "B", "G"])
        self.assertEqual(result.steps, 4)

    def test_dfs_duplicate_entries_do_not_count(self):
        road_map = make_map(["S", "A", "B", "G"], [("S", "B", 1), ("S", "A", 1), ("A", "B", 1)])
        result = run_search("DFS", road_map, "S", "G")
        self.assertEqual(result.expanded, ["S", "A", "B"])
        self.assertEqual(result.steps, 3)

    def test_better_open_path_replaces_expensive_path(self):
        road_map = make_map(["S", "A", "B", "G"], [("S", "A", 10), ("S", "B", 1), ("B", "A", 1), ("A", "G", 1), ("B", "G", 20)])
        for name in ("UCS", "A*"):
            result = run_search(name, road_map, "S", "G")
            self.assertEqual((result.path, result.cost, result.steps), (["S", "B", "A", "G"], 3, 4))

    def test_stale_heap_entries_do_not_count(self):
        road_map = make_map(["S", "A", "B", "G", "T"], [("S", "A", 10), ("S", "B", 1), ("B", "A", 1), ("A", "G", 1), ("B", "G", 20)])
        for name in ("UCS", "A*"):
            result = run_search(name, road_map, "S", "T")
            self.assertFalse(result.found)
            self.assertEqual(result.expanded, ["S", "B", "A", "G"])
            self.assertEqual(result.steps, 4)

    def test_astar_ties_use_city_name_before_g(self):
        road_map = make_map(["S", "A", "B", "G"], [("S", "A", 4), ("S", "B", 1), ("A", "G", 10), ("B", "G", 10)], {"A": (1, 0), "B": (4, 0)})
        self.assertEqual(run_search("A*", road_map, "S", "G").expanded[:2], ["S", "A"])

    def test_inconsistent_admissible_heuristic_keeps_closed_cities(self):
        road_map = make_map(["S", "A", "B", "C", "G"], [("S", "A", 2), ("S", "B", 2), ("A", "C", 2), ("B", "C", 1), ("C", "G", 2)], {"B": (3, 0)})
        self.assertFalse(heuristic_is_consistent(road_map, "G"))
        result = run_search("A*", road_map, "S", "G")
        self.assert_valid_result(road_map, result, "S", "G")
        self.assertEqual(result.cost, 6)
        self.assertEqual(run_search("UCS", road_map, "S", "G").cost, 5)
        self.assertEqual(result.expanded, ["S", "A", "C", "B", "G"])

    def test_zero_cost_cycles_and_self_loops(self):
        road_map = make_map(["S", "A", "B", "G"], [("S", "S", 0), ("S", "A", 0), ("A", "B", 0), ("B", "S", 0), ("B", "G", 2)])
        for name in ALGORITHMS:
            result = run_search(name, road_map, "S", "G")
            self.assert_valid_result(road_map, result, "S", "G")
            self.assertEqual(result.cost, 2)

    def test_decimal_road_costs(self):
        road_map = make_map(["S", "A", "G"], [("S", "G", 1.75), ("S", "A", 0.5), ("A", "G", 0.75)])
        for name in ("UCS", "A*"):
            self.assertEqual(run_search(name, road_map, "S", "G").cost, 1.25)

    def test_informative_invalid_inputs(self):
        for name in ALGORITHMS:
            with self.assertRaisesRegex(ValueError, "Start and goal"):
                run_search(name, self.default_map, "Unknown", "Jenin")
        with self.assertRaisesRegex(ValueError, "Unknown algorithm"):
            run_search("Magic", self.default_map, "Jenin", "Hebron")

    def test_compare_marks_every_actual_minimum(self):
        results = compare_all(self.default_map, "Nablus", "Jerusalem")
        rows = comparison_rows(results)
        self.assertEqual([row["Algorithm"] for row in rows if row["Optimal"] == "Yes"], ["UCS", "Greedy Best-First", "A*"])

    def test_compare_does_not_mark_failed_searches(self):
        road_map = make_map(["S", "G"], [])
        rows = comparison_rows(compare_all(road_map, "S", "G"))
        self.assertTrue(all(row["Cost (km)"] is None and row["Optimal"] == "—" for row in rows))

    def test_compare_marks_same_city_zero_cost_results(self):
        rows = comparison_rows(compare_all(self.default_map, "Jenin", "Jenin"))
        self.assertTrue(all(row["Optimal"] == "Yes" and row["Steps"] == 1 for row in rows))

    def test_compare_does_not_round_different_costs_into_a_tie(self):
        rows = comparison_rows({"one": SearchResult(["S"], 1, 1, ["S"]), "two": SearchResult(["S"], 1.0000000000001, 1, ["S"])})
        self.assertEqual([row["Optimal"] for row in rows], ["Yes", "—"])

    def test_heuristic_is_floored(self):
        coordinates = {"A": (-1, -2), "B": (1, 0), "C": (2, 2)}
        self.assertEqual(heuristic(coordinates, "A", "B"), 2)
        self.assertEqual(heuristic(coordinates, "A", "C"), 5)
        self.assertEqual(heuristic(coordinates, "A", "A"), 0)


if __name__ == "__main__":
    unittest.main()

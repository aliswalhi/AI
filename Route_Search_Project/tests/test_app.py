"""Exercise real Streamlit widgets, uploads, state changes and Plotly output."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from algorithms import run_search
from app import build_network_figure
from map_utils import load_map, validate_map


PROJECT_DIR = Path(__file__).resolve().parents[1]
UPLOAD = {
    "name": "A completely different map", "unit": "km",
    "cities": [{"name": "Alpha", "x": 0, "y": 0}, {"name": "Beta", "x": 3, "y": 4}, {"name": "Gamma", "x": 9, "y": 0}],
    "roads": [{"from": "Alpha", "to": "Beta", "km": 6}],
}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(PROJECT_DIR / "app.py"), default_timeout=45).run()
        self.assertFalse(self.at.exception)

    def assert_no_exception(self):
        self.assertFalse(self.at.exception, [item.message for item in self.at.exception])

    def metric(self, label):
        return next(metric.value for metric in self.at.metric if metric.label == label)

    def upload(self, data):
        self.at.file_uploader[0].upload("custom.json", json.dumps(data).encode(), "application/json").run()
        self.assert_no_exception()

    def test_startup_default_map_and_controls(self):
        self.assertEqual(self.at.title[0].value, "AI Route Search")
        self.assertEqual(self.metric("Cities"), "11")
        self.assertEqual(self.metric("Two-way roads"), "19")
        self.assertEqual(self.at.selectbox(key="start_city").value, "Jenin")
        self.assertEqual(self.at.selectbox(key="goal_city").value, "Hebron")
        self.assertEqual(self.at.selectbox(key="algorithm").value, "A*")

    def test_find_route_nablus_jerusalem(self):
        self.at.selectbox(key="start_city").select("Nablus")
        self.at.selectbox(key="goal_city").select("Jerusalem")
        self.at.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Total distance"), "64 km")
        self.assertEqual(self.metric("Search steps"), "4")
        self.assertEqual(self.at.session_state["selected_result"].path, ["Nablus", "Ramallah", "Jerusalem"])

    def test_compare_has_five_rows_and_all_optimal_results(self):
        self.at.selectbox(key="start_city").select("Nablus")
        self.at.selectbox(key="goal_city").select("Jerusalem")
        self.at.button[1].click().run()
        self.assert_no_exception()
        rows = self.at.dataframe[0].value
        self.assertEqual(len(rows), 5)
        self.assertEqual(list(rows.loc[rows["Optimal"] == "Yes", "Algorithm"]), ["UCS", "Greedy Best-First", "A*"])

    def test_selecting_algorithm_after_compare_updates_result(self):
        self.at.button[1].click().run()
        self.at.selectbox(key="algorithm").select("BFS").run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Total distance"), "185 km")

    def test_change_city_clears_obsolete_results(self):
        self.at.button[0].click().run()
        self.at.button[1].click().run()
        self.at.selectbox(key="goal_city").select("Jenin").run()
        self.assert_no_exception()
        self.assertEqual(len(self.at.dataframe), 0)
        self.assertFalse(any(metric.label == "Total distance" for metric in self.at.metric))

    def test_upload_updates_dropdowns_and_runs_search(self):
        self.upload(UPLOAD)
        self.assertEqual(self.at.selectbox(key="start_city").options, ["Alpha", "Beta", "Gamma"])
        self.assertEqual(self.metric("Cities"), "3")
        self.assertEqual(self.metric("Two-way roads"), "1")
        self.at.selectbox(key="goal_city").select("Beta")
        for name in ("BFS", "DFS", "UCS", "Greedy Best-First", "A*"):
            self.at.selectbox(key="algorithm").select(name)
            self.at.button[0].click().run()
            self.assert_no_exception()
            self.assertEqual(self.metric("Total distance"), "6 km")

    def test_uploaded_disconnected_map_comparison(self):
        self.upload(UPLOAD)
        self.at.button[1].click().run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Total distance"), "—")
        self.assertTrue(all(value == "No route" for value in self.at.dataframe[0].value["Path"]))
        self.assertTrue(all(value == "—" for value in self.at.dataframe[0].value["Optimal"]))

    def test_bad_upload_shows_error_and_keeps_app_usable(self):
        self.at.file_uploader[0].upload("bad.json", b'{"cities": }', "application/json").run()
        self.assert_no_exception()
        self.assertTrue(any("Invalid JSON" in error.value for error in self.at.error))
        self.assertEqual(self.metric("Cities"), "11")
        self.at.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Total distance"), "144 km")

    def test_removing_upload_restores_default_and_clears_results(self):
        self.upload(UPLOAD)
        self.at.button[1].click().run()
        self.at.file_uploader[0].clear().run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Cities"), "11")
        self.assertEqual(len(self.at.dataframe), 0)

    def test_same_city_in_ui(self):
        self.at.selectbox(key="goal_city").select("Jenin")
        self.at.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(self.metric("Total distance"), "0 km")
        self.assertEqual(self.metric("Search steps"), "1")

    def test_charts_toggle_renders_without_errors(self):
        self.at.button[1].click().run()
        next(toggle for toggle in self.at.toggle if toggle.label == "Show comparison charts").set_value(True).run()
        self.assert_no_exception()
        self.assertEqual(len(self.at.get("plotly_chart")), 3)

    def test_inconsistent_upload_explains_astar_limit(self):
        data = json.loads(json.dumps(UPLOAD))
        data["cities"][1]["x"] = 100
        self.upload(data)
        self.at.selectbox(key="goal_city").select("Beta").run()
        self.assert_no_exception()
        self.assertTrue(any("heuristic is inconsistent" in item.value for item in self.at.info))


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.road_map = load_map(PROJECT_DIR / "westbank_map.json")

    def test_diagram_has_every_city_road_and_distance(self):
        figure = build_network_figure(self.road_map, "Jenin", "Hebron")
        nodes = next(trace for trace in figure.data if trace.name == "Cities")
        self.assertEqual(len(nodes.x), 11)
        self.assertEqual(len([trace for trace in figure.data if trace.name == "Roads"]), 19)
        self.assertEqual(len(figure.layout.annotations), 19)
        figure.to_json()

    def test_route_overlay_and_distinct_endpoints(self):
        result = run_search("A*", self.road_map, "Nablus", "Jerusalem")
        figure = build_network_figure(self.road_map, "Nablus", "Jerusalem", result)
        route = next(trace for trace in figure.data if trace.name == "Selected route")
        self.assertEqual(list(route.x), [self.road_map.coordinates[city][0] for city in result.path])
        start = next(trace for trace in figure.data if trace.name == "Start")
        goal = next(trace for trace in figure.data if trace.name == "Goal")
        self.assertNotEqual(start.marker.symbol, goal.marker.symbol)

    def test_single_city_and_same_coordinates(self):
        road_map = validate_map({"cities": [{"name": "Solo", "x": 0, "y": 0}], "roads": [{"from": "Solo", "to": "Solo", "km": 0}]})
        figure = build_network_figure(road_map, "Solo", "Solo", run_search("A*", road_map, "Solo", "Solo"))
        self.assertTrue(any(trace.name == "Start = goal" for trace in figure.data))
        figure.to_json()

    def test_hide_distances(self):
        figure = build_network_figure(self.road_map, "Jenin", "Hebron", show_distances=False)
        self.assertEqual(len(figure.layout.annotations), 0)

    def test_failed_route_has_no_overlay(self):
        road_map = validate_map(UPLOAD)
        result = run_search("UCS", road_map, "Alpha", "Gamma")
        figure = build_network_figure(road_map, "Alpha", "Gamma", result)
        self.assertFalse(any(trace.name == "Selected route" for trace in figure.data))


if __name__ == "__main__":
    unittest.main()

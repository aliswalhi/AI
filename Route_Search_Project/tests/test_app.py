import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from test_maps import BASE


class AppTests(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=45).run()
        self.assertFalse(self.at.exception)

    def test_search_compare_and_change_cities(self):
        self.at.selectbox(key="start_city").select("Nablus")
        self.at.selectbox(key="goal_city").select("Jerusalem")
        self.at.button[0].click().run()
        self.assertEqual(self.at.session_state["selected_result"]["cost"], 64)
        self.at.button[1].click().run()
        table = self.at.dataframe[0].value
        self.assertEqual(len(table), 5)
        self.assertEqual(list(table.loc[table["Optimal"] == "Yes", "Algorithm"]), ["UCS", "Greedy Best-First", "A*"])
        self.at.selectbox(key="algorithm").select("BFS").run()
        self.assertTrue(any(m.value == "108 km" for m in self.at.metric))
        self.at.selectbox(key="goal_city").select("Nablus").run()
        self.assertEqual(len(self.at.dataframe), 0)
        self.at.button[0].click().run()
        self.assertEqual(self.at.session_state["selected_result"]["steps"], 1)
        self.assertFalse(self.at.exception)

    def test_upload_and_restore(self):
        self.at.file_uploader[0].upload("map.json", json.dumps(BASE).encode()).run()
        self.assertEqual(self.at.selectbox(key="start_city").options, ["A", "B"])
        self.at.button[1].click().run()
        self.assertTrue(all(self.at.dataframe[0].value["Cost (km)"] == 6))
        self.at.file_uploader[0].clear().run()
        self.assertEqual(len(self.at.selectbox(key="start_city").options), 11)
        self.assertEqual(len(self.at.dataframe), 0)
        self.assertFalse(self.at.exception)

    def test_invalid_upload(self):
        self.at.file_uploader[0].upload("bad.json", b"{").run()
        self.assertTrue(self.at.error)
        self.assertEqual(len(self.at.selectbox(key="start_city").options), 11)
        self.assertFalse(self.at.exception)


if __name__ == "__main__":
    unittest.main()

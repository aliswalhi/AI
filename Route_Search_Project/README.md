# Assignment 1 — AI Route Search

A local web application for Fundamentals of Artificial Intelligence (10672224).
Explore the instructor's 11-city, 19-road West Bank graph, run five manually
implemented search strategies, and compare their routes, costs and search steps.
The supplied PDF is the source of assignment rules; the pasted project brief
provides the Python/Streamlit stack and additional interface and testing details.

## Group information

Group Number: null

Student 1: [ali swalhi] — [12241088]

Student 2: [omar soud] — [12220165]




## Technologies and files

Python 3.11+, Streamlit and Plotly. The algorithms use only the Python standard
library (`collections`, `heapq` and `math`), with ordinary dictionaries for maps
and search results. No NetworkX or
ready-made graph/search algorithm is used. The interface uses native Streamlit
widgets and its theme configuration, with no custom HTML, CSS or JavaScript.

```text
Route_Search_Project/
├── app.py                    # Streamlit controls, state, results and Plotly graph
├── algorithms.py             # BFS, DFS, UCS, Greedy and A*, plus comparison
├── map_utils.py              # JSON validation, graph, heuristic and route costs
├── westbank_map.json         # Original map from the assignment appendix
├── requirements.txt          # Pinned application dependencies
├── README.md
├── .streamlit/
│   └── config.toml           # Theme, upload limit and telemetry setting
└── tests/
    ├── test_search.py        # Search correctness and assignment rules
    ├── test_maps.py          # JSON, graph and validation checks
    └── test_app.py           # Streamlit interactions and Plotly diagram checks
```

## Install and run

Open a terminal in `Route_Search_Project`. With Python 3.11 or newer installed:

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies and start the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the Local URL printed by Streamlit (normally `http://localhost:8501`).
Keep the terminal running; press Ctrl+C to stop. If PowerShell blocks activation,
use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and
`.\.venv\Scripts\python.exe -m streamlit run app.py` instead.

**Already prepared in this workspace:** a local Python 3.12 runtime and the
installed environment are in the workspace's `.tools/` and `.venv/` directories.
From `Route_Search_Project`, this command runs without a global Python install:

```powershell
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Those setup directories are excluded from the submission archive. The archive
can be run on another computer using the normal installation steps above.


## Map format and validation

```json
{
  "name": "My map",
  "unit": "km",
  "cities": [
    { "name": "Alpha", "x": 0, "y": 0 },
    { "name": "Beta", "x": 3, "y": 4 }
  ],
  "roads": [
    { "from": "Alpha", "to": "Beta", "km": 6 }
  ]
}
```



## Algorithms

| Strategy | Frontier / priority | What the result guarantees |
| --- | --- | --- |
| BFS | FIFO queue | Fewest roads, not necessarily minimum km |
| DFS | LIFO stack | A route if reachable; no cost or hop guarantee |
| UCS | Min-heap ordered by `g(n)` | Minimum cost for nonnegative road weights |
| Greedy Best-First | Min-heap ordered by `h(n)` | A route if reachable; no cost guarantee |
| A* | Min-heap ordered by `g(n) + h(n)` | Minimum cost with a consistent heuristic |

`g(n)` is the road distance travelled from the start. Both informed strategies
use the PDF's exact heuristic:

```text
h(n) = floor(sqrt((x_n - x_goal)^2 + (y_n - y_goal)^2))
```

The code computes this with `math.floor(math.hypot(dx, dy))`.


## Tests and verified results

From this directory, using the activated environment:

```bash
python -m unittest discover -s tests -v
```

Using the environment already prepared in this workspace:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```



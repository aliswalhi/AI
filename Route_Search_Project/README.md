# Assignment 1 — AI Route Search

A local web application for Fundamentals of Artificial Intelligence (10672224).
Explore the instructor's 11-city, 19-road West Bank graph, run five manually
implemented search strategies, and compare their routes, costs and search steps.
The supplied PDF is the source of assignment rules; the pasted project brief
provides the Python/Streamlit stack and additional interface and testing details.

## Group information

Group Number: [GROUP NUMBER]

Student 1: [NAME] — [STUDENT ID]

Student 2: [NAME] — [STUDENT ID]

Student 3: [NAME] — [STUDENT ID]

Fill in your real details before submitting. The PDF permits groups of 2–3;
remove the third placeholder for a two-person group. Rename the source archive
with your actual group number, for example `G05_RouteSearch.zip`.

## Technologies and files

Python 3.11+, Streamlit and Plotly. The algorithms use only the Python standard
library (`collections`, `heapq`, `math` and `dataclasses`). No NetworkX or
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
    ├── test_search.py        # Search correctness and independent distance oracle
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

## Use the application

1. Choose **Start City** and **Goal City** in the sidebar. Any city may be either
   endpoint, including the same city for both. Options come from the loaded file.
2. Choose **BFS**, **DFS**, **UCS**, **Greedy Best-First**, or **A\***.
3. Select **Find Route**. The result shows the complete route, cost in km,
   search steps, route details and expansion order. The green line highlights
   its roads; a green diamond marks the start and an orange star marks the goal.
4. Select **Compare All Algorithms**. A five-row table shows paths, numeric
   costs, steps and every result attaining the lowest computed cost. Select a
   different algorithm to inspect its route. Optional bar charts compare effort
   and cost. Failed searches are never marked optimal.
5. Hover over cities or roads for details; drag to pan and scroll to zoom. Road
   distances are visible by default and can be hidden with the sidebar toggle.
6. Use **Upload JSON map** to load another graph. The diagram, dropdowns and
   searches update together. Removing the file restores the default map.
   An invalid upload displays its error and falls back to the default map.
   Changing maps or endpoints clears previous search/comparison results.
7. **Download active map** exports the current map in the supported JSON format.

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

Every road is inserted in both directions. City names must be nonempty, unique
without regard to case, and have no leading/trailing whitespace or control
characters. Road references must match names exactly. Coordinates and distances
must be finite JSON numbers, not strings or booleans; negative coordinates are
allowed, and road costs must be nonnegative. A numeric magnitude limit of `1e100`
keeps derived calculations finite. Files are UTF-8 JSON, optionally with a BOM,
up to 5 MB. `name` and `unit` are optional; their defaults are `Uploaded road map`
and `km`. An explicit unit must be `km`.

The cities list must contain at least one city. An empty roads list, isolated
cities, zero-cost roads and self-loops are supported. Repeated undirected roads
are rejected, including reversed duplicates, so no distance is silently replaced.
For distinct cities at identical coordinates, nodes overlap; hover and pan/zoom
remain available, but this coordinate-driven diagram does not move those cities.

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

### Assignment conventions and ambiguities

- **Goal test:** performed when the city is removed from the frontier, never
  while generating a neighbor.
- **Steps:** each first valid removal is recorded in `expanded`, including the
  goal whose neighbors need not be generated. Therefore a start equal to the
  goal returns `[start]`, 0 km and **1 step**. The PDF does not explicitly say
  whether to count the goal; this project consistently uses this convention.
- **Graph search:** no city expands twice. Failed searches return `[]`, no
  numeric cost (`None`), and the number of cities actually expanded.
- **Alphabetical ties:** case-insensitive alphabetical comparison, with exact
  spelling as the last tie-breaker. BFS inserts alphabetical neighbors while
  preserving FIFO order between parents. DFS pushes them in reverse order for
  alphabetical removal. Priority queues order equal priorities by city name
  before any other field. An equal-cost alternative retains its first path;
  the rules do not request lexicographic ordering of complete paths.
- **DFS duplicates:** cities close on removal. A queued city can be reached
  through the current deeper branch. Each stack entry owns its path; a later
  duplicate is skipped after the city closes and adds no step.
- **UCS/A* updates:** improving an open city's `g` inserts a new heap entry.
  Entries with obsolete costs or already-closed cities are skipped without
  changing the steps. Best-cost checks use strict improvement, so zero-cost
  cycles cannot create endlessly updated entries.
- **A* reopening:** the PDF says never expand a city twice, while the longer
  brief also mentions reopening. These conflict for inconsistent heuristics.
  The PDF takes precedence: closed cities stay closed. The uploaded heuristic
  is checked for consistency for the selected goal, and the app explains when
  A* loses its minimum-cost guarantee. Merely admissible but inconsistent
  heuristics are not enough for this implementation's guarantee. UCS remains
  the minimum-cost reference. The default heuristic is consistent for all goals.
- **Optimal table labels:** compare actual unrounded computed costs, not
  algorithm names or rounded display strings. All tied minimum results are
  marked, including BFS/DFS/Greedy when they achieve that cost.

## Tests and verified results

From this directory, using the activated environment:

```bash
python -m unittest discover -s tests -v
```

Using the environment already prepared in this workspace:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite contains **59 tests**. One checks all **121 ordered city pairs** through
all five searches (**605 search results**), verifying route edges, costs, unique
expansions, endpoints and step counts. UCS and A* are checked against a separate
Floyd-Warshall distance calculation. Other tests cover the four requested routes,
exact steps, same-city and unreachable searches, alphabetical ties, equal-cost
alternatives, better frontier paths, stale entries, zero-cost cycles, decimal
weights, inconsistent heuristics, malformed JSON and uploaded maps.

Streamlit AppTest exercises real controls: startup, searches, comparison, all
five algorithms on an upload, invalid uploads, removing uploads, disconnected
maps, chart toggles, changing algorithms/endpoints and same-city inputs. Plotly
checks verify city/road/distance coverage, route overlays and endpoint symbols.

For **Nablus → Jerusalem**, the verified results are:

| Algorithm | Route | Cost (km) | Steps | Optimal |
| --- | --- | ---: | ---: | --- |
| BFS | Nablus → Jericho → Jerusalem | 108 | 10 | — |
| DFS | Nablus → Jenin → Tubas → Jericho → Bethlehem → Jerusalem | 194 | 7 | — |
| UCS | Nablus → Ramallah → Jerusalem | 64 | 8 | Yes |
| Greedy Best-First | Nablus → Ramallah → Jerusalem | 64 | 3 | Yes |
| A* | Nablus → Ramallah → Jerusalem | 64 | 4 | Yes |

Additional minimum-cost checks: Jenin → Hebron **144 km**,
Ramallah → Jericho **40 km**, and Bethlehem → Nablus **74 km**.

The application was also started as a real local Streamlit server; the root
page returned HTTP 200 and `/_stcore/health` returned `ok`.
Headless Chrome also rendered the live Plotly network, clicked **Find Route**
and verified the 144 km result, then clicked **Compare All Algorithms** and
verified that the comparison table rendered.

## Demo preparation

Each member should be ready to explain these questions:

1. **Why can BFS choose 108 km when 64 km is available?** Both routes have two
   roads; BFS follows FIFO discovery and alphabetical neighbors, not road costs.
2. **Why does DFS reverse the neighbor ordering?** A stack removes the last
   inserted item, so reverse insertion visits alphabetical neighbors first.
3. **Why test the goal on removal?** A generated goal may have an expensive
   tentative route; UCS/A* must first select a valid frontier entry by priority.
4. **Why are steps different from route length?** Steps measure visited search
   states, including explored branches; route length measures only final roads.
5. **What makes A* optimal here?** Nonnegative weights, the consistent heuristic,
   lowest-f selection and correct updates to the best cost of open cities.
6. **Can A* fail on another map?** Yes: arbitrary coordinates can produce an
   inconsistent or overestimating heuristic. Closed cities cannot reopen under
   the assignment rules; compare against UCS and explain the displayed notice.
7. **What happens to a stale heap entry?** It is removed and skipped if its city
   closed already or its stored cost no longer equals the best open cost.
8. **Why is Greedy sometimes marked optimal?** Optimal labels describe this
   result's actual cost, even when the algorithm has no general cost guarantee.
9. **How do new cities become available?** JSON validation builds coordinates
   and both directions of every road; controls and the diagram use that data.
10. **How are disconnected cities handled?** The frontier empties, the search
    returns no route or cost, and the interface reports the measured steps.

## Scope

This is a local teaching tool for small road networks. It has no external map
service, live traffic, road-access data, accounts or hosted backend. Coordinates
and distances are the assignment's simplified data. Every frontier entry keeps
its path for clarity, which uses more memory than parent pointers on huge graphs.

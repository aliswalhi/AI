"""Streamlit interface and Plotly diagram for the route-search assignment."""

from html import escape
import json
import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from algorithms import ALGORITHMS, compare_all, comparison_rows, run_search
from map_utils import (
    MapValidationError, alphabetical, format_distance,
    heuristic, heuristic_is_consistent, load_map, map_to_dict, parse_map,
)


PROJECT_DIR = Path(__file__).resolve().parent
GREEN = "#17785D"
ORANGE = "#D98835"

ALGORITHM_NOTES = {
    "BFS": ("Breadth-First Search", "Visits the shallowest routes first using a FIFO queue. Finds the fewest roads, which may differ from the shortest distance."),
    "DFS": ("Depth-First Search", "Follows one branch at a time using a LIFO stack. Reverse alphabetical insertion makes the first alphabetical neighbor come out first."),
    "UCS": ("Uniform Cost Search", "Chooses the lowest cost so far, g(n). Finds a minimum-cost route because road distances are nonnegative."),
    "Greedy Best-First": ("Greedy Best-First Search", "Chooses the city with the smallest straight-line estimate, h(n). Ignores the distance already travelled, so the route may cost more."),
    "A*": ("A* Search", "Balances distance travelled and distance estimated: f(n) = g(n) + h(n). Finds a minimum-cost route when the heuristic is consistent."),
}


def build_network_figure(
    road_map, start, goal, result=None,
    show_distances=True,
):
    """Draw the supplied coordinates, with separate road, route and city layers."""
    figure = go.Figure()
    route = result['path'] if result and result['path'] else []
    selected_edges = {frozenset((a, b)) for a, b in zip(route, route[1:])}
    positions = road_map['coordinates']
    all_x = [point[0] for point in positions.values()]
    all_y = [point[1] for point in positions.values()]
    span = max(max(all_x) - min(all_x), max(all_y) - min(all_y), 1)
    road_labels = []

    for index, (source, target, distance) in enumerate(road_map['roads']):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        selected = frozenset((source, target)) in selected_edges
        label = f"{escape(source)} ↔ {escape(target)}<br>{format_distance(distance)} km"
        figure.add_trace(go.Scatter(
            x=[x1, (x1 + x2) / 2, x2], y=[y1, (y1 + y2) / 2, y2],
            mode="lines", line={"color": "#B5C6BD", "width": 2},
            text=[label] * 3, hovertemplate="%{text}<extra></extra>",
            name="Roads", legendgroup="roads", showlegend=index == 0,
        ))
        if show_distances:
            length = math.hypot(x2 - x1, y2 - y1) or 1
            offset = span * 0.012
            label_x = (x1 + x2) / 2 - (y2 - y1) / length * offset
            label_y = (y1 + y2) / 2 + (x2 - x1) / length * offset
            distance_text = f"{format_distance(distance)} km"
            road_labels.append((label_x, label_y, len(distance_text) * span * 0.005))
            figure.add_annotation(
                x=label_x, y=label_y,
                text=distance_text, showarrow=False,
                font={"size": 10, "color": GREEN if selected else "#62776C"},
                bgcolor="#F7F8F4", borderpad=2,
            )

    if route:
        figure.add_trace(go.Scatter(
            x=[positions[city][0] for city in route],
            y=[positions[city][1] for city in route],
            mode="lines", line={"color": GREEN, "width": 5},
            name="Selected route", hoverinfo="skip",
        ))

    cities = list(positions)
    center_x = (min(all_x) + max(all_x)) / 2

    def city_label_position(city):
        # Keep this positioning to preserve the map.
        # Estimate text bounds in coordinate units to avoid nearby distance labels.
        x, y = positions[city]
        half_width = len(city) * span * 0.006
        shift = span * 0.02 + half_width
        candidates = [
            ("middle left", x - shift, y), ("middle right", x + shift, y),
            ("top center", x, y + span * 0.03), ("bottom center", x, y - span * 0.03),
        ]
        if x >= center_x:
            candidates[0], candidates[1] = candidates[1], candidates[0]

        def overlaps(candidate):
            _, label_x, label_y = candidate
            return sum(
                abs(label_x - road_x) < half_width + road_width
                and abs(label_y - road_y) < span * 0.027
                for road_x, road_y, road_width in road_labels
            )

        return min(candidates, key=overlaps)[0]

    hover_labels = [
        f"{escape(city)}<br>{len(road_map['graph'][city])} road connections"
        f"<br>h to {escape(goal)} = {heuristic(positions, city, goal)} km"
        for city in cities
    ]
    figure.add_trace(go.Scatter(
        x=all_x, y=all_y, mode="markers+text", text=[escape(city) for city in cities],
        textposition=[city_label_position(city) for city in cities],
        textfont={"size": 12, "color": "#193C33"},
        marker={"size": 12, "color": "#FFFFFF", "line": {"color": "#678B78", "width": 2}},
        customdata=hover_labels, hovertemplate="%{customdata}<extra></extra>",
        name="Cities", showlegend=False, cliponaxis=False,
    ))
    if route:
        figure.add_trace(go.Scatter(
            x=[positions[city][0] for city in route],
            y=[positions[city][1] for city in route], mode="markers",
            marker={"size": 11, "color": GREEN}, hoverinfo="skip", showlegend=False,
        ))

    endpoints = [(start, "Start", "diamond", GREEN), (goal, "Goal", "star", ORANGE)]
    if start == goal:
        endpoints = [(start, "Start = goal", "diamond", "#7964A7")]
    for city, label, symbol, color in endpoints:
        x, y = positions[city]
        figure.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers", name=label,
            marker={"size": 18, "color": color, "symbol": symbol, "line": {"color": "white", "width": 2}},
            text=[f"{label}: {escape(city)}"], hovertemplate="%{text}<extra></extra>",
        ))

    padding = span * 0.17
    figure.update_layout(
        height=650, margin={"l": 20, "r": 20, "t": 16, "b": 45},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#193C33"},
        xaxis={"visible": False, "range": [min(all_x) - padding, max(all_x) + padding]},
        yaxis={"visible": False, "range": [min(all_y) - padding / 2, max(all_y) + padding / 2], "scaleanchor": "x", "scaleratio": 1},
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.03, "yanchor": "top", "font": {"size": 11}},
        hoverlabel={"bgcolor": "white", "font_size": 12},
        dragmode="pan", uirevision=road_map['name'],
    )
    return figure


def render_result(result, algorithm, start, goal):
    with st.container(border=True):
        st.caption("YOUR SEARCH")
        st.subheader(ALGORITHM_NOTES[algorithm][0])
        st.caption(ALGORITHM_NOTES[algorithm][1])
        st.divider()
        if result is None:
            st.info("Choose your cities and select Find Route to begin.")
            st.text(f"{start} → {goal}")
            return

        distance_column, steps_column = st.columns(2)
        distance_column.metric("Total distance", f"{format_distance(result['cost'])} km" if result['path'] else "—")
        steps_column.metric("Search steps", result['steps'])
        st.caption("Steps count unique frontier removals, including the goal.")
        if result['path']:
            st.success("Route found")
            st.text(" → ".join(result['path']))
            with st.expander(f"Route details · {len(result['path']) - 1} roads"):
                for index, city in enumerate(result['path'], 1):
                    st.text(f"{index:02d}  {city}")
        else:
            st.warning(f"No route connects {start} to {goal} in this map.")
        with st.expander("Inspect expansion order"):
            st.text(" → ".join(result['expanded']))
            st.caption("Duplicate and stale frontier entries are skipped without adding steps.")


def main():
    st.set_page_config(page_title="AI Route Search", page_icon="🧭", layout="wide")

    with st.sidebar:
        st.title("Route planner")
        st.caption("A small map. Five ways to explore it.")
        uploaded = st.file_uploader("Upload JSON map", type=["json"], key="map_upload", help="Use the cities / roads format in the default map. Maximum 5 MB.")
        try:
            default_map = load_map(PROJECT_DIR / "westbank_map.json")
        except MapValidationError as error:
            st.error(str(error))
            st.stop()
        road_map = default_map
        if uploaded is not None:
            try:
                if uploaded.size > 5 * 1024 * 1024:
                    raise MapValidationError("Map files must be 5 MB or smaller.")
                road_map = parse_map(uploaded.getvalue())
            except MapValidationError as error:
                st.error(str(error))
                st.caption("The default map is active. Correct the file and upload it again.")

        payload = json.dumps(map_to_dict(road_map), sort_keys=True, ensure_ascii=False)
        cities = sorted(road_map['graph'], key=alphabetical)
        if st.session_state.get("map_data") != payload:
            st.session_state["map_data"] = payload
            st.session_state["map_version"] = st.session_state.get("map_version", 0) + 1
            # Derive defaults from the file, not from hardcoded city names.
            st.session_state["start_city"] = next(iter(road_map['coordinates']))
            st.session_state["goal_city"] = next(reversed(road_map['coordinates']))

        st.divider()
        start = st.selectbox("Start City", cities, key="start_city")
        goal = st.selectbox("Goal City", cities, key="goal_city")
        algorithm = st.selectbox("Algorithm", ALGORITHMS, index=4, key="algorithm")

        map_key = st.session_state["map_version"]
        context = (map_key, start, goal)
        if st.session_state.get("search_context") != context:
            st.session_state["search_context"] = context
            for key in ("selected_result", "selected_algorithm", "comparison"):
                st.session_state.pop(key, None)

        find_clicked = st.button("Find Route", type="primary", width="stretch")
        compare_clicked = st.button("Compare All Algorithms", width="stretch")
        st.divider()
        show_distances = st.toggle("Show road distances", value=True)
        st.download_button("Download active map", payload, file_name="road_map.json", mime="application/json", width="stretch")
        st.caption("All roads are two-way. Distances and coordinates are in kilometres.")

    if find_clicked:
        st.session_state["selected_result"] = run_search(algorithm, road_map, start, goal)
        st.session_state["selected_algorithm"] = algorithm
    if compare_clicked:
        st.session_state["comparison"] = compare_all(road_map, start, goal)
    comparison = st.session_state.get("comparison")
    result = comparison[algorithm] if comparison else None
    if st.session_state.get("selected_algorithm") == algorithm:
        result = st.session_state.get("selected_result")

    st.caption("FUNDAMENTALS OF ARTIFICIAL INTELLIGENCE  /  ASSIGNMENT 01")
    st.title("AI Route Search")
    st.write("Explore and Compare Artificial Intelligence Search Algorithms")
    st.divider()
    name_column, cities_column, roads_column, algorithms_column = st.columns([3, 1, 1, 1])
    name_column.caption("ACTIVE ROAD NETWORK")
    name_column.write(road_map['name'])
    cities_column.metric("Cities", len(cities))
    roads_column.metric("Two-way roads", len(road_map['roads']))
    algorithms_column.metric("Algorithms", len(ALGORITHMS))

    if (algorithm == "A*" or comparison) and not heuristic_is_consistent(road_map, goal):
        st.info("For this goal, the coordinate heuristic is inconsistent. A* keeps expanded cities closed under the assignment rules, so a minimum-cost route is not guaranteed. Compare with UCS to check the cost.")

    map_column, result_column = st.columns([1.8, 1], gap="large")
    with map_column:
        st.subheader("Explore the network")
        st.caption("Drag to pan · scroll to zoom · hover to inspect cities and roads")
        st.plotly_chart(
            build_network_figure(road_map, start, goal, result, show_distances),
            width="stretch", config={"displaylogo": False, "scrollZoom": True, "toImageButtonOptions": {"filename": "route-search"}},
            key=f"network_{map_key}",
        )
    with result_column:
        st.write("")
        render_result(result, algorithm, start, goal)
        with st.expander("How are choices made?"):
            st.write("BFS uses FIFO order and alphabetical neighbors. DFS reverse-pushes neighbors. Priority queues break equal priorities by city name, without regard to case.")
            st.code("h(n) = floor(sqrt((x_n - x_goal)² + (y_n - y_goal)²))", language=None)
            st.write("The goal is checked on removal from the frontier. Each city can count as a search step once.")

    st.divider()
    st.subheader("Compare the five strategies")
    st.caption("Use Compare All Algorithms to run every strategy on the same start and goal.")
    if comparison:
        rows = comparison_rows(comparison)
        st.dataframe(
            rows, hide_index=True, width="stretch",
            column_config={
                "Algorithm": st.column_config.TextColumn(width="small"),
                "Path": st.column_config.TextColumn(width="large"),
                "Cost (km)": st.column_config.NumberColumn(format="%.6g"),
                "Steps": st.column_config.NumberColumn(format="%d"),
            },
        )
        if any(item['path'] for item in comparison.values()):
            st.caption("Optimal = lowest computed cost. Every result sharing that cost is marked. UCS supplies the minimum-cost reference.")
        else:
            st.info("No algorithm found a route. The selected cities are disconnected.")
        st.caption("Select a different algorithm in the sidebar to inspect its route on the network.")
        if st.toggle("Show comparison charts", value=False):
            cost_column, steps_column = st.columns(2)
            for column, field, title, color in (
                (cost_column, "Cost (km)", "Route cost (km)", GREEN),
                (steps_column, "Steps", "Search steps", ORANGE),
            ):
                chart = go.Figure(go.Bar(x=[row["Algorithm"] for row in rows], y=[row[field] for row in rows], marker_color=color))
                chart.update_layout(title=title, height=280, margin={"l": 20, "r": 10, "t": 45, "b": 30}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                column.plotly_chart(chart, width="stretch")
    else:
        st.info("Ready when you are: compare routes, distances and search effort in one table.")

    with st.expander("Algorithm guide & assignment conventions"):
        for name, (title, description) in ALGORITHM_NOTES.items():
            st.write(f"**{title}**")
            st.write(description)
        st.write("Start equals goal returns a one-city path, 0 km and 1 step. A failed search has no path or cost, but still reports its expanded cities. The final path's road count is separate from search steps.")
        st.write("This is a simplified teaching diagram. It does not describe current road access or real-world travel conditions.")
    st.caption("Assignment 1 · Route Search Web App · Python / Streamlit / Plotly")


if __name__ == "__main__":
    main()

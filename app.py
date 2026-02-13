import heapq
import json
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

ROUTES_FILE = Path(__file__).with_name("airline_routes.json")


def estimate_total_price(total_km, legs):
    base_fare = 35
    per_km = 0.11
    leg_fee = 25
    return round(base_fare + (total_km * per_km) + (legs * leg_fee), 2)


def load_airport_graph():
    with ROUTES_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    airports = {}
    graph = {}

    for code, info in raw.items():
        display_name = info.get("display_name") or info.get("name") or code
        airports[code] = display_name
        graph[code] = []

    for src, info in raw.items():
        for route in info.get("routes", []):
            dst = route.get("iata")
            km = route.get("km")
            if not dst or dst not in graph or not isinstance(km, (int, float)):
                continue
            graph[src].append({"to": dst, "distance": float(km)})

    airports = dict(sorted(airports.items(), key=lambda item: item[0]))
    return airports, graph


def shortest_path(graph, src, dst, mode):
    if src not in graph or dst not in graph:
        return None

airports, route_graph = load_airport_graph()


@app.get("/")
def index():
    return render_template("index.html", airports=airports)


@app.post("/search")
def search():
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()

    if not src or not dst or src == dst:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            result={"best": None, "routes": []},
        )

    best = shortest_path(route_graph, src, dst, mode)

    # Provide a small set of alternatives for the results table.
    candidates = []
    for m in ("distance", "price", "stops"):
        route = shortest_path(route_graph, src, dst, m)
        if route and route["route"] not in [r["route"] for r in candidates]:
            candidates.append(route)

    if best and best["route"] not in [r["route"] for r in candidates]:
        candidates.insert(0, best)

    result = {"best": best, "routes": candidates}
    return render_template("results.html", src=src, dst=dst, mode=mode, result=result)


if __name__ == "__main__":
    app.run(debug=True)

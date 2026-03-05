import heapq
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

ROUTES_FILE = Path(__file__).with_name("airline_routes.json")
USE_MOCK_RESULTS = True


def estimate_total_price(total_km, legs):
    base_fare = 35
    per_km = 0.11
    leg_fee = 25
    return round(base_fare + (total_km * per_km) + (legs * leg_fee), 2)


def estimate_leg_minutes(distance_km):
    cruise_speed_kmh = 850.0
    block_buffer_min = 18
    return max(30, int(round((distance_km / cruise_speed_kmh) * 60 + block_buffer_min)))


def minutes_to_human(total_minutes):
    total_minutes = int(round(total_minutes))
    hours, mins = divmod(total_minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def load_airport_graph():
    with ROUTES_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    airports = {}
    airport_meta = {}
    graph = {}

    for code, info in raw.items():
        display_name = info.get("display_name") or info.get("name") or code
        airports[code] = display_name
        try:
            latitude = float(info.get("latitude")) if info.get("latitude") is not None else None
            longitude = float(info.get("longitude")) if info.get("longitude") is not None else None
        except (TypeError, ValueError):
            latitude = None
            longitude = None
        airport_meta[code] = {
            "code": code,
            "display_name": display_name,
            "name": info.get("name") or display_name,
            "city_name": info.get("city_name") or "",
            "country": info.get("country") or "",
            "timezone": info.get("timezone") or "",
            "latitude": latitude,
            "longitude": longitude,
        }
        graph[code] = []

    for src, info in raw.items():
        for route in info.get("routes", []):
            dst = route.get("iata")
            km = route.get("km")
            if not dst or dst not in graph or not isinstance(km, (int, float)):
                continue
            minutes = route.get("min")
            if not isinstance(minutes, (int, float)):
                minutes = estimate_leg_minutes(float(km))
            carriers = [
                c.get("name")
                for c in route.get("carriers", [])
                if isinstance(c, dict) and c.get("name")
            ]
            graph[src].append(
                {
                    "to": dst,
                    "distance": float(km),
                    "minutes": float(minutes),
                    "carriers": carriers,
                }
            )

    airports = dict(sorted(airports.items(), key=lambda item: item[0]))
    return airports, graph, airport_meta


def shortest_path(graph, airport_meta, src, dst, mode):
    if src not in graph or dst not in graph:
        return None

    if mode not in {"distance", "price", "stops"}:
        mode = "distance"

    def edge_weight(edge):
        if mode == "price":
            return edge["distance"] * 0.11 + 25
        if mode == "stops":
            return 1.0
        return edge["distance"]

    queue = [(0.0, src)]
    costs = {src: 0.0}
    prev = {}

    while queue:
        current_cost, node = heapq.heappop(queue)
        if current_cost > costs.get(node, float("inf")):
            continue
        if node == dst:
            break
        for edge in graph[node]:
            nxt = edge["to"]
            new_cost = current_cost + edge_weight(edge)
            if new_cost < costs.get(nxt, float("inf")):
                costs[nxt] = new_cost
                prev[nxt] = (node, edge)
                heapq.heappush(queue, (new_cost, nxt))

    if dst not in costs:
        return None

    route = [dst]
    edges = []
    cursor = dst
    while cursor != src:
        prev_node, edge = prev[cursor]
        edges.append((prev_node, cursor, edge))
        cursor = prev_node
        route.append(cursor)
    route.reverse()
    edges.reverse()

    legs = []
    map_points = []
    total_distance = 0.0
    flight_minutes = 0.0
    for idx, (from_code, to_code, edge) in enumerate(edges, start=1):
        total_distance += edge["distance"]
        flight_minutes += edge["minutes"]
        from_meta = airport_meta.get(from_code, {})
        to_meta = airport_meta.get(to_code, {})
        legs.append(
            {
                "leg_number": idx,
                "from": from_code,
                "to": to_code,
                "from_name": from_meta.get("display_name", from_code),
                "to_name": to_meta.get("display_name", to_code),
                "distance_km": round(edge["distance"], 1),
                "duration_min": int(round(edge["minutes"])),
                "duration_label": minutes_to_human(edge["minutes"]),
                "carrier_names": edge.get("carriers", []),
            }
        )

    for seq, code in enumerate(route, start=1):
        meta = airport_meta.get(code, {})
        lat = meta.get("latitude")
        lon = meta.get("longitude")
        if lat is None or lon is None:
            continue
        map_points.append(
            {
                "seq": seq,
                "code": code,
                "label": meta.get("display_name", code),
                "lat": lat,
                "lon": lon,
            }
        )

    return finalize_result(route, legs, map_points, mode)


def finalize_result(route, legs, map_points, mode):
    total_distance = sum(leg["distance_km"] for leg in legs)
    flight_minutes = sum(leg["duration_min"] for leg in legs)
    stops = max(0, len(route) - 2)
    layover_minutes = stops * 45
    total_travel_minutes = int(round(flight_minutes + layover_minutes))
    departure_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    arrival_utc = departure_utc + timedelta(minutes=total_travel_minutes)
    avg_speed = (total_distance / (flight_minutes / 60.0)) if flight_minutes else 0.0

    price = estimate_total_price(total_distance, len(legs))
    if mode == "price":
        price = round(price * 0.84, 2)
    elif mode == "stops":
        price = round(price * 1.07, 2)

    return {
        "route": route,
        "distance": int(round(total_distance)),
        "distance_exact": round(total_distance, 1),
        "price": price,
        "stops": stops,
        "legs": legs,
        "map_points": map_points,
        "flight_minutes": int(round(flight_minutes)),
        "flight_time_label": minutes_to_human(flight_minutes),
        "layover_minutes": layover_minutes,
        "layover_time_label": minutes_to_human(layover_minutes),
        "total_travel_minutes": total_travel_minutes,
        "total_travel_label": minutes_to_human(total_travel_minutes),
        "departure_utc": departure_utc.isoformat(),
        "arrival_utc": arrival_utc.isoformat(),
        "avg_speed_kmh": int(round(avg_speed)),
        "mode": mode,
        "mock": True,
    }


def build_mock_result_for_route(route_codes, airport_meta, mode):
    legs = []
    map_points = []

    for seq, code in enumerate(route_codes, start=1):
        meta = airport_meta.get(code, {})
        map_points.append(
            {
                "seq": seq,
                "code": code,
                "label": meta.get("display_name", code),
                "lat": meta.get("latitude"),
                "lon": meta.get("longitude"),
            }
        )

    for idx in range(len(route_codes) - 1):
        from_code = route_codes[idx]
        to_code = route_codes[idx + 1]
        from_meta = airport_meta.get(from_code, {})
        to_meta = airport_meta.get(to_code, {})
        lat1 = from_meta.get("latitude")
        lon1 = from_meta.get("longitude")
        lat2 = to_meta.get("latitude")
        lon2 = to_meta.get("longitude")

        if None not in (lat1, lon1, lat2, lon2):
            distance = round(haversine_km(lat1, lon1, lat2, lon2), 1)
        else:
            distance = 900 + (idx * 260)

        duration = estimate_leg_minutes(distance)
        if mode == "price":
            duration += 10

        legs.append(
            {
                "leg_number": idx + 1,
                "from": from_code,
                "to": to_code,
                "from_name": from_meta.get("display_name", from_code),
                "to_name": to_meta.get("display_name", to_code),
                "distance_km": distance,
                "duration_min": duration,
                "duration_label": minutes_to_human(duration),
                "carrier_names": ["Demo Airways", "Codex Connect"],
            }
        )

    return finalize_result(route_codes, legs, map_points, mode)


def build_mock_results(src, dst, airport_meta):
    codes = list(airport_meta.keys())
    if not codes:
        return {"distance": None, "price": None, "stops": None}

    src_code = src if src in airport_meta else "SIN" if "SIN" in airport_meta else codes[0]
    dst_code = dst if dst in airport_meta and dst != src_code else "LHR" if "LHR" in airport_meta else codes[-1]

    preferred_hubs = ["DXB", "DOH", "AMS", "HND", "CDG", "JFK", "LAX", "IST"]
    hubs = [h for h in preferred_hubs if h in airport_meta and h not in {src_code, dst_code}]
    if not hubs:
        hubs = [c for c in codes if c not in {src_code, dst_code}]

    primary_hub = hubs[0] if hubs else dst_code
    secondary_hub = hubs[1] if len(hubs) > 1 else primary_hub

    routes_by_mode = {
        "distance": [src_code, primary_hub, dst_code],
        "price": [src_code, secondary_hub, dst_code],
        "stops": [src_code, dst_code],
    }

    results = {}
    for mode_name, route_codes in routes_by_mode.items():
        cleaned_route = [route_codes[0]]
        for code in route_codes[1:]:
            if code != cleaned_route[-1]:
                cleaned_route.append(code)
        if len(cleaned_route) < 2:
            cleaned_route = [src_code, dst_code]
        results[mode_name] = build_mock_result_for_route(cleaned_route, airport_meta, mode_name)
    return results


airports, route_graph, airport_meta = load_airport_graph()


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

    if USE_MOCK_RESULTS:
        mock_results = build_mock_results(src, dst, airport_meta)
        best = mock_results.get(mode) or mock_results.get("distance")
        candidates = [mock_results[m] for m in ("distance", "price", "stops") if mock_results.get(m)]
    else:
        best = shortest_path(route_graph, airport_meta, src, dst, mode)
        candidates = []
        for m in ("distance", "price", "stops"):
            route = shortest_path(route_graph, airport_meta, src, dst, m)
            if route and route["route"] not in [r["route"] for r in candidates]:
                candidates.append(route)
        if best and best["route"] not in [r["route"] for r in candidates]:
            candidates.insert(0, best)

    result = {"best": best, "routes": candidates}
    return render_template("results.html", src=src, dst=dst, mode=mode, result=result)


if __name__ == "__main__":
    app.run(debug=True)

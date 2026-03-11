import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dijkstra import Dijkstra
from loadDataset import WeightedGraph
from yen import Yen


class RouteService:
    def __init__(self, routes_file: Path):
        self.routes_file = routes_file
        self.airports = {}
        self.airport_meta = {}
        self.weighted_graph = WeightedGraph()
        self.dijkstra_solver = None
        self.yen_solver = None
        self._load_routing_context()

    def _load_routing_context(self):
        with self.routes_file.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        airports = {}
        airport_meta = {}

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

        self.weighted_graph.build_graph_from_data(raw)
        self.airports = dict(sorted(airports.items(), key=lambda item: item[0]))
        self.airport_meta = airport_meta
        self.dijkstra_solver = Dijkstra(self.weighted_graph)
        self.yen_solver = Yen(self.weighted_graph, dijkstra=self.dijkstra_solver)

    def estimate_total_price(self, total_km, legs):
        base_fare = 35
        per_km = 0.11
        leg_fee = 25
        return round(base_fare + (total_km * per_km) + (legs * leg_fee), 2)

    def estimate_leg_minutes(self, distance_km):
        cruise_speed_kmh = 850.0
        block_buffer_min = 18
        return max(30, int(round((distance_km / cruise_speed_kmh) * 60 + block_buffer_min)))

    def minutes_to_time(self, total_minutes):
        total_minutes = int(round(total_minutes))
        hours, mins = divmod(total_minutes, 60)
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"

    def haversine_km(self, lat1, lon1, lat2, lon2):
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

    def _build_result_from_route(self, route_codes, mode):
        if not route_codes or len(route_codes) < 2:
            return None

        legs = []
        map_points = []

        for idx in range(len(route_codes) - 1):
            from_code = route_codes[idx]
            to_code = route_codes[idx + 1]
            edge = self.weighted_graph.graph.get(from_code, {}).get(to_code, {})

            distance = edge.get("distance")
            if not isinstance(distance, (int, float)) or distance <= 0:
                from_meta = self.airport_meta.get(from_code, {})
                to_meta = self.airport_meta.get(to_code, {})
                lat1 = from_meta.get("latitude")
                lon1 = from_meta.get("longitude")
                lat2 = to_meta.get("latitude")
                lon2 = to_meta.get("longitude")
                if None not in (lat1, lon1, lat2, lon2):
                    distance = self.haversine_km(lat1, lon1, lat2, lon2)
                else:
                    distance = 0

            minutes = edge.get("time")
            if not isinstance(minutes, (int, float)) or minutes <= 0:
                minutes = self.estimate_leg_minutes(float(distance))

            carriers = edge.get("carriers", [])
            if not isinstance(carriers, list):
                carriers = []

            from_meta = self.airport_meta.get(from_code, {})
            to_meta = self.airport_meta.get(to_code, {})
            legs.append(
                {
                    "leg_number": idx + 1,
                    "from": from_code,
                    "to": to_code,
                    "from_name": from_meta.get("display_name", from_code),
                    "to_name": to_meta.get("display_name", to_code),
                    "distance_km": round(float(distance), 1),
                    "duration_min": int(round(float(minutes))),
                    "duration_label": self.minutes_to_time(minutes),
                    "carrier_names": carriers,
                }
            )

        for seq, code in enumerate(route_codes, start=1):
            meta = self.airport_meta.get(code, {})
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

        return self._finalize_result(route_codes, legs, map_points, mode)

    def _pick_best_route(self, results, mode):
        if not results:
            return None
        if mode == "price":
            return min(results, key=lambda route: route.get("price", float("inf")))
        if mode == "stops":
            return min(
                results,
                key=lambda route: (
                    route.get("stops", float("inf")),
                    route.get("distance_exact", float("inf")),
                ),
            )
        return min(results, key=lambda route: route.get("distance_exact", float("inf")))

    def _finalize_result(self, route, legs, map_points, mode):
        total_distance = sum(leg["distance_km"] for leg in legs)
        flight_minutes = sum(leg["duration_min"] for leg in legs)
        stops = max(0, len(route) - 2)
        layover_minutes = stops * 45
        total_travel_minutes = int(round(flight_minutes + layover_minutes))
        departure_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        arrival_utc = departure_utc + timedelta(minutes=total_travel_minutes)
        avg_speed = (total_distance / (flight_minutes / 60.0)) if flight_minutes else 0.0

        price = self.estimate_total_price(total_distance, len(legs))
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
            "flight_time_label": self.minutes_to_time(flight_minutes),
            "layover_minutes": layover_minutes,
            "layover_time_label": self.minutes_to_time(layover_minutes),
            "total_travel_minutes": total_travel_minutes,
            "total_travel_label": self.minutes_to_time(total_travel_minutes),
            "departure_utc": departure_utc.isoformat(),
            "arrival_utc": arrival_utc.isoformat(),
            "avg_speed_kmh": int(round(avg_speed)),
            "mode": mode,
            "mock": False,
        }

    def compute_algorithm_results(self, source_code, destination_code, mode):
        if source_code not in self.weighted_graph.graph or destination_code not in self.weighted_graph.graph:
            return {"best": None, "routes": []}

        selected_mode = mode if mode in ("distance", "price", "stops") else "distance"
        shortest_path_codes, _, _ = self.dijkstra_solver.findShortestPath(source_code, destination_code)
        if not shortest_path_codes:
            return {"best": None, "routes": []}

        # Best route is always computed from Dijkstra shortest path only.
        best = self._build_result_from_route(shortest_path_codes, selected_mode)
        if best:
            best["mode"] = selected_mode

        # Yen is used only for alternative routes shown after the map section.
        alternatives = []
        seen_paths = {tuple(shortest_path_codes)}
        k_paths = self.yen_solver.findKShortestPath(source_code, destination_code, k=8) or []
        for path_info in k_paths:
            path = path_info.get("path")
            if not path:
                continue
            path_key = tuple(path)
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)

            alternative = self._build_result_from_route(path, "distance")
            if alternative:
                alternative["mode"] = "alternative"
                alternatives.append(alternative)

        return {"best": best, "routes": alternatives}

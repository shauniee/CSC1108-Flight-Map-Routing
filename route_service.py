import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dijkstra import Dijkstra
from loadDataset import WeightedGraph
from yen import Yen


class RouteService:
    def __init__(self, routesFile: Path):
        self.routesFile = routesFile
        self.airports = {}
        self.airportMeta = {}
        self.weightedGraph = WeightedGraph()
        self.dijkstraSolver = None
        self.yenSolver = None
        self._loadRoutingContext()

    def _loadRoutingContext(self):
        with self.routesFile.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        airports = {}
        airportMeta = {}

        for code, info in raw.items():
            displayName = info.get("display_name") or info.get("name") or code
            airports[code] = displayName

            try:
                latitude = float(info.get("latitude")) if info.get("latitude") is not None else None
                longitude = float(info.get("longitude")) if info.get("longitude") is not None else None
            except (TypeError, ValueError):
                latitude = None
                longitude = None

            airportMeta[code] = {
                "code": code,
                "display_name": displayName,
                "name": info.get("name") or displayName,
                "city_name": info.get("city_name") or "",
                "country": info.get("country") or "",
                "timezone": info.get("timezone") or "",
                "latitude": latitude,
                "longitude": longitude,
            }

        self.weightedGraph.buildGraphFromData(raw)
        self.airports = dict(sorted(airports.items(), key=lambda item: item[0]))
        self.airportMeta = airportMeta
        self.dijkstraSolver = Dijkstra(self.weightedGraph)
        self.yenSolver = Yen(self.weightedGraph, dijkstra=self.dijkstraSolver)

    def estimateTotalPrice(self, totalKm, legs):
        baseFare = 35
        perKm = 0.11
        legFee = 25
        return round(baseFare + (totalKm * perKm) + (legs * legFee), 2)

    def estimateLegMinutes(self, distanceKm):
        cruiseSpeedKmh = 850.0
        blockBufferMin = 18
        return max(30, int(round((distanceKm / cruiseSpeedKmh) * 60 + blockBufferMin)))

    def minutesToTime(self, totalMinutes):
        totalMinutes = int(round(totalMinutes))
        hours, mins = divmod(totalMinutes, 60)
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"

    def haversineKm(self, lat1, lon1, lat2, lon2):
        r = 6371.0
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = (
            math.sin(dLat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dLon / 2) ** 2
        )
        return 2 * r * math.asin(math.sqrt(a))

    def _buildResultFromRoute(self, routeCodes, mode):
        if not routeCodes or len(routeCodes) < 2:
            return None

        legs = []
        mapPoints = []

        for idx in range(len(routeCodes) - 1):
            fromCode = routeCodes[idx]
            toCode = routeCodes[idx + 1]
            edge = self.weightedGraph.graph.get(fromCode, {}).get(toCode, {})

            distance = edge.get("distance")
            if not isinstance(distance, (int, float)) or distance <= 0:
                fromMeta = self.airportMeta.get(fromCode, {})
                toMeta = self.airportMeta.get(toCode, {})
                lat1 = fromMeta.get("latitude")
                lon1 = fromMeta.get("longitude")
                lat2 = toMeta.get("latitude")
                lon2 = toMeta.get("longitude")
                if None not in (lat1, lon1, lat2, lon2):
                    distance = self.haversineKm(lat1, lon1, lat2, lon2)
                else:
                    distance = 0

            minutes = edge.get("time")
            if not isinstance(minutes, (int, float)) or minutes <= 0:
                minutes = self.estimateLegMinutes(float(distance))

            carriers = edge.get("carriers", [])
            if not isinstance(carriers, list):
                carriers = []

            fromMeta = self.airportMeta.get(fromCode, {})
            toMeta = self.airportMeta.get(toCode, {})
            legs.append(
                {
                    "leg_number": idx + 1,
                    "from": fromCode,
                    "to": toCode,
                    "from_name": fromMeta.get("display_name", fromCode),
                    "to_name": toMeta.get("display_name", toCode),
                    "distance_km": round(float(distance), 1),
                    "duration_min": int(round(float(minutes))),
                    "duration_label": self.minutesToTime(minutes),
                    "carrier_names": carriers,
                }
            )

        for seq, code in enumerate(routeCodes, start=1):
            meta = self.airportMeta.get(code, {})
            lat = meta.get("latitude")
            lon = meta.get("longitude")
            if lat is None or lon is None:
                continue
            mapPoints.append(
                {
                    "seq": seq,
                    "code": code,
                    "label": meta.get("display_name", code),
                    "lat": lat,
                    "lon": lon,
                }
            )

        return self._finalizeResult(routeCodes, legs, mapPoints, mode)

    def _pickBestRoute(self, results, mode):
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

    def _finalizeResult(self, route, legs, mapPoints, mode):
        totalDistance = sum(leg["distance_km"] for leg in legs)
        flightMinutes = sum(leg["duration_min"] for leg in legs)
        stops = max(0, len(route) - 2)
        layoverMinutes = stops * 45
        totalTravelMinutes = int(round(flightMinutes + layoverMinutes))
        departureUtc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        arrivalUtc = departureUtc + timedelta(minutes=totalTravelMinutes)
        avgSpeed = (totalDistance / (flightMinutes / 60.0)) if flightMinutes else 0.0

        price = self.estimateTotalPrice(totalDistance, len(legs))
        if mode == "price":
            price = round(price * 0.84, 2)
        elif mode == "stops":
            price = round(price * 1.07, 2)

        return {
            "route": route,
            "distance": int(round(totalDistance)),
            "distance_exact": round(totalDistance, 1),
            "price": price,
            "stops": stops,
            "legs": legs,
            "map_points": mapPoints,
            "flight_minutes": int(round(flightMinutes)),
            "flight_time_label": self.minutesToTime(flightMinutes),
            "layover_minutes": layoverMinutes,
            "layover_time_label": self.minutesToTime(layoverMinutes),
            "total_travel_minutes": totalTravelMinutes,
            "total_travel_label": self.minutesToTime(totalTravelMinutes),
            "departure_utc": departureUtc.isoformat(),
            "arrival_utc": arrivalUtc.isoformat(),
            "avg_speed_kmh": int(round(avgSpeed)),
            "mode": mode,
            "mock": False,
        }

    def computeAlgorithmResults(self, sourceCode, destinationCode, mode):
        if sourceCode not in self.weightedGraph.graph or destinationCode not in self.weightedGraph.graph:
            return {"best": None, "routes": []}

        selectedMode = mode if mode in ("distance", "price", "stops") else "distance"
        shortestPathCodes, _, _ = self.dijkstraSolver.findShortestPath(sourceCode, destinationCode)
        if not shortestPathCodes:
            return {"best": None, "routes": []}

        # Best route is always computed from Dijkstra shortest path only.
        best = self._buildResultFromRoute(shortestPathCodes, selectedMode)
        if best:
            best["mode"] = selectedMode

        # Yen is used only for alternative routes shown after the map section.
        alternatives = []
        seenPaths = {tuple(shortestPathCodes)}
        kPaths = self.yenSolver.findKShortestPath(sourceCode, destinationCode, k=8) or []
        for pathInfo in kPaths:
            path = pathInfo.get("path")
            if not path:
                continue
            pathKey = tuple(path)
            if pathKey in seenPaths:
                continue
            seenPaths.add(pathKey)

            alternative = self._buildResultFromRoute(path, "distance")
            if alternative:
                alternative["mode"] = "alternative"
                alternatives.append(alternative)

        return {"best": best, "routes": alternatives}
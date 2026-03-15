# route_service.py
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dijkstra import Dijkstra
from loadDataset import WeightedGraph
from yen import Yen
from pricing import priceCalculation  # Import the pricing class


class RouteService:
    def __init__(self, routesFile: Path):
        self.routesFile = routesFile
        self.airports = {}
        self.airportMeta = {}
        self.weightedGraph = WeightedGraph()
        self.dijkstraSolver = None
        self.yenSolver = None
        self.priceCalculator = priceCalculation()  # Initialize price calculator
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
        """Legacy method - kept for backward compatibility"""
        baseFare = 35
        perKm = 0.11
        legFee = 25
        return round(baseFare + (totalKm * perKm) + (legs * legFee), 2)

    def calculateAccuratePrice(self, routeCodes, segments_details, mode="distance"):
        """
        Calculate accurate price using the priceCalculation class
        
        Args:
            routeCodes: List of airport codes in the route
            segments_details: List of segment details with carriers, distance, etc.
            mode: Current search mode (affects pricing)
            
        Returns:
            Dictionary with price and breakdown
        """
        if len(routeCodes) < 2:
            return {'price': 0, 'breakdown': {'base': 0, 'fuel': 0, 'total': 0}}
        
        total_price = 0
        segments_prices = []
        
        for i in range(len(routeCodes) - 1):
            from_airport = routeCodes[i]
            to_airport = routeCodes[i + 1]
            
            # Get segment details
            segment = segments_details[i] if i < len(segments_details) else {}
            distance = segment.get('distance_km', 0)
            carriers = segment.get('carrier_names', [])
            
            # Determine if direct flight or connecting
            is_direct = (len(routeCodes) == 2)
            connecting_airport = None if is_direct else routeCodes[i]
            
            # Calculate price for this segment using the pricing class
            segment_price_info = self.priceCalculator.calculatePrice(
                fromAirport=from_airport,
                toAirport=to_airport,
                distance=distance,
                carrier=carriers,
                directFlight=is_direct,
                connectingAirport=connecting_airport
            )
            
            segments_prices.append({
                'from': from_airport,
                'to': to_airport,
                'price': segment_price_info['price'],
                'breakdown': segment_price_info['breakdown']
            })
            
            total_price += segment_price_info['price']
        
        # Apply route-level adjustments based on mode
        if mode == "price":
            total_price *= 0.98  # Small discount for price-optimized routes
        elif mode == "stops":
            total_price *= 1.05  # Premium for fewer stops
        
        return {
            'total_price': round(total_price, 2),
            'segments': segments_prices,
            'breakdown': {
                'base': sum(s['breakdown']['base'] for s in segments_prices),
                'fuel': sum(s['breakdown']['fuel'] for s in segments_prices),
                'total': round(total_price, 2)
            }
        }

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
        segments_details = []  # Store segment details for price calculation

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
            
            # Store for price calculation
            segments_details.append({
                'distance_km': distance,
                'carrier_names': carriers,
                'from_airport': fromCode,
                'to_airport': toCode
            })

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

        return self._finalizeResult(routeCodes, legs, mapPoints, mode, segments_details)

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

    def _finalizeResult(self, route, legs, mapPoints, mode, segments_details=None):
        totalDistance = sum(leg["distance_km"] for leg in legs)
        flightMinutes = sum(leg["duration_min"] for leg in legs)
        stops = max(0, len(route) - 2)
        layoverMinutes = stops * 45
        totalTravelMinutes = int(round(flightMinutes + layoverMinutes))
        departureUtc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        arrivalUtc = departureUtc + timedelta(minutes=totalTravelMinutes)
        avgSpeed = (totalDistance / (flightMinutes / 60.0)) if flightMinutes else 0.0

        # Use accurate price calculation if segments_details provided
        if segments_details:
            price_info = self.calculateAccuratePrice(route, segments_details, mode)
            price = price_info['total_price']
            price_breakdown = price_info['breakdown']
            segments_prices = price_info['segments']
        else:
            # Fallback to estimate
            price = self.estimateTotalPrice(totalDistance, len(legs))
            price_breakdown = None
            segments_prices = []

        # Apply mode-based adjustments
        if mode == "price":
            price = round(price * 0.84, 2)
        elif mode == "stops":
            price = round(price * 1.07, 2)

        result = {
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
        
        # Add price breakdown if available
        if price_breakdown:
            result['price_breakdown'] = price_breakdown
        if segments_prices:
            result['segments_prices'] = segments_prices

        return result

    # route_service.py (updated computeAlgorithmResults method)
    def computeAlgorithmResults(self, sourceCode, destinationCode, mode):
        if sourceCode not in self.weightedGraph.graph or destinationCode not in self.weightedGraph.graph:
            print(f"Airport not found: {sourceCode} or {destinationCode}")
            return {"best": None, "routes": []}

        # Map UI mode to weight type
        weight_type = 'distance'  # default
        if mode == 'price':
            weight_type = 'price'
        elif mode == 'stops':
            weight_type = 'distance'  # Still use distance for stops optimization
        else:
            weight_type = 'distance'

        print(f"Finding path from {sourceCode} to {destinationCode} using {weight_type} optimization")
        
        # Find shortest path based on selected weight type with max 2 transits
        shortestPathCodes, total_dist, total_time, total_price = self.dijkstraSolver.findShortestPath(
            sourceCode, destinationCode, weight_type
        )
        
        if not shortestPathCodes:
            print(f"No path found from {sourceCode} to {destinationCode} within transit limit")
            return {"best": None, "routes": []}

        print(f"Found path: {' -> '.join(shortestPathCodes)}")
        print(f"Distance: {total_dist}, Time: {total_time}, Price: {total_price}")

        # Best route is computed based on selected mode
        best = self._buildResultFromRoute(shortestPathCodes, mode)
        if best:
            best["mode"] = mode
            # Add the accurate metrics
            best["distance_exact"] = total_dist
            best["price"] = total_price if mode == 'price' else best.get("price", total_price)
            best["flight_minutes"] = total_time
            best["stops"] = len(shortestPathCodes) - 2  # Ensure stops count is accurate

        # Yen is used for alternative routes with same transit limit
        alternatives = []
        seenPaths = {tuple(shortestPathCodes)}
        
        # Get k-shortest paths based on the same weight type with max 2 transits
        try:
            kPaths = self.yenSolver.findKShortestPath(
                sourceCode, destinationCode, k=8, weight_type=weight_type
            ) or []
        except Exception as e:
            print(f"Error in Yen's algorithm: {e}")
            kPaths = []
        
        # Ensure kPaths is a list
        if not isinstance(kPaths, list):
            kPaths = []
        
        print(f"Found {len(kPaths)} alternative paths from Yen's algorithm")
        
        for pathInfo in kPaths:
            # Skip if pathInfo is not a dictionary
            if not isinstance(pathInfo, dict):
                continue
                
            path = pathInfo.get("path")
            if not path:
                continue
                
            pathKey = tuple(path)
            if pathKey in seenPaths:
                continue
                
            # Verify transit count (should already be enforced, but double-check)
            if len(path) - 2 > 2:
                continue
                
            seenPaths.add(pathKey)

            alternative = self._buildResultFromRoute(path, mode)
            if alternative:
                alternative["mode"] = "alternative"
                # Update with accurate metrics from pathInfo
                alternative["distance_exact"] = pathInfo.get("dist", 0)
                alternative["price"] = pathInfo.get("price", 0)
                alternative["flight_minutes"] = pathInfo.get("time", 0)
                alternative["stops"] = len(path) - 2
                alternatives.append(alternative)

        # Sort alternatives based on mode
        if mode == "price":
            alternatives.sort(key=lambda x: x.get("price", float("inf")))
        elif mode == "stops":
            alternatives.sort(key=lambda x: (x.get("stops", float("inf")), x.get("distance_exact", float("inf"))))
        else:  # distance
            alternatives.sort(key=lambda x: x.get("distance_exact", float("inf")))

        # Limit alternatives to top 5 for display
        alternatives = alternatives[:5]

        result = {
            "best": best, 
            "routes": alternatives
        }
        
        print(f"Returning best route and {len(alternatives)} alternatives")
        return result
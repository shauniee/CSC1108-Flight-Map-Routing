# route_service.py
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from Algorithms.betweenness import Betweenness
from Algorithms.astar import AStar
from Algorithms.BellmanFord import BellmanFord
from Algorithms.dfs import DFS
from Algorithms.dijkstra import Dijkstra
from flightSchedule import FlightSchedule
from loadDataset import WeightedGraph
from Algorithms.yen import Yen
from AirlineData.pricing import PriceCalculation  # Import the pricing class
from budgetLoop import BudgetLoopSearch
from AirlineData.pricing import PriceCalculation 


class RouteService:
    def __init__(self, routesFile: Path, airlineClassification: Path):
        
        if routesFile is None:
            self.routesFile = Path("AirlineData/airline_routes.json")
        else:
            self.routesFile = routesFile

        if airlineClassification is None:
            self.airlineClassificationFile = Path(__file__).parent / "AirlineData" / "airline_classifications.json"
        else:
            self.airlineClassificationFile = airlineClassification

        self.airports = {}
        self.airportMeta = {}
        self.weightedGraph = WeightedGraph()
        self.astarSolver = None
        self.dijkstraSolver = None
        self.bellmanFordSolver = None
        self.yenSolver = None
        self.dfsSolver = None
        self.budgetloopSolver = None
        self.betweennessSolver = None
        self.scheduleSolver = None
        self.priceCalculator = PriceCalculation(str(self.airlineClassificationFile))
        self._loadRoutingContext()
        self.airlineClassifications = self._loadAirlineClassifications()

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
        self.astarSolver = AStar(self.weightedGraph)
        self.dijkstraSolver = Dijkstra(self.weightedGraph)
        self.bellmanFordSolver = BellmanFord(self.weightedGraph)
        self.yenSolver = Yen(self.weightedGraph, dijkstra=self.dijkstraSolver)
        self.dfsSolver = DFS(self._buildDfsGraph())
        self.budgetloopSolver = BudgetLoopSearch(self.weightedGraph.graph)
        self.betweennessSolver = Betweenness(self.weightedGraph.graph)

        self.scheduleSolver = FlightSchedule(
            self.airportMeta,
            self.weightedGraph.graph,
            price_calculator=self.priceCalculator
        )

    def _buildDfsGraph(self):
        dfsGraph = {}
        for fromCode, neighbors in self.weightedGraph.graph.items():
            dfsGraph[fromCode] = []
            for toCode, edge in neighbors.items():
                dfsGraph[fromCode].append(
                    (
                        toCode,
                        float(edge.get("time", 0)) / 60.0,
                        float(edge.get("price", 0)),
                        float(edge.get("distance", 0)),
                        edge.get("carriers", []),
                    )
                )
        return dfsGraph

    def _loadAirlineClassifications(self):
        """Load airline classifications from JSON file"""
        try:
            with self.airlineClassificationFile.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.airlineClassifications = data
            
            # Initialize price calculator with the classification file
            self.priceCalculator = PriceCalculation(str(self.airlineClassificationFile))
            
        except Exception as e:
            self.priceCalculator = PriceCalculation()
            self.airlineClassifications = {}
            
            
        self.scheduleSolver = FlightSchedule(
            self.airportMeta,
            self.weightedGraph.graph,
            price_calculator=self.priceCalculator
        )

    def getAirlineType(self, carrierIata):
        if self.priceCalculator:
            return self.priceCalculator.getAirlineType(carrierIata)
        return "Standard"
    
    def getAirlineName(self, carrierIata):
        if self.priceCalculator:
            return self.priceCalculator.getAirlineName(carrierIata)
        return carrierIata  # Return IATA code as fallback

    def getAirlineRateAdjustmentLabel(self, airlineType):
        if self.priceCalculator:
            return self.priceCalculator.getRateAdjustmentLabel(airlineType)
        if airlineType == "Premium":
            return "+20%"
        if airlineType == "Budget":
            return "-20%"
        return "0%"

    def estimateTotalPrice(self, totalKm, legs):
        """Legacy method - kept for backward compatibility"""
        baseFare = 35
        perKm = 0.11
        legFee = 25
        return round(baseFare + (totalKm * perKm) + (legs * legFee), 2)

    def calculateAccuratePrice(self, routeCodes, segments_details, mode="distance"):
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
                carriers=carriers,
                directFlight=is_direct,
                connectingAirport=connecting_airport
            )
            carrier_price_options = self.priceCalculator.getCarrierPriceOptions(
                distance=distance,
                carriers=carriers,
                directFlight=is_direct,
                connectingAirport=connecting_airport
            )
            
            # Get airline type for this segment
            airline_type = segment_price_info.get("airlineInfo", {}).get("type", "Standard")
            
            # FIXED: Correct list comprehension for airline names
            airline_names = [self.getAirlineName(c) for c in carriers] if carriers else []
            
            segments_prices.append({
                'from': from_airport,
                'to': to_airport,
                'price': segment_price_info['price'],
                'breakdown': segment_price_info['breakdown'],
                'airline_type': airline_type,
                'carriers': carriers,
                'airline_names': airline_names,
                'carrier_price_options': carrier_price_options,
                'selected_carrier': carrier_price_options[0]['carrier'] if carrier_price_options else None,
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

    def findAirportsWithinRadius(self, sourceCode, radiusKm):
        origin = self.airportMeta.get(sourceCode)
        if not origin:
            return {
                "type": "proximity",
                "origin": None,
                "airports": [],
                "map_points": [],
                "radius_km": radiusKm,
                "count": 0,
            }

        originLat = origin.get("latitude")
        originLon = origin.get("longitude")
        if originLat is None or originLon is None:
            return {
                "type": "proximity",
                "origin": None,
                "airports": [],
                "map_points": [],
                "radius_km": radiusKm,
                "count": 0,
            }

        airports = []
        mapPoints = [
            {
                "code": sourceCode,
                "label": origin.get("display_name", sourceCode),
                "lat": originLat,
                "lon": originLon,
                "kind": "origin",
            }
        ]

        for code, meta in self.airportMeta.items():
            if code == sourceCode:
                continue

            lat = meta.get("latitude")
            lon = meta.get("longitude")
            if lat is None or lon is None:
                continue

            distanceKm = self.haversineKm(originLat, originLon, lat, lon)
            if distanceKm > radiusKm:
                continue

            airport = {
                "code": code,
                "display_name": meta.get("display_name", code),
                "city_name": meta.get("city_name", ""),
                "country": meta.get("country", ""),
                "distance_km": round(distanceKm, 1),
                "latitude": lat,
                "longitude": lon,
            }
            airports.append(airport)
            mapPoints.append(
                {
                    "code": code,
                    "label": airport["display_name"],
                    "lat": lat,
                    "lon": lon,
                    "kind": "nearby",
                }
            )

        airports.sort(key=lambda item: item["distance_km"])
        return {
            "type": "proximity",
            "origin": {
                "code": sourceCode,
                "display_name": origin.get("display_name", sourceCode),
                "city_name": origin.get("city_name", ""),
                "country": origin.get("country", ""),
                "latitude": originLat,
                "longitude": originLon,
            },
            "airports": airports,
            "map_points": mapPoints,
            "radius_km": radiusKm,
            "count": len(airports),
        }

    def _buildResultFromRoute(self, routeCodes, mode, depart_date_str=None):
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
            
            # Extract carrier IATA codes and names
            carrier_iata = []
            carrier_names = []
            for carrier in carriers:
                if isinstance(carrier, dict):
                    iata = carrier.get('iata')
                    name = carrier.get('name')
                    if iata:
                        carrier_iata.append(iata)
                        carrier_names.append(name or iata)
                else:
                    carrier_iata.append(carrier)
                    carrier_names.append(carrier)

            fromMeta = self.airportMeta.get(fromCode, {})
            toMeta = self.airportMeta.get(toCode, {})
            
            carrier_details = []
            display_priority = {"Budget": 0, "Standard": 1, "Premium": 2}
            airline_type = "Standard"

            for idx_carrier, carrier_name in enumerate(carrier_names):
                carrier_code = carrier_iata[idx_carrier] if idx_carrier < len(carrier_iata) else carrier_name
                carrier_type = self.getAirlineType(carrier_code)
                if carrier_type == "Standard":
                    carrier_type = self.getAirlineType(carrier_name)
                rate_adjustment = self.getAirlineRateAdjustmentLabel(carrier_type)

                carrier_details.append(
                    {
                        "name": carrier_name,
                        "code": carrier_code,
                        "type": carrier_type,
                        "rate_adjustment": rate_adjustment,
                    }
                )

            carrier_details.sort(key=lambda item: (display_priority.get(item["type"], 3), item["name"]))
            if carrier_details:
                airline_type = carrier_details[0]["type"]
            
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
                    "carrier_names": carrier_names,
                    "carrier_iata": carrier_iata,
                    "carrier_details": carrier_details,
                    "airline_type": airline_type,  # Add airline type to leg
                    "airline_rate_adjustment": self.getAirlineRateAdjustmentLabel(airline_type),
                }
            )
            
            # Store for price calculation (use IATA codes for price calculation)
            segments_details.append({
                'distance_km': distance,
                'carrier_names': carrier_iata,  # Use IATA codes for price calculation
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

        return self._finalizeResult(routeCodes, legs, mapPoints, mode, segments_details, depart_date_str=depart_date_str)

    def buildRouteResult(self, routeCodes, mode, depart_date_str=None):
        return self._buildResultFromRoute(routeCodes, mode, depart_date_str=depart_date_str)

    def computeDfsResults(self, sourceCode, destinationCode, mode, maxDepth=3, maxResults=25, timeoutSec=5.0, sort_by = "distance"):
        if not self.dfsSolver:
            return {"routes": [], "timed_out": False}

        routes, timedOut = self.dfsSolver.all_routes(
            sourceCode,
            destinationCode,
            max_depth=maxDepth,
            max_results=maxResults,
            timeout_sec=timeoutSec,
            sort_by=sort_by
        )

        builtRoutes = []
        seenPaths = set()
        for _, _, _, path in routes:
            pathKey = tuple(path)
            if pathKey in seenPaths:
                continue
            seenPaths.add(pathKey)
            built = self._buildResultFromRoute(path, mode)
            if built:
                builtRoutes.append(built)

        if sort_by == "price":
            builtRoutes.sort(key=lambda item: (item.get("price", float("inf")), item.get("distance_exact", float("inf"))))
        elif sort_by in ("stops", "connections"):
            builtRoutes.sort(key=lambda item: (item.get("stops", float("inf")), item.get("distance_exact", float("inf"))))
        else:
            builtRoutes.sort(key=lambda item: item.get("distance_exact", float("inf")))

        return {
            "routes": builtRoutes,
            "timed_out": timedOut,
        }

    def _pickBestRoute(self, results, mode):
        if not results:
            return None
        if mode == "price":
            return min(results, key=lambda route: route.get("price", float("inf")))
        if mode in ("stops", "direct"):
            return min(
                results,
                key=lambda route: (
                    route.get("stops", float("inf")),
                    route.get("distance_exact", float("inf")),
                ),
            )
        return min(results, key=lambda route: route.get("distance_exact", float("inf")))

    def _finalizeResult(self, route, legs, mapPoints, mode, segments_details=None, depart_date_str=None):
        totalDistance = sum(leg["distance_km"] for leg in legs)
        flightMinutes = sum(leg["duration_min"] for leg in legs)
        stops = max(0, len(route) - 2)
        layoverMinutes = stops * 45
        totalTravelMinutes = int(round(flightMinutes + layoverMinutes))

        current_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if depart_date_str:
            try:
                dt = datetime.strptime(depart_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                departureUtc = dt.replace(hour=current_utc.hour, minute=current_utc.minute, second=0, microsecond=0)
            except ValueError:
                departureUtc = current_utc
        else:
            departureUtc = current_utc
            
        arrivalUtc = departureUtc + timedelta(minutes=totalTravelMinutes)
        avgSpeed = (totalDistance / (flightMinutes / 60.0)) if flightMinutes else 0.0

        # Use accurate price calculation if segments_details provided
        if segments_details and self.priceCalculator:
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

        # Count airline types in the route
        airline_type_counts = {
            'Premium': sum(1 for leg in legs if leg.get('airline_type') == 'Premium'),
            'Budget': sum(1 for leg in legs if leg.get('airline_type') == 'Budget'),
            'Standard': sum(1 for leg in legs if leg.get('airline_type') == 'Standard')
        }

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
            "airline_stats": airline_type_counts,  # Add airline statistics
        }
        
        # Add price breakdown if available
        if price_breakdown:
            result['price_breakdown'] = price_breakdown
        if segments_prices:
            result['segments_prices'] = segments_prices

        return result

    def computeAlgorithmResults(self, sourceCode, destinationCode, mode, depart_date_str=None):
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
        shortestPathCodes, total_dist, total_time = self.astarSolver.findShortestPath(
            sourceCode, destinationCode, weight_type
        )
        
        if not shortestPathCodes:
            print(f"No path found from {sourceCode} to {destinationCode} within transit limit")
            return {"best": None, "routes": []}

        print(f"Found path: {' -> '.join(shortestPathCodes)}")
        print(f"Distance: {total_dist}, Time: {total_time}")

        # Best route is computed based on selected mode
        best = self._buildResultFromRoute(shortestPathCodes, mode, depart_date_str=depart_date_str)
        if best:
            best["mode"] = mode
            # Add the accurate metrics
            best["distance_exact"] = total_dist
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

            alternative = self._buildResultFromRoute(path, mode, depart_date_str=depart_date_str)
            if alternative:
                alternative["mode"] = "alternative"
                # Update with accurate metrics from pathInfo
                alternative["distance_exact"] = pathInfo.get("dist", 0)
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

    def computeBellmanFordResults(self, sourceCode, destinationCode, mode, depart_date_str=None):
        if sourceCode not in self.weightedGraph.graph or destinationCode not in self.weightedGraph.graph:
            print(f"Airport not found: {sourceCode} or {destinationCode}")
            return {"best": None, "routes": []}

        weight_type = "price" if mode == "price" else "distance"

        try:
            shortest_path_codes, total_weight = self.bellmanFordSolver.getShortestPath(
                sourceCode, destinationCode, weight_type
            )
        except ValueError as exc:
            print(f"Bellman-Ford failed: {exc}")
            return {"best": None, "routes": []}

        if not shortest_path_codes:
            print(f"No Bellman-Ford path found from {sourceCode} to {destinationCode}")
            return {"best": None, "routes": []}

        best = self._buildResultFromRoute(shortest_path_codes, mode, depart_date_str=depart_date_str)
        if best:
            best["mode"] = mode
            if weight_type == "distance":
                best["distance_exact"] = total_weight
                best["flight_minutes"] = sum(
                    self.weightedGraph.graph.get(shortest_path_codes[i], {})
                    .get(shortest_path_codes[i + 1], {})
                    .get("time", 0)
                    for i in range(len(shortest_path_codes) - 1)
                )
            else:
                best["price"] = round(total_weight, 2)
            best["stops"] = len(shortest_path_codes) - 2

        alternatives = []
        seen_paths = {tuple(shortest_path_codes)}

        try:
            kPaths = self.yenSolver.findKShortestPath(
                sourceCode, destinationCode, k=8, weight_type=weight_type
            ) or []
        except Exception as exc:
            print(f"Error in Yen's algorithm: {exc}")
            kPaths = []

        if not isinstance(kPaths, list):
            kPaths = []

        for pathInfo in kPaths:
            if not isinstance(pathInfo, dict):
                continue

            path = pathInfo.get("path")
            if not path:
                continue

            path_key = tuple(path)
            if path_key in seen_paths:
                continue

            if len(path) - 2 > 2:
                continue

            seen_paths.add(path_key)

            alternative = self._buildResultFromRoute(path, mode, depart_date_str=depart_date_str)
            if alternative:
                alternative["mode"] = "alternative"
                alternative["distance_exact"] = pathInfo.get("dist", alternative.get("distance_exact", 0))
                alternative["flight_minutes"] = pathInfo.get("time", alternative.get("flight_minutes", 0))
                if mode == "price":
                    alternative["price"] = round(pathInfo.get("price", alternative.get("price", 0)), 2)
                alternative["stops"] = len(path) - 2
                alternatives.append(alternative)

        if mode == "price":
            alternatives.sort(key=lambda x: x.get("price", float("inf")))
        elif mode == "stops":
            alternatives.sort(key=lambda x: (x.get("stops", float("inf")), x.get("distance_exact", float("inf"))))
        else:
            alternatives.sort(key=lambda x: x.get("distance_exact", float("inf")))

        return {"best": best, "routes": alternatives[:5]}
    
    def findBestBudgetLoop(self, sourceCode, budget, targetCities):
        origin = self.airportMeta.get(sourceCode)
        if not origin or not self.budgetloopSolver:
            return {
                "type" : "budget-loop",
                "origin" : None,
                "budget" : budget,
                "best_route" : None,
                "target_cities" : targetCities,
            }
        
        searchResult = self.budgetloopSolver.find_best_loop(sourceCode,budget, targetCities)

        if not searchResult:
            return {
                "type" : "budget-loop",
                "origin" : {
                    "code" : sourceCode,
                    "display_name" : origin.get("display_name", sourceCode),
                    "city_name" : origin.get("city_name", ""),
                    "country" : origin.get("country",""),
                    
                },
                "budget" : budget,
                "best_route" : None,
                "target_cities" : targetCities,
            }
        
        routeCodes = searchResult["path"]
        builtRoute = self._buildResultFromRoute(routeCodes, "price")

        if builtRoute:
            builtRoute["price"] = searchResult["total_cost"]
            builtRoute["cities_visited"] = searchResult["cities_visited"]
            builtRoute["remaining_budget"] = searchResult["remaining_budget"]

        return {
                "type" : "budget-loop",
                "origin" : {
                    "code" : sourceCode,
                    "display_name" : origin.get("display_name", sourceCode),
                    "city_name" : origin.get("city_name", ""),
                    "country" : origin.get("country",""),
                },
                "budget" : budget,
                "best_route" : builtRoute,
                "target_cities" : targetCities,
        }

    def get_hubs(self, top_n: int = 20) -> list:
        """
        Return the top *top_n* hub airports ranked by Betweenness Centrality.
        Cached after first call so subsequent visits are instant.
        """
        if not hasattr(self, "_hub_cache"):
            raw = self.betweennessSolver.top_hubs(top_n=top_n)
            for item in raw:
                meta = self.airportMeta.get(item["code"], {})
                item["display_name"] = meta.get("display_name", item["code"])
                item["city_name"]    = meta.get("city_name", "")
                item["country"]      = meta.get("country", "")
                item["latitude"]     = meta.get("latitude")
                item["longitude"]    = meta.get("longitude")
            self._hub_cache = raw
        return self._hub_cache
 
    def get_flight_schedule(self, src: str, dst: str, date=None) -> dict:
        """Generate a daily flight timetable from src to dst."""
        return self.scheduleSolver.generate(src, dst, date=date, num_flights=8)

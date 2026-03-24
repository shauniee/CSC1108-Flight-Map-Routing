import heapq
import math

from loadDataset import WeightedGraph


class AStar:
    def __init__(self, graph: WeightedGraph):
        self.airportGraph = graph
        self.graphDictionary = graph.graph
        self.maxTransit = 2
        self._minPricePerKm = self._computeMinPricePerKm()

    def findShortestPath(self, start: str, end: str, weight_type: str = "distance"):
        if start not in self.graphDictionary:
            print(f"Start airport '{start}' not found")
            return None, None, None

        if end not in self.graphDictionary:
            print(f"Destination airport '{end}' not found")
            return None, None, None

        if weight_type not in ["distance", "time", "price"]:
            weight_type = "distance"

        g_costs = {airport: float("inf") for airport in self.graphDictionary}
        times = {airport: float("inf") for airport in self.graphDictionary}
        previous = {airport: None for airport in self.graphDictionary}
        transit_count = {airport: float("inf") for airport in self.graphDictionary}

        g_costs[start] = 0
        times[start] = 0
        transit_count[start] = 0

        start_priority = self.heuristic(start, end, weight_type)
        open_set = [(start_priority, 0, 0, start)]
        best_states = {start: (0, 0)}

        while open_set:
            _, current_cost, current_transits, current_node = heapq.heappop(open_set)

            state = (current_cost, current_transits)
            if best_states.get(current_node, (float("inf"), float("inf"))) < state:
                continue

            if current_node == end:
                break

            for neighbor, edge_data in self.graphDictionary.get(current_node, {}).items():
                new_transits = current_transits + (0 if current_node == start else 1)
                if new_transits > self.maxTransit:
                    continue

                edge_weight = self._getEdgeWeight(edge_data, weight_type)
                new_cost = current_cost + edge_weight
                new_time = times[current_node] + edge_data.get("time", 0)
                current_best = best_states.get(neighbor, (float("inf"), float("inf")))

                if new_cost < current_best[0] or (
                    new_cost == current_best[0] and new_transits < current_best[1]
                ):
                    g_costs[neighbor] = new_cost
                    times[neighbor] = new_time
                    transit_count[neighbor] = new_transits
                    previous[neighbor] = current_node
                    best_states[neighbor] = (new_cost, new_transits)
                    priority = new_cost + self.heuristic(neighbor, end, weight_type)
                    heapq.heappush(open_set, (priority, new_cost, new_transits, neighbor))

        path = self.reconstructPath(previous, start, end)
        if path and len(path) - 2 <= self.maxTransit:
            total_distance = self.calculatePathMetric(path, "distance")
            total_time = self.calculatePathMetric(path, "time")
            return path, total_distance, total_time

        return None, None, None

    def heuristic(self, start: str, end: str, weight_type: str) -> float:
        start_info = self.airportGraph.getAirportInfo(start)
        end_info = self.airportGraph.getAirportInfo(end)

        try:
            start_lat = float(start_info.get("latitude"))
            start_lon = float(start_info.get("longitude"))
            end_lat = float(end_info.get("latitude"))
            end_lon = float(end_info.get("longitude"))
        except (TypeError, ValueError):
            return 0

        direct_distance = self._haversineKm(start_lat, start_lon, end_lat, end_lon)

        if weight_type == "time":
            cruise_speed_kmh = 850.0
            return (direct_distance / cruise_speed_kmh) * 60.0
        if weight_type == "price":
            return direct_distance * self._minPricePerKm
        return direct_distance

    def reconstructPath(self, previous: dict, start: str, end: str):
        path = []
        current = end

        while current is not None:
            path.append(current)
            current = previous.get(current)

        path.reverse()
        return path if path and path[0] == start else None

    def calculatePathMetric(self, path: list, metric: str):
        if not path or len(path) < 2:
            return 0

        total = 0
        for i in range(len(path) - 1):
            from_code = path[i]
            to_code = path[i + 1]
            edge = self.graphDictionary.get(from_code, {}).get(to_code, {})
            if metric == "distance":
                total += edge.get("distance", 0)
            elif metric == "time":
                total += edge.get("time", 0)
            elif metric == "price":
                total += edge.get("price", 0)
        return total

    def _getEdgeWeight(self, edge_data: dict, weight_type: str) -> float:
        if weight_type == "time":
            return edge_data.get("time", 0)
        if weight_type == "price":
            return edge_data.get("price", 0)
        return edge_data.get("distance", 0)

    def _computeMinPricePerKm(self) -> float:
        min_ratio = None
        for neighbors in self.graphDictionary.values():
            for edge in neighbors.values():
                distance = edge.get("distance", 0)
                price = edge.get("price", 0)
                if not distance or distance <= 0:
                    continue
                ratio = price / distance
                if min_ratio is None or ratio < min_ratio:
                    min_ratio = ratio
        return min_ratio if min_ratio is not None else 0

    def _haversineKm(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        return 2 * radius_km * math.asin(math.sqrt(a))

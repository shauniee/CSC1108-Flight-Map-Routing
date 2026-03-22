class BellmanFord:
    def __init__(self, graph):
        self.graph = graph

    def run(self, source, weight_key="price"):
        nodes = self.graph.getAllAirports()
        if source not in nodes:
            raise ValueError(f"Unknown source airport: {source}")

        distances = {node: float("inf") for node in nodes}
        predecessors = {node: None for node in nodes}
        distances[source] = 0

        for _ in range(len(nodes) - 1):
            updated = False

            for u in nodes:
                if distances[u] == float("inf"):
                    continue

                for v, edge_data in self.graph.getConnections(u).items():
                    weight = edge_data.get(weight_key, float("inf"))
                    if not isinstance(weight, (int, float)):
                        continue

                    candidate = distances[u] + weight
                    if candidate < distances.get(v, float("inf")):
                        distances[v] = candidate
                        predecessors[v] = u
                        updated = True

            if not updated:
                break

        for u in nodes:
            if distances[u] == float("inf"):
                continue

            for v, edge_data in self.graph.getConnections(u).items():
                weight = edge_data.get(weight_key, float("inf"))
                if not isinstance(weight, (int, float)):
                    continue

                if distances[u] + weight < distances.get(v, float("inf")):
                    raise ValueError("Graph contains a negative-weight cycle")

        return distances, predecessors

    def calculatePath(self, source, weight_key="price"):
        return self.run(source, weight_key)

    def getShortestPath(self, source, destination, weight_key="price"):
        distances, predecessors = self.run(source, weight_key)

        if destination not in distances or distances[destination] == float("inf"):
            return [], float("inf")

        path = []
        current = destination

        while current is not None:
            path.append(current)
            current = predecessors[current]

        path.reverse()
        return path, distances[destination]

    def getReturnFlight(self, source, destination, weight_key="price"):
        outbound_path, outbound_cost = self.getShortestPath(source, destination, weight_key)
        return_path, return_cost = self.getShortestPath(destination, source, weight_key)

        if not outbound_path or not return_path:
            return {
                "outbound_path": outbound_path,
                "outbound_cost": outbound_cost,
                "return_path": return_path,
                "return_cost": return_cost,
                "total_cost": float("inf"),
            }

        return {
            "outbound_path": outbound_path,
            "outbound_cost": outbound_cost,
            "return_path": return_path,
            "return_cost": return_cost,
            "total_cost": outbound_cost + return_cost,
        }

from collections import deque


def estimate_total_price(total_km, legs):
    base_fare = 35
    per_km = 0.11
    leg_fee = 25
    return round(base_fare + (total_km * per_km) + (legs * leg_fee), 2)


class BFS:
    """
    Breadth-First Search over a flight graph adjacency list.
    """

    def __init__(self, graph: dict):
        self.graph = graph

    # - Public API -------------------------------------------------------------

    def shortest_path(self, src: str, dst: str, mode: str):
        if src not in self.graph or dst not in self.graph:
            return None
        
        if mode in ("stops", "direct"):
            queue = deque([(src, [src])])
            visited = {src}

            while queue:
                current, path = queue.popleft()

                if current == dst:
                    if mode == "direct" and len(path) > 2:
                        return None
                    total_km = self.calculate_path_distance(path)
                    return {
                        "route": path,
                        "distance": total_km,
                        "price": estimate_total_price(total_km, len(path) - 1),
                        "stops": max(0, len(path) - 2)
                    }
                
                if mode == "direct" and len(path) >= 2:
                    continue
                
                for neighbor in self.graph.get(current, {}):
                    if neighbor and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
            return None
    
    def calculate_path_distance(self, path: list):
        total = 0
        for i in range(len(path) - 1):
            if path[i+1] in self.graph.get(path[i], {}):
                total += self.graph[path[i]][path[i+1]].get('distance', 0)
        return total

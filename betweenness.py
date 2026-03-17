from collections import deque
import random


class Betweenness:
    """
    Computes Betweenness Centrality for every airport in the flight network.

    Betweenness Centrality measures how often a node appears on the shortest
    path between any two other nodes. Airports with high betweenness are
    critical hubs — removing them would disconnect the most routes.

    Algorithm: Brandes (2001) — O(V * E) for unweighted graphs.
    This is NOT taught in the module; it is used in network analysis,
    logistics, and internet routing.

    Parameters
    ----------
    graph : dict[str, dict]
        Adjacency dict in WeightedGraph format:
        { airport_code: { neighbour_code: { distance, time, carriers } } }
    """

    def __init__(self, graph: dict):
        self.graph = {k: v for k, v in graph.items() if v}
        self.nodes = list(self.graph.keys())

    def compute(self, sample_size: int = 200) -> dict:
        """
        Run the Brandes algorithm and return a dict mapping each airport
        code to its (unnormalised) betweenness centrality score.
        """
        centrality = {node: 0.0 for node in self.nodes}
        
        sources = random.Random(42).sample(
            self.nodes, min(sample_size, len(self.nodes))
        )

        for source in sources:
            stack   = []
            pred    = {node: [] for node in self.nodes}
            sigma   = {node: 0   for node in self.nodes}
            dist    = {node: -1  for node in self.nodes}

            sigma[source] = 1
            dist[source]  = 0

            queue = deque([source])
            while queue:
                v = queue.popleft()
                stack.append(v)
                for w in self.graph.get(v, {}):
                    if w not in dist:
                        continue
                    if dist[w] < 0:
                        queue.append(w)
                        dist[w] = dist[v] + 1
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)

            delta = {node: 0.0 for node in self.nodes}
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    if sigma[w] > 0:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != source:
                    centrality[w] += delta[w]

        scale = len(self.nodes) / len(sources) if sources else 1.0
        for node in centrality:
            centrality[node] = round(centrality[node] * scale, 2)
            
        return centrality

    def top_hubs(self, top_n: int = 20) -> list:
        """
        Return the top *top_n* airports ranked by betweenness centrality.

        Each entry is a dict:
            code, centrality_score, rank, connection_count
        """
        print(f"Running Betweenness on {len(self.nodes)} nodes...")
        scores = self.compute(sample_size=100)
        print("Betweenness done.")
  
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (code, score) in enumerate(ranked[:top_n], start=1):
            results.append({
                "rank":             rank,
                "code":             code,
                "centrality_score": round(score, 2),
                "connection_count": len(self.graph.get(code, {})),
            })
        return results
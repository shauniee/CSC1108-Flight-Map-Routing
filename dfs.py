import time


class DFS:
    """
    Depth-First Search over a flight graph adjacency list.

    Parameters
    ----------
    graph : dict[str, list]
        Adjacency list in the format produced by Graph:
        { airport_code: [(dest, duration_hrs, price_usd, km, carriers), ...] }
    """

    def __init__(self, graph: dict):
        self.graph = graph

    # ── Public API ────────────────────────────────────────────

    def all_routes(
        self,
        start:       str,
        end:         str,
        max_depth:   int   = 3,
        max_results: int   = 50,
        timeout_sec: float = 5.0,
        sort_by:     str   = "duration",
    ) -> tuple[list, bool]:
        """
        Enumerate simple paths from *start* → *end* up to *max_depth* hops.

        Each result is a tuple:
            (total_duration_hrs, total_price_usd, total_km, path_list)

        Results are sorted by the specified criterion (ascending).

        Returns
        -------
        results   : list of (float, float, float, list[str])
        timed_out : bool – True if the search was cut short
        """
        results  = []
        deadline = time.time() + timeout_sec

        # Stack entry: (current_node, path_so_far, cum_duration, cum_price, cum_km)
        stack = [(start, [start], 0.0, 0.0, 0.0)]

        while stack:
            # ── Safeguard checks ──────────────────────────────
            if len(results) >= max_results:
                break
            if time.time() > deadline:
                break

            node, path, total_dur, total_price, total_km = stack.pop()

            # ── Goal check ───────────────────────────────────
            if node == end and len(path) > 1:
                results.append((total_dur, total_price, total_km, path))
                continue          # keep searching for more routes

            # ── Depth limit ──────────────────────────────────
            if len(path) > max_depth + 1:
                continue

            # ── Expand neighbours ────────────────────────────
            for nb, dur, price, km, _ in self.graph.get(node, []):
                if nb not in path:               # avoid cycles in current path
                    stack.append((
                        nb,
                        path + [nb],
                        total_dur   + dur,
                        total_price + price,
                        total_km    + km,
                    ))

        timed_out = len(stack) > 0   # items still on stack → stopped early
        
        sort_key_map = {
            "duration": lambda x: x[0],
            "price":    lambda x: x[1],
            "km":       lambda x: x[2],
        }
        
        sort_key = sort_key_map.get(sort_by, sort_key_map["duration"])
        results.sort(key=sort_key)
        
        return results, timed_out

    # Convenience helpers

    def fastest_route(self, start: str, end: str, **kwargs):
        """Return the single fastest route found by DFS (or None)."""
        results, _ = self.all_routes(start, end, **kwargs)
        return results[0] if results else None

    def cheapest_route(self, start: str, end: str, **kwargs):
        """Return the single cheapest (by price) route found by DFS (or None)."""
        results, _ = self.all_routes(start, end, **kwargs)
        if not results:
            return None
        return min(results, key=lambda x: x[1])

    def shortest_route(self, start: str, end: str, **kwargs):
        """Return the single shortest (by km) route found by DFS (or None)."""
        results, _ = self.all_routes(start, end, **kwargs)
        if not results:
            return None
        return min(results, key=lambda x: x[2])

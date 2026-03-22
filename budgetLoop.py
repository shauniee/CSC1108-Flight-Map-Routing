import time
class BudgetLoopSearch:
    def __init__(self, graph):
        self.graph = graph

    def find_best_loop(self, start : str, budget : float, target_cities : int, max_depth: int=None, time_outsec : float = 9.0):
        best_path = None
        best_cost = float("inf")

        if target_cities >= 5:
            time_outsec = 25.0

        deadline = time.time() + time_outsec

        if max_depth is None:
            max_depth = target_cities + 1

        stack = [(start, [start], 0.0)]

        while stack:
            if time.time() > deadline:
                break

            node, path, total_cost = stack.pop()

            if len(path) > max_depth:
                continue

            for next_node, edge in self.graph.get(node, {}).items():
                price = edge.get("price",0)

                if not isinstance(price, (int, float)):
                    continue
                    
                next_cost = total_cost + price

                if next_cost > budget:
                    continue
                if next_node == start and len(path) > 1:
                    candidate_path = path + [start]
                    candidate_cities = len(candidate_path) - 2
                    #best_cities = len(best_path) - 2 if best_path else - 1
                    
                    if candidate_cities != target_cities:
                        continue

                    if best_path is None or next_cost < best_cost:
                        best_path = candidate_path
                        best_cost = next_cost
                
                    # if best_path is None or candidate_cities > best_cities:
                    #     best_path = candidate_path
                    #     best_cost = next_cost
                    # elif candidate_cities == best_cities and next_cost > best_cost:
                    #     best_path = candidate_path
                    #     best_cost = next_cost

                    continue

                if next_node in path:
                    continue
                
                stack.append((next_node, path + [next_node], next_cost))


        if best_path is None:
            return None
        
        return {
             "path" : best_path,
             "total_cost" : round(best_cost, 2),
             "cities_visited" : len(best_path) - 2,
             "remaining_budget" : round(budget - best_cost, 2)
        }
import heapq
from loadDataset import WeightedGraph

class Dijkstra:
    def __init__(self, graph: WeightedGraph):
        self.airportGraph = graph
        self.graphDictionary = graph.graph
        self.maxTransit = 2  # Internal constant for maximum transit flights
        
    def findShortestPath(self, start: str, end: str, weight_type: str = 'distance'):
        # Validate airports exist
        if start not in self.graphDictionary:
            print(f"Start airport '{start}' not found")
            return None, None, None, None
            
        if end not in self.graphDictionary:
            print(f"Destination airport '{end}' not found")
            return None, None, None, None
            
        # Validate weight type
        if weight_type not in ['distance', 'time']:
            weight_type = 'distance'
            
        # Initialize data structures
        weights = {}  # Store the primary weight
        times = {}    # Always store time separately
        previous = {}
        transit_count = {}  # Track number of transits for each node
        
        # Initialize all airports
        for airport in self.graphDictionary:
            weights[airport] = float('inf')
            times[airport] = float('inf')
            transit_count[airport] = float('inf')
            previous[airport] = None
        
        # Set start node values
        weights[start] = 0
        times[start] = 0
        transit_count[start] = 0  # Start with 0 transits
        
        # Priority queue: (weight, transit_count, node)
        # Include transit_count to prefer paths with fewer transits when weights are equal
        priorityQueue = [(0, 0, start)]
        
        # Use a dictionary to track best (weight, transits) for each node
        best_states = {start: (0, 0)}
        
        while priorityQueue:
            currentWeight, currentTransits, currentNode = heapq.heappop(priorityQueue)
            
            state = (currentWeight, currentTransits)
            if currentNode in best_states and best_states[currentNode] < state:
                continue
            
            # Early exit if we reached destination
            if currentNode == end:
                break
            
            # Skip if no neighbors
            if currentNode not in self.graphDictionary:
                continue
                
            # Explore neighbors
            for neighbor, edgeData in self.graphDictionary[currentNode].items():
                # Calculate new transit count
                # A transit occurs when we move from currentNode to neighbor and it's not the first move
                newTransits = currentTransits
                if currentNode != start:  # If we're not at start, this is a transit
                    newTransits += 1
                
                # Check transit limit
                if newTransits > self.maxTransit:
                    continue
                
                # Get the appropriate weight based on weight_type
                if weight_type == 'time':
                    edgeWeight = edgeData.get('time', 0)
                else:  # distance
                    edgeWeight = edgeData['distance']
                
                # Calculate new weight
                newWeight = weights[currentNode] + edgeWeight
                
                # Get time from edge data
                legTime = edgeData.get('time', 0)
                newTime = times[currentNode] + legTime
                
                # Check if this path is better
                current_best = best_states.get(neighbor, (float('inf'), float('inf')))
                
                # Update if we found a better path (better weight OR same weight with fewer transits)
                if (newWeight < current_best[0] or 
                    (newWeight == current_best[0] and newTransits < current_best[1])):
                    
                    weights[neighbor] = newWeight
                    times[neighbor] = newTime
                    transit_count[neighbor] = newTransits
                    previous[neighbor] = currentNode
                    best_states[neighbor] = (newWeight, newTransits)
                    heapq.heappush(priorityQueue, (newWeight, newTransits, neighbor))
        
        # Reconstruct path
        path = self.reconstructPath(previous, start, end)
        
        if path:
            # Verify transit count
            actual_transits = len(path) - 2
            if actual_transits <= self.maxTransit:
                total_distance = self.calculatePathMetric(path, 'distance')
                total_time = self.calculatePathMetric(path, 'time')
                return path, total_distance, total_time
        
        return None, None, None
    
    def findAllPathsWithMaxTransits(self, start: str, end: str):
        """
        Find all possible paths within transit limit (for Yen's algorithm initialization)
        """
        if start not in self.graphDictionary or end not in self.graphDictionary:
            return None, None, None
        
        # Use BFS to find a path within transit limit
        queue = [(start, [start], 0, 0, 0)]  # (node, path, transits, distance, time)
        visited_paths = set()  # To avoid revisiting same paths
        
        while queue:
            node, path, transits, distance, time = queue.pop(0)
            
            # Create a path signature to avoid cycles
            path_key = tuple(path)
            if path_key in visited_paths:
                continue
            visited_paths.add(path_key)
            
            if node == end and len(path) >= 2:
                return path, distance, time
            
            if transits >= self.maxTransit and node != end:
                continue  # Can't add more transits
                
            for neighbor, edgeData in self.graphDictionary.get(node, {}).items():
                if neighbor not in path:  # Avoid cycles
                    new_transits = transits
                    if node != start:
                        new_transits += 1
                    
                    if new_transits <= self.maxTransit:
                        new_path = path + [neighbor]
                        new_distance = distance + edgeData['distance']
                        new_time = time + edgeData.get('time', 0)
                        queue.append((neighbor, new_path, new_transits, new_distance, new_time))
        
        return None, None, None
    
    def reconstructPath(self, previous: dict, start: str, end: str):
        """Reconstruct the path from start to end"""
        path = []
        current = end
        
        # Follow breadcrumbs backwards
        while current is not None:
            path.append(current)
            current = previous.get(current)
        
        # Reverse to get start → end order
        path.reverse()
        
        # Check if path is valid (starts at start)
        if path and path[0] == start:
            return path
        else:
            return None
    
    def calculatePathMetric(self, path: list, metric: str):
        """Calculate total distance or time for a path"""
        if not path or len(path) < 2:
            return 0
            
        total = 0
        for i in range(len(path) - 1):
            fromCode = path[i]
            toCode = path[i + 1]
            
            if fromCode in self.graphDictionary and toCode in self.graphDictionary[fromCode]:
                edge = self.graphDictionary[fromCode][toCode]
                if metric == 'distance':
                    total += edge['distance']
                elif metric == 'time':
                    total += edge.get('time', 0)
        
        return total
    
    def getName(self, code: str) -> str:
        """Get display name for an airport"""
        if code in self.airportGraph.airportData:
            data = self.airportGraph.airportData[code]
            return data.get('display_name', data.get('name', code))
        return code
    
    def getRouteDetails(self, path: list) -> dict:
        """
        Get detailed information about a route for display
        """
        if not path:
            return {}
        
        details = {
            'path': path,
            'segments': [],
            'total_distance': 0,
            'total_time': 0,
            'carriers': set()
        }
        
        for i in range(len(path) - 1):
            fromCode = path[i]
            toCode = path[i + 1]
            
            if fromCode in self.graphDictionary and toCode in self.graphDictionary[fromCode]:
                edge = self.graphDictionary[fromCode][toCode]
                
                # Get airport names if available
                fromName = self.getName(fromCode)
                toName = self.getName(toCode)
                
                segment = {
                    'from': fromCode,
                    'from_name': fromName,
                    'to': toCode,
                    'to_name': toName,
                    'distance': edge['distance'],
                    'time': edge.get('time', 0)
                }
                
                # Add carriers if available
                if 'carriers' in edge and edge['carriers']:
                    segment['carriers'] = edge['carriers']
                    for carrier in edge['carriers']:
                        if isinstance(carrier, dict):
                            details['carriers'].add(carrier.get('name', carrier.get('iata')))
                        else:
                            details['carriers'].add(carrier)
                
                details['segments'].append(segment)
                details['total_distance'] += segment['distance']
                details['total_time'] += segment['time']
        
        details['connections'] = len(path) - 1
        details['carriers'] = list(details['carriers'])
        
        return details
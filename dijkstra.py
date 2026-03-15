# dijkstra.py
import heapq
from copy import deepcopy
from loadDataset import WeightedGraph

class Dijkstra:
    def __init__(self, graph: WeightedGraph):
        self.airportGraph = graph
        self.graphDictionary = graph.graph
        
    def findShortestPath(self, start: str, end: str, weight_type: str = 'distance'):
        """
        Find shortest path based on specified weight type
        
        Args:
            start: Starting airport code
            end: Destination airport code
            weight_type: 'distance', 'time', or 'price'
        """
        # Validate airports exist
        if start not in self.graphDictionary:
            print(f"Start airport '{start}' not found")
            return None, None, None
            
        if end not in self.graphDictionary:
            print(f"Destination airport '{end}' not found")
            return None, None, None
            
        # Validate weight type
        if weight_type not in ['distance', 'time', 'price']:
            weight_type = 'distance'
            
        # Initialize data structures
        weights = {}  # Store the primary weight (distance, time, or price)
        times = {}    # Always store time separately for consistency
        previous = {}
        
        # Initialize all airports
        for airport in self.graphDictionary:
            weights[airport] = float('inf')
            times[airport] = float('inf')
            previous[airport] = None
        
        # Set start node values
        weights[start] = 0
        times[start] = 0
        
        # Priority queue: (weight, node)
        priorityQueue = [(0, start)]
        visited = set()
        
        while priorityQueue:
            currentWeight, currentNode = heapq.heappop(priorityQueue)
            
            if currentNode in visited:
                continue
                
            visited.add(currentNode)
            
            # Early exit if we reached destination
            if currentNode == end:
                break
            
            # Skip if no neighbors
            if currentNode not in self.graphDictionary:
                continue
                
            # Explore neighbors
            for neighbor, edgeData in self.graphDictionary[currentNode].items():
                if neighbor in visited:
                    continue
                
                # Get the appropriate weight based on weight_type
                if weight_type == 'time':
                    edgeWeight = edgeData.get('time', 0)
                elif weight_type == 'price':
                    edgeWeight = edgeData.get('price', 0)
                else:  # distance
                    edgeWeight = edgeData['distance']
                
                # Calculate new weight
                newWeight = weights[currentNode] + edgeWeight
                
                # Get time from edge data (always track time)
                legTime = edgeData.get('time', 0)
                newTime = times[currentNode] + legTime
                
                # If we found a better path based on the selected weight type
                if newWeight < weights[neighbor]:
                    weights[neighbor] = newWeight
                    times[neighbor] = newTime
                    previous[neighbor] = currentNode
                    heapq.heappush(priorityQueue, (newWeight, neighbor))
        
        # Reconstruct path
        path = self._reconstructPath(previous, start, end)
        
        if path:
            # Return path and the actual metrics
            total_distance = self.calculatePathMetric(path, 'distance')
            total_time = self.calculatePathMetric(path, 'time')
            total_price = self.calculatePathMetric(path, 'price')
            return path, total_distance, total_time, total_price
        else:
            return None, None, None, None
    
    def _reconstructPath(self, previous: dict, start: str, end: str):
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
        """Calculate total distance, time, or price for a path"""
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
                elif metric == 'price':
                    total += edge.get('price', 0)
        
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
            'total_price': 0,
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
                    'time': edge.get('time', 0),
                    'price': edge.get('price', 0)
                }
                
                # Add carriers if available
                if 'carriers' in edge and edge['carriers']:
                    segment['carriers'] = edge['carriers']
                    for carrier in edge['carriers']:
                        details['carriers'].add(carrier)
                
                details['segments'].append(segment)
                details['total_distance'] += segment['distance']
                details['total_time'] += segment['time']
                details['total_price'] += segment['price']
        
        details['connections'] = len(path) - 1
        details['carriers'] = list(details['carriers'])
        
        return details
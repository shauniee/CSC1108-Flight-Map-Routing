import heapq
from copy import deepcopy
from loadDataset import WeightedGraph

class Dijkstra:
    def __init__(self, graph: WeightedGraph):
        self.airportGraph = graph
        self.graphDictionary = graph.graph
        
    def findShortestPath(self, start: str, end: str):
        # Validate airports exist
        if start not in self.graphDictionary:
            print(f"Start airport '{start}' not found")
            return None, None, None
            
        if end not in self.graphDictionary:
            print(f"Destination airport '{end}' not found")
            return None, None, None
            
        # Initialize data structures
        distances = {}
        times = {}
        previous = {}
        
        # Initialize all airports
        for airport in self.graphDictionary:
            distances[airport] = float('inf')
            times[airport] = float('inf')
            previous[airport] = None
        
        # Set start node values
        distances[start] = 0
        times[start] = 0
        
        # Priority queue: (distance, node)
        priorityQueue = [(0, start)]
        visited = set()
        
        while priorityQueue:
            currentDistance, currentNode = heapq.heappop(priorityQueue)
            
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
                
                # Calculate new distance
                newDistance = distances[currentNode] + edgeData['distance']
                
                # Get time from edge data
                legTime = edgeData.get('time', 0)
                newTime = times[currentNode] + legTime
                
                # If we found a shorter path
                if newDistance < distances[neighbor]:
                    distances[neighbor] = newDistance
                    times[neighbor] = newTime
                    previous[neighbor] = currentNode
                    heapq.heappush(priorityQueue, (newDistance, neighbor))
        
        # Reconstruct path
        path = self._reconstructPath(previous, start, end)
        
        if path:
            return path, distances[end], times[end]
        else:
            return None, None, None
    
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
                        details['carriers'].add(carrier)
                
                details['segments'].append(segment)
                details['total_distance'] += segment['distance']
                details['total_time'] += segment['time']
        
        details['connections'] = len(path) - 1
        details['carriers'] = list(details['carriers'])
        
        return details
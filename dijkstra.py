# dijkstra.py
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
        priority_queue = [(0, start)]
        visited = set()
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            
            # Early exit if we reached destination
            if current_node == end:
                break
            
            # Skip if no neighbors
            if current_node not in self.graphDictionary:
                continue
                
            # Explore neighbors
            for neighbor, edge_data in self.graphDictionary[current_node].items():
                if neighbor in visited:
                    continue
                
                # Calculate new distance
                new_distance = distances[current_node] + edge_data['distance']
                
                # Get time from edge data
                leg_time = edge_data.get('time', 0)
                new_time = times[current_node] + leg_time
                
                # If we found a shorter path
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    times[neighbor] = new_time
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor))
        
        # Reconstruct path
        path = self._reconstruct_path(previous, start, end)
        
        if path:
            return path, distances[end], times[end]
        else:
            return None, None, None
    
    def _reconstruct_path(self, previous: dict, start: str, end: str):
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
        if code in self.airportGraph.airport_data:
            data = self.airportGraph.airport_data[code]
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
            from_code = path[i]
            to_code = path[i + 1]
            
            if from_code in self.graphDictionary and to_code in self.graphDictionary[from_code]:
                edge = self.graphDictionary[from_code][to_code]
                
                # Get airport names if available
                from_name = self.getName(from_code)
                to_name = self.getName(to_code)
                
                segment = {
                    'from': from_code,
                    'from_name': from_name,
                    'to': to_code,
                    'to_name': to_name,
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
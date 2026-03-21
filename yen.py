# yen.py
import heapq
import itertools
from dijkstra import Dijkstra


class Yen:
    def __init__(self, graph, dijkstra=None):
        self.graph = graph  # This is a WeightedGraph instance
        self.graphDictionary = graph.graph  # Keep for backward compatibility
        self.maxTransit = 2  # Internal constant for maximum transit flights
        if dijkstra is None:
            self.dijkstra = Dijkstra(graph)
        else:
            self.dijkstra = dijkstra

    def findKShortestPath(self, start, end, k, weight_type='distance'):
        """
        Find k shortest paths based on specified weight type with transit limit
        """
        if start not in self.graphDictionary:
            print(f"Start airport {start} not found in graph")
            return None
        if end not in self.graphDictionary:
            print(f"End airport {end} not found in graph")
            return None
        
        # Use Dijkstra with specified weight type
        path, dist, time = self.dijkstra.findShortestPath(start, end, weight_type)
        price = 0
        
        # If no path found, try to find any path within limit
        if not path:
            print(f"No direct path found, trying to find any path within transit limit")
            path, dist, time = self.dijkstra.findAllPathsWithMaxTransits(start, end)
            price = 0
        
        if not path:
            print(f"No path found from {start} to {end}")
            return []
        
        print(f"Initial path found: {' -> '.join(path)}")
        
        # Verify transit count
        if len(path) - 2 > self.maxTransit:
            print(f"Initial path exceeds transit limit: {len(path)-2} transits")
            return []
        
        # Store the appropriate metric based on weight_type
        primary_metric = 0
        if weight_type == 'time':
            primary_metric = time
        elif weight_type == 'price':
            primary_metric = price
        else:  # distance
            primary_metric = dist
        
        A = [{ 
            'path': path,
            'dist': dist,
            'time': time,
            'price': price,
            'primary_metric': primary_metric,
            'connections': len(path) - 1,
            'details': self.dijkstra.getRouteDetails(path) if hasattr(self.dijkstra, 'getRouteDetails') else None
        }]

        B = []
        queueCounter = itertools.count()

        for pathIndex in range(1, k):
            print(f"Looking for alternative path {pathIndex}")
            
            # Check if we have a previous path to work with
            if pathIndex - 1 >= len(A):
                print(f"No more paths in A at index {pathIndex-1}")
                break
                
            prev = A[pathIndex-1]['path']
            
            # Skip if prev is None or too short
            if not prev or len(prev) < 2:
                print(f"Previous path is invalid or too short")
                continue
                
            # Skip if we've reached the transit limit for spur paths
            if len(prev) - 2 >= self.maxTransit:
                print(f"Previous path already at transit limit")
                continue
                
            pathsFound = 0

            # For each possible spur node (except the last node)
            for spurIndex in range(len(prev) - 1):
                spurNode = prev[spurIndex]
                print(f"  Trying spur at index {spurIndex}: {spurNode}")
                
                # Check if we would exceed transit limit with this spur
                rootPath = prev[:spurIndex + 1]  # Include spur node
                rootTransits = len(rootPath) - 1 if rootPath else 0
                if rootTransits > self.maxTransit:
                    print(f"    Root path would exceed transit limit")
                    continue
                
                try:
                    # Use the WeightedGraph method to create a modified graph for spur calculation
                    modified_graph = self.graph.createGraphForYenSpur(A, prev, spurIndex)
                    
                    # Create a new Dijkstra instance with the modified graph
                    temp = self._createDijkstraWithModifiedGraph(modified_graph)

                    spurPath, spurDist, spurTime = temp.findShortestPath(
                        spurNode, end, weight_type
                    )
                    spurPrice = 0

                    if spurPath and len(spurPath) > 0:
                        print(f"    Found spur path: {' -> '.join(spurPath)}")
                        
                        # Root path should not include the spur node twice
                        # Root path already ends with spur node, so we exclude it from spur path
                        if spurPath[0] == spurNode:
                            spurPath = spurPath[1:]
                        
                        totalPath = rootPath + spurPath
                        
                        # Check total transit count
                        if len(totalPath) - 2 > self.maxTransit:
                            print(f"    Total path exceeds transit limit")
                            continue

                        totalDist, totalTime, totalPrice = self.calculatePathMetrics(totalPath)

                        # Calculate primary metric based on weight_type
                        primary_metric = 0
                        if weight_type == 'time':
                            primary_metric = totalTime
                        elif weight_type == 'price':
                            primary_metric = totalPrice
                        else:  # distance
                            primary_metric = totalDist

                        candidate = {
                            'path': totalPath,
                            'dist': totalDist,
                            'time': totalTime,
                            'price': totalPrice,
                            'primary_metric': primary_metric,
                            'connections': len(totalPath) - 1
                        }

                        if self.validCandidate(candidate, A, B):
                            print(f"    Adding candidate: {' -> '.join(totalPath)}")
                            heapq.heappush(B, (candidate['primary_metric'], next(queueCounter), candidate))
                            pathsFound += 1
                        else:
                            print(f"    Candidate already exists")
                    else:
                        print(f"    No spur path found from {spurNode} to {end}")
                        
                except Exception as e:
                    print(f"    Error in spur path calculation: {e}")
                    continue

            if not B:
                print(f"No candidates found in B, breaking")
                break

            # Get the best candidate
            try:
                _, _, bestCandidate = heapq.heappop(B)
                
                # Final transit check
                if len(bestCandidate['path']) - 2 <= self.maxTransit:
                    if hasattr(self.dijkstra, 'getRouteDetails'):
                        bestCandidate['details'] = self.dijkstra.getRouteDetails(bestCandidate['path'])
                    A.append(bestCandidate)
                    print(f"Added alternative path {pathIndex}: {' -> '.join(bestCandidate['path'])}")
                else:
                    print(f"Candidate exceeds transit limit")
            except IndexError:
                print(f"Error popping from B")
                break

        print(f"Found {len(A)-1} alternative paths")
        return A

    def _createDijkstraWithModifiedGraph(self, modified_graph):
        """
        Create a new Dijkstra instance with a modified graph
        """
        return Dijkstra(modified_graph)

    def calculatePathMetrics(self, path):
        """Calculate total distance, time, and price for a path"""
        totalDist = 0
        totalTime = 0
        totalPrice = 0
        
        if not path or len(path) < 2:
            return totalDist, totalTime, totalPrice
            
        for i in range(len(path) - 1):
            fromCode = path[i]
            toCode = path[i+1]

            if fromCode in self.graphDictionary and toCode in self.graphDictionary.get(fromCode, {}):
                edge = self.graphDictionary[fromCode][toCode]
                totalDist += edge.get('distance', 0)
                totalTime += edge.get('time', 0)
                totalPrice += edge.get('price', 0)

        return totalDist, totalTime, totalPrice
    
    def validCandidate(self, candidate, A, B):
        """Check if candidate path is unique"""
        if not candidate or 'path' not in candidate:
            return False
            
        candidateTuple = tuple(candidate['path'])

        # Check against accepted paths
        for pathData in A:
            if 'path' in pathData and tuple(pathData['path']) == candidateTuple:
                return False
            
        # Check against candidates in B
        for item in B:
            if len(item) >= 3 and 'path' in item[2]:
                if tuple(item[2]['path']) == candidateTuple:
                    return False
            
        return True
    
    def returnData(self, paths):
        """Format path data for output"""
        result = []
        if not paths:
            return result
            
        for i, pathData in enumerate(paths, 1):
            if not isinstance(pathData, dict):
                continue
                
            dist = pathData.get('dist', 0)
            time = pathData.get('time', 0)
            price = pathData.get('price', 0)
            path_list = pathData.get('path', [])
            connections = pathData.get('connections', len(path_list) - 1 if path_list else 0)

            pathDict = {
                'rank': i,
                'path': path_list,
                'path_display': ' -> '.join(path_list) if path_list else '',
                'dist': dist,
                'time': time,
                'price': price,
                'connections': connections,
                'segments': []
            }
            
            # Add segment details
            if 'details' in pathData and pathData['details'] and 'segments' in pathData['details']:
                for segment in pathData['details']['segments']:
                    segment_dict = {
                        'from': segment.get('from', ''),
                        'from_name': segment.get('from_name', '').split(',')[0] if segment.get('from_name') else '',
                        'to': segment.get('to', ''),
                        'to_name': segment.get('to_name', '').split(',')[0] if segment.get('to_name') else '',
                        'dist': segment.get('distance', 0),
                        'time': segment.get('time', 0),
                        'price': segment.get('price', 0),
                        'carriers': segment.get('carriers', [])
                    }
                    pathDict['segments'].append(segment_dict)
            
            result.append(pathDict)
        
        return result

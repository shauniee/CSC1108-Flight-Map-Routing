# yen.py
import heapq
import itertools

from copy import deepcopy
from dijkstra import Dijkstra


class Yen:
    def __init__(self, graph, dijkstra=None):
        self.graph = graph
        self.graphDictionary = graph.graph
        if dijkstra is None:
            self.dijkstra = Dijkstra(graph)
        else:
            self.dijkstra = dijkstra

    def findKShortestPath(self, start, end, k, weight_type='distance'):
        """
        Find k shortest paths based on specified weight type
        
        Args:
            start: Starting airport code
            end: Destination airport code
            k: Number of paths to find
            weight_type: 'distance', 'time', or 'price'
        """
        if start not in self.graphDictionary:
            return None
        if end not in self.graphDictionary:
            return None
        
        # Use Dijkstra with specified weight type
        path, dist, time, price = self.dijkstra.findShortestPath(start, end, weight_type)
        
        if not path:
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
            'details': self.dijkstra.getRouteDetails(path) }]

        B = []
        queueCounter = itertools.count()

        for pathIndex in range(1, k):
            prev = A[pathIndex-1]['path']
            pathsFound = 0

            for spurIndex in range(len(prev) - 1):
                spurNode = prev[spurIndex]
                updatedGraph = self.updateGraph(A, prev, spurIndex, start, end)

                if not updatedGraph:
                    continue
            
                temp = self.newDijkstra(updatedGraph)

                spurPath, spurDist, spurTime, spurPrice = temp.findShortestPath(spurNode, end, weight_type)

                if spurPath:
                    rootPath = prev[:spurIndex]
                    totalPath = rootPath + spurPath

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
                        heapq.heappush(B, (candidate['primary_metric'], next(queueCounter), candidate))
                        pathsFound += 1

            if not B:
                break

            _, _, bestCandidate = heapq.heappop(B)

            bestCandidate['details'] = self.dijkstra.getRouteDetails(bestCandidate['path'])
            A.append(bestCandidate)

        return A

    def updateGraph(self, A, prevPath, index, start, end):
        updatedGraph = {}
        for airport, connections in self.graphDictionary.items():
            updatedGraph[airport] = deepcopy(connections)

        for pathData in A:
            path = pathData['path']
            if len(path) > index+1:
                fromNode = path[index]
                toNode = path[index+1]

                if(fromNode in updatedGraph and toNode in updatedGraph[fromNode]):
                    del updatedGraph[fromNode][toNode]

        for node in prevPath[:index]:
            updatedGraph[node] = {}
            for airport in list(updatedGraph.keys()):
                if node in updatedGraph[airport]:
                    del updatedGraph[airport][node]
        return updatedGraph
    
    def newDijkstra(self, updatedGraph):
        temp = Dijkstra(self.graph)
        temp.graphDictionary = updatedGraph
        return temp
    
    def calculatePathMetrics(self, path):
        """Calculate total distance, time, and price for a path"""
        totalDist = 0
        totalTime = 0
        totalPrice = 0
        for i in range(len(path) - 1):
            fromCode = path[i]
            toCode = path[i+1]

            if (fromCode in self.graphDictionary and toCode in self.graphDictionary[fromCode]):
                edge = self.graphDictionary[fromCode][toCode]
                totalDist += edge['distance']
                totalTime += edge.get('time', 0)
                totalPrice += edge.get('price', 0)

        return totalDist, totalTime, totalPrice
    
    def validCandidate(self, candidate, A, B):
        candidateTuple = tuple(candidate['path'])

        for pathData in A:
            if tuple(pathData['path']) == candidateTuple:
                return False
            
        for (_, _, pathData) in B:
            if tuple(pathData['path']) == candidateTuple:
                return False
            
        return True
    
    def returnData(self, paths):
        result = []
        for i, pathData in enumerate(paths, 1):
            dist = pathData.get('dist', 0)
            time = pathData.get('time', 0)
            price = pathData.get('price', 0)
            connections = pathData.get('connections', len(pathData['path']) - 1)

            pathDict = {
                'rank': i,
                'path': pathData['path'],
                'path_display': ' -> '.join(pathData['path']),
                'dist': dist,
                'time': time,
                'price': price,
                'connections': connections,
                'segments': []
            }
            
            # Add segment details
            if 'details' in pathData:
                for segment in pathData['details']['segments']:
                    pathDict['segments'].append({
                        'from': segment['from'],
                        'from_name': segment['from_name'].split(',')[0],
                        'to': segment['to'],
                        'to_name': segment['to_name'].split(',')[0],
                        'dist': segment['distance'],
                        'time': segment['time'],
                        'price': segment.get('price', 0),
                        'carriers': segment.get('carriers', [])
                    })
            
            result.append(pathDict)
        
        return result
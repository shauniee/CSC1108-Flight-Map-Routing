import heapq
import itertools

from copy import deepcopy
from dijkstra import Dijkstra

class Yen:
    def __init__ (self, graph, dijkstra=None):
        self.graph = graph
        self.graphDictionary = graph.graph
        if dijkstra is None:
            self.dijkstra = Dijkstra(graph)
        else:
            self.dijkstra = dijkstra

    def findKShortestPath(self, start, end, k):
        if start not in self.graphDictionary:
            return None
        if end not in self.graphDictionary:
            return None
        
        path, dist, time = self.dijkstra.findShortestPath(start, end)
        
        if not path:
            return []
        
        A = [{ 
            'path' : path,
            'dist' : dist,
            'time' : time,
            'connections' : len(path) - 1,
            'details' : self.dijkstra.getRouteDetails(path) }]

        B = []
        queue_counter = itertools.count()

        for pathIndex in range(1, k):
            prev = A[pathIndex-1]['path']
            pathsFound = 0

            for spurIndex in range(len(prev) - 1):
                spurNode = prev[spurIndex]
                updatedGraph = self.updateGraph(A, prev, spurIndex, start, end)

                if not updatedGraph:
                    continue
            
                temp = self.newDijkstra(updatedGraph)

                spurPath, spurDist, spurTime = temp.findShortestPath(spurNode, end)

                if spurPath:
                    rootPath = prev[:spurIndex]
                    totalPath = rootPath + spurPath

                    totalDist, totalTime = self.calculatePath(totalPath)

                    candidate = {
                        'path': totalPath,
                        'dist': totalDist,
                        'time': totalTime,
                        'connections': len(totalPath) - 1
                    }

                    if self.validCandidate(candidate, A, B):
                        heapq.heappush(B, (candidate['dist'], next(queue_counter), candidate))
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
    
    def calculatePath(self, path):
        totalDist = 0
        totalTime = 0
        for i in range(len(path) - 1):
            fromCode = path[i]
            toCode = path[i+1]

            if (fromCode in self.graphDictionary and toCode in self.graphDictionary[fromCode]):
                edge = self.graphDictionary[fromCode][toCode]
                totalDist += edge['distance']
                totalTime += edge.get('time', 0)

        return totalDist, totalTime
    
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
            connections = pathData.get('connections', len(pathData['path']) - 1)

            pathDict = {
                'rank': i,
                'path': pathData['path'],
                'path_display': ' -> '.join(pathData['path']),
                'dist': dist,
                'time': time,
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
                        'carriers': segment.get('carriers', [])
                    })
            
            result.append(pathDict)
        
        return result

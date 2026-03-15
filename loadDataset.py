# loadDataset.py
import json
from pathlib import Path

class WeightedGraph:
    def __init__(self):
        # Graph representation: {airport_iata: {neighbor_iata: {distance, time, carriers}}}
        self.graph = {}
        self.airportData = {}  # Store the full airport data
        
    def buildGraphFromData(self, airportsData: dict):
        """
        Build graph from your airport dataset structure
        
        Args:
            airportsData: Dictionary of airport data with IATA codes as keys
        """
        self.airportData = airportsData
        
        for iata, airport in airportsData.items():
            # Initialize graph entry for this airport
            if iata not in self.graph:
                self.graph[iata] = {}
            
            # Add edges from routes
            if 'routes' in airport and isinstance(airport['routes'], list):
                for route in airport['routes']:
                    if not isinstance(route, dict):
                        continue
                        
                    destIata = route.get('iata')
                    if not destIata:
                        continue
                        
                    # Get distance and time
                    distance = route.get('km', 0)
                    time = route.get('min', 0)
                    
                    # Get carriers
                    carriers = []
                    if 'carriers' in route and isinstance(route['carriers'], list):
                        for carrier in route['carriers']:
                            if isinstance(carrier, dict) and 'name' in carrier:
                                carriers.append(carrier['name'])
                    
                    # Store edge with both distance and time
                    self.graph[iata][destIata] = {
                        'distance': distance,
                        'time': time,
                        'carriers': carriers
                    }
    
    def getAirportInfo(self, iataCode: str) -> dict:
        """Get information about a specific airport"""
        return self.airportData.get(iataCode, {})
    
    def getAllAirports(self) -> list:
        """Get list of all airport codes"""
        return list(self.graph.keys())
    
    def getConnections(self, iataCode: str) -> dict:
        """Get all connections from an airport"""
        return self.graph.get(iataCode, {})
    
    def getGraphStats(self) -> dict:
        """Get statistics about the graph"""
        totalAirports = len(self.graph)
        totalRoutes = sum(len(destinations) for destinations in self.graph.values())
        
        # Find airports with most connections
        airportConnections = []
        for airport, destinations in self.graph.items():
            airportConnections.append((airport, len(destinations)))
        
        airportConnections.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_airports': totalAirports,
            'total_routes': totalRoutes,
            'avg_routes_per_airport': totalRoutes / totalAirports if totalAirports > 0 else 0,
            'top_hubs': airportConnections[:10],
            'isolated_airports': [a for a, d in airportConnections if d == 0]
        }
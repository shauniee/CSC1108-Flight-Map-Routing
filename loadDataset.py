# loadDataset.py
import json
from pathlib import Path

class WeightedGraph:
    def __init__(self):
        # Graph representation: {airport_iata: {neighbor_iata: {distance, time, carriers}}}
        self.graph = {}
        self.airport_data = {}  # Store the full airport data
        
    def build_graph_from_data(self, airports_data: dict):
        """
        Build graph from your airport dataset structure
        
        Args:
            airports_data: Dictionary of airport data with IATA codes as keys
        """
        self.airport_data = airports_data
        
        for iata, airport in airports_data.items():
            # Initialize graph entry for this airport
            if iata not in self.graph:
                self.graph[iata] = {}
            
            # Add edges from routes
            if 'routes' in airport and isinstance(airport['routes'], list):
                for route in airport['routes']:
                    if not isinstance(route, dict):
                        continue
                        
                    dest_iata = route.get('iata')
                    if not dest_iata:
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
                    self.graph[iata][dest_iata] = {
                        'distance': distance,
                        'time': time,
                        'carriers': carriers
                    }
    
    def get_airport_info(self, iata_code: str) -> dict:
        """Get information about a specific airport"""
        return self.airport_data.get(iata_code, {})
    
    def get_all_airports(self) -> list:
        """Get list of all airport codes"""
        return list(self.graph.keys())
    
    def get_connections(self, iata_code: str) -> dict:
        """Get all connections from an airport"""
        return self.graph.get(iata_code, {})
    
    def get_graph_stats(self) -> dict:
        """Get statistics about the graph"""
        total_airports = len(self.graph)
        total_routes = sum(len(destinations) for destinations in self.graph.values())
        
        # Find airports with most connections
        airport_connections = []
        for airport, destinations in self.graph.items():
            airport_connections.append((airport, len(destinations)))
        
        airport_connections.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_airports': total_airports,
            'total_routes': total_routes,
            'avg_routes_per_airport': total_routes / total_airports if total_airports > 0 else 0,
            'top_hubs': airport_connections[:10],
            'isolated_airports': [a for a, d in airport_connections if d == 0]
        }
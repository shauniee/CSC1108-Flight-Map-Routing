# loadDataset.py
import json
from pathlib import Path
from copy import deepcopy


class WeightedGraph:
    def __init__(self):
        # Graph representation: {airport_iata: {neighbor_iata: {distance, time, carriers, price}}}
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
                    
                    # Calculate estimated price for this edge
                    # This is a simplified price calculation - you can make it more sophisticated
                    base_rate = 0.15
                    fuel_rate = 0.02
                    estimated_price = distance * (base_rate + fuel_rate)
                    
                    # Adjust price based on carriers if available
                    if carriers:
                        budgetAirlines = ['Scoot', 'Ryanair', 'AirAsia', 'Firefly']
                        premiumAirlines = ['Singapore Airlines', 'Emirates', 'Lufthansa', 
                                         'British Airways', 'Qatar Airways', 'Qantas']
                        
                        for carrier in carriers:
                            if carrier in budgetAirlines:
                                estimated_price *= 0.8
                                break
                            elif carrier in premiumAirlines:
                                estimated_price *= 1.2
                                break
                    
                    # Store edge with all metrics
                    self.graph[iata][destIata] = {
                        'distance': distance,
                        'time': time,
                        'price': round(estimated_price, 2),
                        'carriers': carriers
                    }
    
    def createModifiedCopy(self, removed_edges=None, removed_nodes=None):
        """
        Create a modified copy of this graph
        
        Args:
            removed_edges: List of tuples (from_node, to_node) to remove
            removed_nodes: List of nodes to isolate (remove all connections)
            
        Returns:
            A new WeightedGraph instance with modifications
        """
        removed_edges = removed_edges or []
        removed_nodes = removed_nodes or []
        
        # Create deep copy of the graph dictionary
        modified_graph_dict = {}
        for airport, connections in self.graph.items():
            modified_graph_dict[airport] = deepcopy(connections)
        
        # Remove specified edges
        for from_node, to_node in removed_edges:
            if from_node in modified_graph_dict and to_node in modified_graph_dict[from_node]:
                del modified_graph_dict[from_node][to_node]
        
        # Remove specified nodes (isolate them by clearing their outgoing edges
        # and removing incoming edges)
        for node in removed_nodes:
            if node in modified_graph_dict:
                modified_graph_dict[node] = {}
            
            # Remove incoming edges to this node
            for airport in list(modified_graph_dict.keys()):
                if node in modified_graph_dict[airport]:
                    del modified_graph_dict[airport][node]
        
        # Create new WeightedGraph instance with modifications
        modified_graph = WeightedGraph()
        modified_graph.airportData = self.airportData  # Share airport data
        modified_graph.graph = modified_graph_dict
        
        return modified_graph
    
    def createGraphForYenSpur(self, accepted_paths, prev_path, spur_index):
        """
        Convenience method to create a graph for Yen's algorithm spur path calculation
        
        Args:
            accepted_paths: List of already accepted paths (from Yen's A list)
            prev_path: The previous path being processed
            spur_index: The spur node index
            
        Returns:
            Modified WeightedGraph for spur path calculation
        """
        removed_edges = []
        
        # Validate inputs
        if not prev_path or spur_index >= len(prev_path):
            return self.createModifiedCopy()  # Return unmodified copy if invalid
        
        # Remove edges from accepted paths that share the root path
        for path_data in accepted_paths:
            if not isinstance(path_data, dict):
                continue
                
            path = path_data.get('path', [])
            if not path or len(path) <= spur_index + 1:
                continue
                
            from_node = path[spur_index]
            to_node = path[spur_index + 1]
            removed_edges.append((from_node, to_node))
        
        # Remove nodes in root path (except spur node)
        removed_nodes = []
        if spur_index > 0:
            removed_nodes = prev_path[:spur_index]
        
        return self.createModifiedCopy(
            removed_edges=removed_edges,
            removed_nodes=removed_nodes
        )
    
    def removeEdge(self, from_node, to_node):
        """
        Create a new graph with a specific edge removed
        
        Args:
            from_node: Source airport code
            to_node: Destination airport code
            
        Returns:
            New WeightedGraph with the specified edge removed
        """
        return self.createModifiedCopy(removed_edges=[(from_node, to_node)])
    
    def removeNode(self, node):
        """
        Create a new graph with a specific node isolated
        
        Args:
            node: Airport code to isolate
            
        Returns:
            New WeightedGraph with the node isolated
        """
        return self.createModifiedCopy(removed_nodes=[node])
    
    def getAirportInfo(self, iataCode: str) -> dict:
        """Get information about a specific airport"""
        return self.airportData.get(iataCode, {})
    
    def getAllAirports(self) -> list:
        """Get list of all airport codes"""
        return list(self.graph.keys())
    
    def getConnections(self, iataCode: str) -> dict:
        """Get all connections from an airport"""
        return self.graph.get(iataCode, {})
    
    def getEdge(self, from_node: str, to_node: str) -> dict:
        """Get edge information between two airports"""
        return self.graph.get(from_node, {}).get(to_node, {})
    
    def hasEdge(self, from_node: str, to_node: str) -> bool:
        """Check if an edge exists between two airports"""
        return to_node in self.graph.get(from_node, {})
    
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
import json
from collections import defaultdict

class AirlineClassifier:
    def __init__(self, dataset_file):
        """
        Initialize the classifier with your dataset
        """
        with open(dataset_file, 'r') as f:
            self.data = json.load(f)
        
        self.airline_details = {}  # Store airline name and IATA
        
        # Known budget airlines (LCCs)
        self.KNOWN_BUDGET_AIRLINES = {
            # Asia Pacific
            'TR': 'Scoot',
            '3K': 'Jetstar Asia',
            'GK': 'Jetstar Japan',
            'JQ': 'Jetstar Airways',
            'TT': 'Tigerair Australia',
            'AK': 'AirAsia',
            'QZ': 'Indonesia AirAsia',
            'FD': 'Thai AirAsia',
            'DJ': 'AirAsia Japan',
            'Z2': 'Philippines AirAsia',
            'D7': 'AirAsia X',
            'XJ': 'Thai AirAsia X',
            '5J': 'Cebu Pacific',
            'DG': 'Cebgo',
            'DD': 'Nok Air',
            'SL': 'Thai Lion Air',
            'JT': 'Lion Air',
            'ID': 'Batik Air',
            'OD': 'Batik Air Malaysia',
            'IW': 'Wings Air',
            'QG': 'Citilink',
            'IN': 'Nam Air',
            '9C': 'Spring Airlines',
            'AQ': '9 Air Co',
            'PN': 'West Air (China)',
            '8L': 'Lucky Air',
            'GJ': 'Loong Air',
            'GT': 'Air Guilin',
            'GY': 'Colorful Guizhou Airlines',
            'BK': 'Okay Airways',
            'GS': 'Tianjin Airlines',
            'HO': 'Juneyao Airlines',
            'EU': 'Chengdu Airlines',
            'KY': 'Kunming Airlines',
            'QW': 'Qingdao Airlines',
            'RY': 'Jiangxi Airlines',
            'GX': 'Guangxi Beibu Gulf Airlines',
            'Y8': 'Suparna Airlines',
            'JR': 'Joy Air',
            'FU': 'Fuzhou Airlines',
            'UQ': 'Urumqi Airlines',
            '9H': 'Air Changan',
            
            # Europe
            'FR': 'Ryanair',
            'RK': 'Ryanair UK',
            'U2': 'easyJet',
            'DS': 'easyJet Switzerland',
            'EC': 'easyJet Europe',
            'W6': 'Wizz Air',
            'W9': 'Wizz Air UK',
            'LS': 'Jet2.com',
            'DY': 'Norwegian Air Shuttle',
            'D8': 'Norwegian Air International',
            'VF': 'Norwegian Air UK',
            'DI': 'Norwegian Air Argentina',
            'TO': 'Transavia France',
            'HV': 'Transavia',
            'VY': 'Vueling',
            'EW': 'Eurowings',
            '4U': 'Germanwings',
            'HG': 'Niki',
            'AB': 'Air Berlin',
            
            # North America
            'WN': 'Southwest Airlines',
            'NK': 'Spirit Airlines',
            'B6': 'JetBlue',
            'G4': 'Allegiant Air',
            'F9': 'Frontier Airlines',
            'WS': 'WestJet',
            'S7': 'WestJet Encore',
            'SY': 'Sun Country Airlines',
            
            # Middle East
            'G9': 'Air Arabia',
            '3L': 'Air Arabia Abu Dhabi',
            'FZ': 'flydubai',
            'XY': 'flynas',
            'OV': 'Salam Air',
            
            # Africa
            'FA': 'FlySafair',
            'MN': 'Kulula.com',
            '4Z': 'South African Express',
            
            # Latin America
            'AD': 'Azul Brazilian Airlines',
            'G3': 'Gol Transportes Aéreos',
            'JA': 'JetSmart',
            'H2': 'Sky Airline',
            'VB': 'Viva Aerobus',
            'Y4': 'Volaris',
        }
        
        # Known legacy/premium airlines (full-service carriers)
        self.KNOWN_PREMIUM_AIRLINES = {
            # Major alliances
            'AA': 'American Airlines',
            'DL': 'Delta Air Lines',
            'UA': 'United Airlines',
            'AC': 'Air Canada',
            'LH': 'Lufthansa',
            'BA': 'British Airways',
            'AF': 'Air France',
            'KL': 'KLM Royal Dutch Airlines',
            'EY': 'Etihad Airways',
            'EK': 'Emirates',
            'QR': 'Qatar Airways',
            'SQ': 'Singapore Airlines',
            'CX': 'Cathay Pacific',
            'JL': 'Japan Airlines',
            'NH': 'All Nippon Airways',
            'KE': 'Korean Air',
            'OZ': 'Asiana Airlines',
            'CA': 'Air China',
            'CZ': 'China Southern Airlines',
            'MU': 'China Eastern Airlines',
            'HU': 'Hainan Airlines',
            '3U': 'Sichuan Airlines',
            'ZH': 'Shenzhen Airlines',
            'MF': 'Xiamen Airlines',
        }
        
        self._process_data()
    
    def _process_data(self):
        """Extract airline information from the dataset"""
        for airport_code, airport_data in self.data.items():
            if 'routes' not in airport_data:
                continue
                
            for route in airport_data['routes']:
                for carrier in route.get('carriers', []):
                    carrier_iata = carrier.get('iata')
                    carrier_name = carrier.get('name')
                    
                    if carrier_iata and carrier_name:
                        self.airline_details[carrier_iata] = carrier_name
    
    def get_classifications(self):
        """
        Get classifications with only IATA and airline name
        """
        classifications = {
            'budget': [],
            'premium': [],
            'unknown': []  # Airlines not in either known list
        }
        
        for iata, name in self.airline_details.items():
            if iata in self.KNOWN_BUDGET_AIRLINES:
                classifications['budget'].append({
                    'iata': iata,
                    'name': name
                })
            elif iata in self.KNOWN_PREMIUM_AIRLINES:
                classifications['premium'].append({
                    'iata': iata,
                    'name': name
                })
            else:
                classifications['unknown'].append({
                    'iata': iata,
                    'name': name
                })
        
        # Sort each list by name
        for category in classifications:
            classifications[category].sort(key=lambda x: x['name'])
        
        return classifications
    
    def print_report(self):
        """Print simple report with counts"""
        classifications = self.get_classifications()
        
        print("=" * 60)
        print("AIRLINE CLASSIFICATION REPORT")
        print("=" * 60)
        
        print(f"\nBudget Airlines: {len(classifications['budget'])}")
        print(f"Premium Airlines: {len(classifications['premium'])}")
        print(f"Unknown Airlines: {len(classifications['unknown'])}")
        
        # Show sample of each category
        print("\nSample Budget Airlines (first 10):")
        for airline in classifications['budget'][:10]:
            print(f"  • {airline['iata']} - {airline['name']}")
        
        print("\nSample Premium Airlines (first 10):")
        for airline in classifications['premium'][:10]:
            print(f"  • {airline['iata']} - {airline['name']}")
    
    def export_classifications(self, output_file='airline_classifications.json'):
        """
        Export only IATA and name for budget and premium airlines
        """
        classifications = self.get_classifications()
        
        # Create clean export with only what we need
        export_data = {
            'budget_airlines': classifications['budget'],
            'premium_airlines': classifications['premium'],
            'statistics': {
                'total_budget': len(classifications['budget']),
                'total_premium': len(classifications['premium']),
                'total_unknown': len(classifications['unknown']),
                'total_airlines': len(classifications['budget']) + len(classifications['premium']) + len(classifications['unknown'])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n✓ Classifications exported to {output_file}")
        print(f"  • {export_data['statistics']['total_budget']} budget airlines")
        print(f"  • {export_data['statistics']['total_premium']} premium airlines")

# Even simpler version - just get the lists
def get_airline_lists(dataset_file):
    """
    Quick function to just get the airline lists
    Returns: (budget_list, premium_list)
    """
    classifier = AirlineClassifier(dataset_file)
    classifications = classifier.get_classifications()
    
    return classifications['budget'], classifications['premium']

# Main execution
if __name__ == "__main__":
    dataset_file = "airline_routes.json"  # Update this path
    
    print("Initializing Airline Classifier...")
    classifier = AirlineClassifier(dataset_file)
    
    # Print simple report
    classifier.print_report()
    
    # Export clean JSON with only IATA and name
    classifier.export_classifications('airline_classifications.json')
    
    # Example: Get the lists directly
    budget_airlines, premium_airlines = get_airline_lists(dataset_file)
    
    print("\n" + "=" * 60)
    print("FIRST 5 BUDGET AIRLINES:")
    for airline in budget_airlines[:5]:
        print(f"  {airline['iata']}: {airline['name']}")
    
    print("\nFIRST 5 PREMIUM AIRLINES:")
    for airline in premium_airlines[:5]:
        print(f"  {airline['iata']}: {airline['name']}")
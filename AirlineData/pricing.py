import json

class PriceCalculation:
    def __init__(self, airlineClassificationFile='airline_classifications.json'):
        self.baseRate = 0.15
        self.fuelRate = 0.02

        self.majorHubs = {
            # Middle East
            "DOH": 0.70,
            "DXB": 0.70,
            "IST": 0.75,
            "AUH": 0.8,

            # Europe
            "AMS": 0.8,
            "FRA": 0.8,

            # APAC
            "KUL": 0.75,
            "HKG": 0.75,
            
            # North America
            "ATL": 0.75,
            "ORD": 0.8,
        }
        
        # Load airline classifications
        self.budgetAirlines = {}
        self.premiumAirlines = {}
        self.loadAirlineClassifications(airlineClassificationFile)
    
    def loadAirlineClassifications(self, classificationFile):
        try:
            with open(classificationFile, 'r') as f:
                data = json.load(f)
            
            # Convert lists to dictionaries for easy lookup
            self.budgetAirlines = {
                airline['iata']: airline['name'] 
                for airline in data.get('budget_airlines', [])
            }
            
            self.premiumAirlines = {
                airline['iata']: airline['name'] 
                for airline in data.get('premium_airlines', [])
            }
            
            print(f"✓ Loaded {len(self.budgetAirlines)} budget airlines and {len(self.premiumAirlines)} premium airlines")

        except Exception as e:
            print(f"Error loading classification file: {e}")
            # Set empty dictionaries if error
            self.budgetAirlines = {}
            self.premiumAirlines = {}
    
    def calculatePrice(self, fromAirport, toAirport, distance, carriers=None, directFlight=False, connectingAirport=None):
        basePrice = distance * self.baseRate
        fuelPrice = distance * self.fuelRate
        price = basePrice + fuelPrice

        # Direct flight premium surcharge
        if directFlight:
            price *= 1.1

        # Discount for connecting via major hubs
        if connectingAirport in self.majorHubs:
            discountRate = self.majorHubs[connectingAirport]
            price *= discountRate
        # Discount for transit flights (Non-major hubs)
        elif connectingAirport is not None:
            discountRate = 0.9
            price *= discountRate

        # Apply airline factor based on carrier type
        if carriers:
            price, airlineType = self.applyAirlineFactor(price, carriers)
        else:
            airlineType = 'Standard'

        return {
            'price': round(price, 2),
            'breakdown': {
                'base': round(basePrice, 2),
                'fuel': round(fuelPrice, 2),
                'total': round(price, 2)
            },
            'airlineInfo': {
                'type': airlineType,
                'carriers': carriers if carriers else []
            }
        }
    
    def applyAirlineFactor(self, price, carriers):
        if not carriers:
            return price, 'Standard'
        
        # Check if any carrier is premium (premium takes precedence for pricing)
        for carrier in carriers:
            if carrier in self.premiumAirlines:
                adjustedPrice = price * 1.2
                return adjustedPrice, 'Premium'
        
        # Check if any carrier is budget
        for carrier in carriers:
            if carrier in self.budgetAirlines:
                adjustedPrice = price * 0.8
                return adjustedPrice, 'Budget'
        
        # Standard airline type - no adjustment
        return price, 'Standard'
    
    def getAirlineName(self, carrierIata):
        if carrierIata in self.premiumAirlines:
            return self.premiumAirlines[carrierIata]
        elif carrierIata in self.budgetAirlines:
            return self.budgetAirlines[carrierIata]
        else:
            return f"Standard Airline ({carrierIata})"
    
    def getAirlineType(self, carrierIata):
        if carrierIata in self.premiumAirlines:
            return 'Premium'
        elif carrierIata in self.budgetAirlines:
            return 'Budget'
        else:
            return 'Standard'
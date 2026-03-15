class priceCalculation:
    def __init__(self):
        self.baseRate = 0.15
        self.fuelRate = 0.02

        self.major_hubs = {
            #Middle East
            "DOH": .70,
            "DXB": .70,
            "IST": .75,
            "AUH": .8,

            #Europe
            "AMS": .8,
            "FRA": .8,

            #APAC
            "KUL": .75,
            "HKG": .75,
            
            #North America
            "ATL": .75,
            "ORD": .8,
        }

    def calculatePrice(self, fromAirport, toAirport, distance, carrier = None, directFlight = False, connectingAirport = None):
        basePrice = distance * self.baseRate
        fuelPrice = distance * self.fuelRate
        price = basePrice + fuelPrice

        #direct flight premium surcharge
        if directFlight == True: 
            price *= 1.1

        #discount for connecting via major hubs
        if connectingAirport in self.major_hubs:
            discountRate = self.major_hubs[connectingAirport]
            price *= discountRate

        # Discount for transit flights (Non-major hubs)
        elif connectingAirport is not None:  
            discountRate = 0.9 
            price *= discountRate

        if carrier:
            price = self.applyAirlineFactor(price, carrier)

        return {
            'price': round(price, 2),
            'breakdown': {
                'base': round(basePrice, 2),
                'fuel': round(fuelPrice, 2),
                'total': round(price, 2)
            }
        }
    
    def applyAirlineFactor(self, price, carriers):
        budgetAirlines = ['Scoot', 'Ryanair', 'AirAsia', 'Firefly']
        premiumAirlines = ['Singapore Airlines', 'Emirates', 'Lufthansa', 'British Airways', 'Qatar Airways', 'Qantas']
    
        for carrier in carriers:
            if carrier in budgetAirlines:
                price *= .8
                break
            elif carrier in premiumAirlines:
                price *= 1.2

        return price
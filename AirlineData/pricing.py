import json


class PriceCalculation:
    def __init__(self, airlineClassificationFile="airline_classifications.json"):
        self.baseRate = 0.10
        self.fuelRate = 0.05

        self.majorHubs = {
            "DOH": 0.70,
            "DXB": 0.70,
            "IST": 0.75,
            "AUH": 0.8,
            "AMS": 0.8,
            "FRA": 0.8,
            "KUL": 0.75,
            "HKG": 0.75,
            "ATL": 0.75,
            "ORD": 0.8,
        }

        self.budgetAirlines = {}
        self.premiumAirlines = {}
        self.budgetAirlineNames = {}
        self.premiumAirlineNames = {}
        self.loadAirlineClassifications(airlineClassificationFile)

    def loadAirlineClassifications(self, classificationFile):
        try:
            with open(classificationFile, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.budgetAirlines = {
                airline["iata"]: airline["name"]
                for airline in data.get("budget_airlines", [])
            }
            self.budgetAirlineNames = {
                airline["name"].strip().lower(): airline["iata"]
                for airline in data.get("budget_airlines", [])
                if airline.get("name")
            }

            self.premiumAirlines = {
                airline["iata"]: airline["name"]
                for airline in data.get("premium_airlines", [])
            }
            self.premiumAirlineNames = {
                airline["name"].strip().lower(): airline["iata"]
                for airline in data.get("premium_airlines", [])
                if airline.get("name")
            }

            print(
                f"Loaded {len(self.budgetAirlines)} budget airlines and "
                f"{len(self.premiumAirlines)} premium airlines"
            )

        except Exception as e:
            print(f"Error loading classification file: {e}")
            self.budgetAirlines = {}
            self.premiumAirlines = {}
            self.budgetAirlineNames = {}
            self.premiumAirlineNames = {}

    def _normalizeCarrier(self, carrier):
        if not isinstance(carrier, str):
            return ""
        return carrier.strip()

    def _resolveCarrierType(self, carrier):
        carrier = self._normalizeCarrier(carrier)
        if not carrier:
            return "Standard"

        carrier_key = carrier.upper()
        carrier_name = carrier.lower()

        if carrier_key in self.premiumAirlines or carrier_name in self.premiumAirlineNames:
            return "Premium"
        if carrier_key in self.budgetAirlines or carrier_name in self.budgetAirlineNames:
            return "Budget"
        return "Standard"

    def getRateAdjustmentLabel(self, airlineType):
        if airlineType == "Premium":
            return "+20%"
        if airlineType == "Budget":
            return "-20%"
        return "0%"

    def applyAirlineTypeFactor(self, price, airlineType):
        if airlineType == "Premium":
            return price * 1.2
        if airlineType == "Budget":
            return price * 0.8
        return price

    def calculateBaseSegmentPrice(self, distance, directFlight=False, connectingAirport=None):
        basePrice = distance * self.baseRate
        fuelPrice = distance * self.fuelRate
        price = basePrice + fuelPrice

        if directFlight:
            price *= 1.1

        if connectingAirport in self.majorHubs:
            price *= self.majorHubs[connectingAirport]
        elif connectingAirport is not None:
            price *= 0.9

        return {
            "base": round(basePrice, 2),
            "fuel": round(fuelPrice, 2),
            "pre_airline_total": round(price, 2),
        }

    def calculatePrice(self, fromAirport, toAirport, distance, carriers=None, directFlight=False, connectingAirport=None):
        base_info = self.calculateBaseSegmentPrice(
            distance,
            directFlight=directFlight,
            connectingAirport=connectingAirport,
        )
        price = base_info["pre_airline_total"]

        if carriers:
            price, airlineType = self.applyAirlineFactor(price, carriers)
        else:
            airlineType = "Standard"

        return {
            "price": round(price, 2),
            "breakdown": {
                "base": base_info["base"],
                "fuel": base_info["fuel"],
                "total": round(price, 2),
            },
            "airlineInfo": {
                "type": airlineType,
                "carriers": carriers if carriers else [],
            },
        }

    def applyAirlineFactor(self, price, carriers):
        if not carriers:
            return price, "Standard"

        for carrier in carriers:
            if self._resolveCarrierType(carrier) == "Budget":
                return price * 0.8, "Budget"

        for carrier in carriers:
            if self._resolveCarrierType(carrier) == "Premium":
                return price * 1.2, "Premium"

        return price, "Standard"

    def getCarrierPriceOptions(self, distance, carriers=None, directFlight=False, connectingAirport=None):
        base_info = self.calculateBaseSegmentPrice(
            distance,
            directFlight=directFlight,
            connectingAirport=connectingAirport,
        )
        base_price = base_info["pre_airline_total"]
        options = []

        for carrier in carriers or []:
            carrier_name = self.getAirlineName(carrier)
            airline_type = self.getAirlineType(carrier)
            adjusted_price = round(self.applyAirlineTypeFactor(base_price, airline_type), 2)
            options.append(
                {
                    "carrier": carrier_name,
                    "type": airline_type,
                    "rate_adjustment": self.getRateAdjustmentLabel(airline_type),
                    "price": adjusted_price,
                }
            )

        options.sort(key=lambda item: (item["price"], item["carrier"]))
        return options

    def getAirlineName(self, carrierIata):
        carrier = self._normalizeCarrier(carrierIata)
        carrier_key = carrier.upper()
        carrier_name = carrier.lower()

        if carrier_key in self.premiumAirlines:
            return self.premiumAirlines[carrier_key]
        if carrier_key in self.budgetAirlines:
            return self.budgetAirlines[carrier_key]
        if carrier_name in self.premiumAirlineNames or carrier_name in self.budgetAirlineNames:
            return carrier
        return carrier or "Standard Airline"

    def getAirlineType(self, carrierIata):
        return self._resolveCarrierType(carrierIata)

from __future__ import annotations
import math
import random
from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "AirlineData"))
from AirlineData.pricing import PriceCalculation


class FlightSchedule:

    _DEPARTURE_WINDOWS = [
        (5,  7),    # early morning
        (7,  9),    # morning rush
        (9,  12),   # late morning
        (12, 14),   # midday
        (14, 17),   # afternoon
        (17, 20),   # evening rush
        (20, 23),   # night
    ]

    # Real aircraft types matched to route distance
    _AIRCRAFT = {
        "short":  ["Boeing 737-800", "Airbus A320neo", "Embraer E190"],
        "medium": ["Boeing 737 MAX 8", "Airbus A321neo", "Boeing 757-200"],
        "long":   ["Boeing 787-9 Dreamliner", "Airbus A350-900", "Boeing 777-300ER"],
    }

    EARTH_RADIUS_KM: float = 6_371.0

    def __init__(self, airport_meta: dict, graph: dict, price_calculator: PriceCalculation = None):
        self.airport_meta = airport_meta
        self.graph = graph
        self.priceCalculator = price_calculator if price_calculator else PriceCalculation()

    def generate(
        self,
        src:         str,
        dst:         str,
        date:        datetime | None = None,
        num_flights: int             = 8,
    ) -> dict:
        """
        Generate a daily flight schedule from *src* to *dst*.

        Returns a dict with: src, dst, src_meta, dst_meta,
        distance_km, co2_kg, duration_label, date_label, flights list.
        """
        src_meta = self.airport_meta.get(src)
        dst_meta = self.airport_meta.get(dst)
        if not src_meta or not dst_meta:
            return {"error": "Unknown airport code", "flights": []}

        if date is None:
            date = datetime.now(timezone.utc)

        edge = self.graph.get(src, {}).get(dst, {})
        if not edge:
            return {"error": "No direct route in dataset", "flights": []}

        # Use real distance and flight time from dataset
        distance_km = float(edge.get("distance") or 0)
        if distance_km <= 0:
            distance_km = self._haversine_meta(src_meta, dst_meta)

        flight_minutes = int(round(float(edge.get("time") or 0)))
        if flight_minutes <= 0:
            flight_minutes = self._flight_minutes(distance_km)

        # Use real carriers from dataset
        carriers = edge.get("carriers") or []
        carriers = [c for c in carriers if isinstance(c, str) and c.strip()]
        if not carriers:
            carriers = ["Charter"]

        # Stable seed so same route = same schedule each day
        seed = hash(f"{src}{dst}{date.strftime('%Y%m%d')}") & 0xFFFFFFFF
        rng  = random.Random(seed)

        flights_target = max(1, min(num_flights, len(carriers) * 2, 12))
        departures     = self._generate_departures(flights_target, rng)
        airlines       = [carriers[i % len(carriers)] for i in range(flights_target)]

        flights = []
        for i, (dep_hour, dep_min) in enumerate(departures):
            airline_name  = airlines[i]
            airline_code  = self._airline_code(airline_name)
            flight_number = f"{airline_code}{200 + i}"

            dep_dt = date.replace(
                hour=dep_hour, minute=dep_min, second=0, microsecond=0,
                tzinfo=timezone.utc,
            )
            arr_dt = dep_dt + timedelta(minutes=flight_minutes)
            
            airline_type = self._get_airline_type(airline_name) 

            base_result = self.priceCalculator.calculatePrice(
                fromAirport=src,
                toAirport=dst,
                distance=distance_km,
                carriers=[airline_name],
                directFlight=False,
            )
            
    
            base_price = base_result['price']
            if airline_type == "Premium":
                base_price *= 1.2
            elif airline_type == "Budget":
                base_price *= 0.8
            
            multiplier = self._price_multiplier(dep_hour, rng)
            price = round(base_price * multiplier, 2)

            flights.append({
                "flight_number":  flight_number,
                "airline":        airline_name,
                "departure_time": dep_dt.strftime("%H:%M"),
                "arrival_time":   arr_dt.strftime("%H:%M"),
                "duration_label": self._minutes_to_label(flight_minutes),
                "duration_min":   flight_minutes,
                "price":          price,
                "airline_type":   airline_type,
                })

        flights.sort(key=lambda f: f["departure_time"])

        return {
            "src":            src,
            "dst":            dst,
            "src_meta":       src_meta,
            "dst_meta":       dst_meta,
            "distance_km":    round(distance_km, 1),
            "flight_minutes": flight_minutes,
            "duration_label": self._minutes_to_label(flight_minutes),
            "date_label":     date.strftime("%A, %d %B %Y"),
            "flights":        flights,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _generate_departures(self, n: int, rng: random.Random) -> list:
        slots = []
        for start, end in self._DEPARTURE_WINDOWS:
            for h in range(start, end):
                slots.append(h)
        chosen_hours = rng.choices(slots, k=n)
        departures = []
        for h in chosen_hours:
            m = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
            departures.append((h, m))
        return departures

    def _airline_code(self, airline_name: str) -> str:
        letters = "".join(ch for ch in airline_name.upper() if ch.isalpha())
        if len(letters) >= 2:
            return letters[:2]
        if len(letters) == 1:
            return f"{letters}X"
        return "XX"

    def _price_multiplier(self, hour: int, rng: random.Random) -> float:
        if 7 <= hour <= 9 or 17 <= hour <= 20:
            return rng.uniform(1.15, 1.45)
        if 0 <= hour <= 5:
            return rng.uniform(0.70, 0.90)
        return rng.uniform(0.95, 1.10)

    def _flight_minutes(self, distance_km: float) -> int:
        return max(30, int(round((distance_km / 850.0) * 60 + 18)))

    def _minutes_to_label(self, total_minutes: int) -> str:
        hours, mins = divmod(total_minutes, 60)
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"

    def _haversine_meta(self, meta1: dict, meta2: dict) -> float:
        lat1, lon1 = meta1.get("latitude"), meta1.get("longitude")
        lat2, lon2 = meta2.get("latitude"), meta2.get("longitude")
        if None in (lat1, lon1, lat2, lon2):
            return 0.0
        return self._haversine(lat1, lon1, lat2, lon2)

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        R = self.EARTH_RADIUS_KM
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi       = math.radians(lat2 - lat1)
        dlambda    = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(a))
    
    def _get_airline_type(self, airline_name: str) -> str:
        pc = self.priceCalculator
        name_upper = airline_name.upper()
        for iata, name in pc.premiumAirlines.items():
            if name.upper() == name_upper:
                return "Premium"
        for iata, name in pc.budgetAirlines.items():
            if name.upper() == name_upper:
                return "Budget"
        return "Standard"
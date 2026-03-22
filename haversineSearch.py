from __future__ import annotations
import math


class HaversineSearch:
    """
    Great-circle distance calculations and geographic radius search
    over an airport dictionary.

    Parameters
    ----------
    airports : dict[str, Airport]
        Dictionary mapping IATA code → Airport object.
        Each Airport must expose  .lat  and  .lon  attributes (decimal degrees).
    """

    # Mean radius of the Earth in kilometres (IUPAC value)
    EARTH_RADIUS_KM: float = 6_371.0

    def __init__(self, airports: dict):
        self.airports = airports

    # Core formula 

    def distance(self, code1: str, code2: str) -> float:
        """
        Compute the great-circle distance in km between two airports.

        Parameters
        ----------
        code1, code2 : str  –  IATA airport codes (e.g. "SIN", "LHR")

        Returns
        -------
        float  –  distance in km, or 0.0 if either airport is unknown.
        """
        a1 = self.airports.get(code1)
        a2 = self.airports.get(code2)
        if not a1 or not a2:
            return 0.0
        return self._haversine(a1.lat, a1.lon, a2.lat, a2.lon)

    def distance_from_coords(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """
        Compute the great-circle distance in km between two raw
        (lat, lon) coordinate pairs.  Useful when you don't have an
        Airport object handy.
        """
        return self._haversine(lat1, lon1, lat2, lon2)

    # Radius search

    def nearby_airports(
        self,
        code:      str,
        radius_km: float = 300.0,
        limit:     int   = 25,
    ) -> list[tuple[float, object]]:
        """
        Find all airports within *radius_km* km of the given airport.

        Parameters
        ----------
        code      : str   –  IATA code of the origin airport
        radius_km : float –  search radius in kilometres (default 300)
        limit     : int   –  maximum number of results to return (default 25)

        Returns
        -------
        List of (distance_km, Airport) tuples sorted by distance ascending.
        Returns an empty list if the origin code is unknown.
        """
        origin = self.airports.get(code)
        if not origin:
            return []

        results: list[tuple[float, object]] = []
        for other_code, other_ap in self.airports.items():
            if other_code == code:
                continue
            d = self._haversine(origin.lat, origin.lon, other_ap.lat, other_ap.lon)
            if d <= radius_km:
                results.append((d, other_ap))

        results.sort(key=lambda x: x[0])
        return results[:limit]

    def nearby_from_coords(
        self,
        lat:       float,
        lon:       float,
        radius_km: float = 300.0,
        limit:     int   = 25,
    ) -> list[tuple[float, object]]:
        """
        Find airports within *radius_km* of an arbitrary (lat, lon) point.
        Useful for "nearest airport to my current GPS location" queries.

        Returns
        -------
        List of (distance_km, Airport) tuples sorted by distance ascending.
        """
        results: list[tuple[float, object]] = []
        for code, ap in self.airports.items():
            d = self._haversine(lat, lon, ap.lat, ap.lon)
            if d <= radius_km:
                results.append((d, ap))
        results.sort(key=lambda x: x[0])
        return results[:limit]

    def closest_airport(self, lat: float, lon: float) -> tuple[float, object] | None:
        """
        Return the single closest airport to the given coordinates.

        Returns (distance_km, Airport) or None if the airport dict is empty.
        """
        best: tuple[float, object] | None = None
        for ap in self.airports.values():
            d = self._haversine(lat, lon, ap.lat, ap.lon)
            if best is None or d < best[0]:
                best = (d, ap)
        return best

    # CO₂ helper (distance-based estimate) 

    @staticmethod
    def co2_kg(km: float) -> float:
        """
        Estimated CO₂ emission per passenger in kg.
        Uses ICAO standard factor: ~0.255 kg CO₂ per km.

        Parameters
        ----------
        km : float  –  flight distance in kilometres

        Returns
        -------
        float  –  CO₂ in kg (rounded to 1 decimal place)
        """
        return round(km * 0.255, 1)

    #Private implementation 
    def _haversine(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """Internal Haversine computation on raw decimal-degree coordinates."""
        R = self.EARTH_RADIUS_KM
        phi1, phi2   = math.radians(lat1), math.radians(lat2)
        dphi         = math.radians(lat2 - lat1)
        dlambda      = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(a))
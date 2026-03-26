"""
External service adapters — Adapter pattern.

TransitProvider defines the interface. GTFSAdapter and CityAPIAdapter adapt
two different external APIs to that interface. TransitFacade aggregates them
so the rest of the app talks to one unified object.
"""


class TransitProvider:
    """Interface all transit adapters must implement."""

    def get_nearby_stops(self, lat, lon):
        raise NotImplementedError

    def get_next_departures(self, stop_id):
        raise NotImplementedError


class GTFSAdapter(TransitProvider):
    """Adapts a GTFS-based public transit feed."""

    def get_nearby_stops(self, lat, lon):
        # Stub: would query a GTFS API endpoint
        return [
            {"id": "GTFS-001", "name": "Central Station", "distance_m": 120},
            {"id": "GTFS-002", "name": "Market St & 3rd", "distance_m": 340},
        ]

    def get_next_departures(self, stop_id):
        return [
            {"route": "Green Line", "destination": "Downtown", "minutes": 3},
            {"route": "Green Line", "destination": "Airport", "minutes": 11},
        ]


class CityAPIAdapter(TransitProvider):
    """Adapts a city-provided REST transit API."""

    def get_nearby_stops(self, lat, lon):
        return [
            {"id": "CITY-101", "name": "Bus Terminal North", "distance_m": 210},
            {"id": "CITY-102", "name": "Riverside Tram Stop", "distance_m": 480},
        ]

    def get_next_departures(self, stop_id):
        return [
            {"route": "Route 12", "destination": "West End", "minutes": 7},
            {"route": "Tram 4", "destination": "Old Town", "minutes": 15},
        ]


class TransitFacade:
    """Aggregates multiple TransitProvider adapters into one unified interface."""

    def __init__(self):
        self._providers = [GTFSAdapter(), CityAPIAdapter()]

    def get_nearby_stops(self, lat=45.4972, lon=-73.6103):
        results = []
        for provider in self._providers:
            results.extend(provider.get_nearby_stops(lat, lon))
        return sorted(results, key=lambda s: s["distance_m"])

    def get_next_departures(self, stop_id):
        for provider in self._providers:
            try:
                return provider.get_next_departures(stop_id)
            except Exception:
                continue
        return []


class ParkingLot:
    """Stub parking lot data model for external parking service."""

    def __init__(self, lot_id, name, address, total_spots, available_spots, hourly_rate, city="MTL"):
        self.lot_id = lot_id
        self.name = name
        self.address = address
        self.total_spots = total_spots
        self.available_spots = available_spots
        self.hourly_rate = hourly_rate
        self.city = city

    @property
    def occupancy_pct(self):
        if self.total_spots == 0:
            return 0
        return round((1 - self.available_spots / self.total_spots) * 100)


class ParkingService:
    """Stub parking service — returns hardcoded lots (would call external API)."""

    def get_nearby_lots(self):
        return [
            ParkingLot("P1",  "Complexe Desjardins",       "150 Rue Sainte-Catherine O", 320,  85,  3.50, "MTL"),
            ParkingLot("P2",  "Place Ville Marie",          "1 Pl. Ville Marie",          500, 210,  4.00, "MTL"),
            ParkingLot("P3",  "Quartier des Spectacles",    "175 Rue Sainte-Catherine E",  80,   0,   2.50, "MTL"),
            ParkingLot("P4",  "Galeries Laval",             "1600 Boul. Le Corbusier",    450, 180,  2.75, "LAV"),
            ParkingLot("P5",  "Centropolis Laval",          "2 Rue du Centropolis",       200,  55,  3.00, "LAV"),
            ParkingLot("P6",  "Promenades Saint-Bruno",     "1855 Boul. Pelletier",       380, 140,  2.00, "LON"),
            ParkingLot("P7",  "Place de la Cité",           "2600 Boul. Laurier",         600, 250,  3.75, "QC"),
            ParkingLot("P8",  "Les Galeries de la Capitale","5401 Boul. des Galeries",    700, 320,  2.50, "QC"),
            ParkingLot("P9",  "Les Promenades Gatineau",    "50 Boul. Lorrain",           300, 120,  2.25, "GAT"),
            ParkingLot("P10", "Carrefour de l'Estrie",      "3050 Boul. de Portland",     400, 175,  2.00, "SHE"),
        ]

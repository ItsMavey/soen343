"""
External service adapters — Adapter pattern.

TransitProvider defines the interface. GTFSAdapter fetches real bus stops from
OpenStreetMap via the Overpass API. CityAPIAdapter fetches real metro stations
the same way. TransitFacade aggregates them.

ParkingService returns hardcoded Quebec lots with time-varying simulated
occupancy (no public real-time parking API exists for these cities).
"""
import hashlib
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ---------------------------------------------------------------------------
# City centre coordinates
# ---------------------------------------------------------------------------

CITY_COORDS = {
    "MTL": (45.5017, -73.5673),
    "LAV": (45.6066, -73.7124),
    "LON": (45.5200, -73.5250),   # Longueuil city center, south of St. Lawrence
    "QC":  (46.8322, -71.2453),   # Haute-Ville / Limoilou, away from St. Lawrence
    "GAT": (45.4765, -75.7013),
    "SHE": (45.4042, -71.8929),
}

# ---------------------------------------------------------------------------
# Overpass API helper
# ---------------------------------------------------------------------------

_CACHE_TTL = 600  # 10 minutes


def _overpass_fetch(query: str) -> dict | None:
    """POST an Overpass QL query; return parsed JSON or None on any error."""
    from django.core.cache import cache

    key = "overpass_" + hashlib.md5(query.encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached

    url = "https://overpass-api.de/api/interpreter"
    payload = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            result = json.loads(resp.read().decode())
            cache.set(key, result, _CACHE_TTL)
            return result
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def _dist_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Haversine distance in metres."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# ---------------------------------------------------------------------------
# Transit adapters
# ---------------------------------------------------------------------------

class TransitProvider:
    """Interface all transit adapters must implement."""

    def get_nearby_stops(self, lat: float, lon: float) -> list[dict]:
        raise NotImplementedError

    def get_next_departures(self, stop_id: str) -> list[dict]:
        raise NotImplementedError


class GTFSAdapter(TransitProvider):
    """
    Fetches real bus stops near a coordinate from OpenStreetMap (Overpass API).
    Falls back to hardcoded stubs if the API is unreachable.
    Departures are time-of-day-aware simulations (no free real-time STM API).
    """

    _FALLBACK = [
        {"id": "STM-0001", "name": "Rue Berri / Sainte-Catherine",    "lat": 45.5152, "lon": -73.5617, "distance_m": 95},
        {"id": "STM-0002", "name": "Boul. René-Lévesque / Saint-Denis","lat": 45.5122, "lon": -73.5612, "distance_m": 260},
        {"id": "STM-0003", "name": "Rue Sherbrooke / Saint-Laurent",   "lat": 45.5187, "lon": -73.5697, "distance_m": 430},
    ]

    _ROUTES = [
        ("STM 24", "Sherbrooke / Mont-Royal"),
        ("STM 55", "Saint-Laurent / Sauvé"),
        ("STM 80", "Avenue du Parc / Côte-Sainte-Catherine"),
        ("STM 15", "Sainte-Catherine / Atwater"),
        ("STM 47", "Saint-Denis / Jean-Talon"),
    ]

    def get_nearby_stops(self, lat: float, lon: float) -> list[dict]:
        query = f"""[out:json][timeout:12];
node["highway"="bus_stop"](around:700,{lat},{lon});
out 10;"""
        data = _overpass_fetch(query)
        if not data or not data.get("elements"):
            return self._FALLBACK

        stops = []
        for el in data["elements"][:8]:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("ref") or f"Stop #{el['id'] % 10000}"
            stops.append({
                "id": f"STM-{el['id'] % 100000}",
                "name": name,
                "lat": el["lat"],
                "lon": el["lon"],
                "distance_m": _dist_m(lat, lon, el["lat"], el["lon"]),
            })
        return sorted(stops, key=lambda s: s["distance_m"])

    def get_next_departures(self, stop_id: str) -> list[dict]:
        hour = datetime.now().hour
        is_peak = (7 <= hour <= 9) or (15 <= hour <= 18)
        gap = 3 if is_peak else 8
        return [
            {"route": route, "destination": dest, "minutes": gap + i * (gap - 1)}
            for i, (route, dest) in enumerate(self._ROUTES[:3])
        ]


class CityAPIAdapter(TransitProvider):
    """
    Fetches real metro stations from OpenStreetMap (Overpass API).
    Falls back to hardcoded stubs if the API is unreachable.
    """

    _FALLBACK = [
        {"id": "MTL-0101", "name": "Berri-UQAM",    "lat": 45.5193, "lon": -73.5617, "distance_m": 210},
        {"id": "MTL-0102", "name": "McGill",         "lat": 45.5048, "lon": -73.5782, "distance_m": 510},
        {"id": "MTL-0103", "name": "Place-des-Arts", "lat": 45.5077, "lon": -73.5686, "distance_m": 680},
    ]

    _LINES = [
        ("Ligne Orange", "Montmorency"),
        ("Ligne Verte",  "Honoré-Beaugrand"),
        ("Ligne Orange", "Côte-Vertu"),
        ("Ligne Bleue",  "Saint-Michel"),
    ]

    def get_nearby_stops(self, lat: float, lon: float) -> list[dict]:
        # Pull all STM metro stations (sparse enough to sort by distance client-side)
        query = """[out:json][timeout:12];
node["station"="subway"]["network"="STM"](45.40,45.63,-73.97,-73.45);
out;"""
        data = _overpass_fetch(query)
        if not data or not data.get("elements"):
            return self._FALLBACK

        stops = []
        for el in data["elements"]:
            name = el.get("tags", {}).get("name", "Station")
            stops.append({
                "id": f"MTL-{el['id'] % 100000}",
                "name": name,
                "lat": el["lat"],
                "lon": el["lon"],
                "distance_m": _dist_m(lat, lon, el["lat"], el["lon"]),
            })
        stops.sort(key=lambda s: s["distance_m"])
        return stops[:5]

    def get_next_departures(self, stop_id: str) -> list[dict]:
        hour = datetime.now().hour
        is_peak = (7 <= hour <= 9) or (15 <= hour <= 18)
        gap = 2 if is_peak else 5
        return [
            {"route": line, "destination": dest, "minutes": gap + i * (gap + 1)}
            for i, (line, dest) in enumerate(self._LINES[:3])
        ]


class TransitFacade:
    """Aggregates GTFSAdapter and CityAPIAdapter into one unified interface."""

    def __init__(self):
        self._bus = GTFSAdapter()
        self._metro = CityAPIAdapter()

    def get_nearby_stops(self, lat: float = 45.5017, lon: float = -73.5673) -> list[dict]:
        results = self._bus.get_nearby_stops(lat, lon) + self._metro.get_nearby_stops(lat, lon)
        return sorted(results, key=lambda s: s["distance_m"])

    def get_next_departures(self, stop_id: str) -> list[dict]:
        if stop_id and stop_id.startswith("MTL-"):
            return self._metro.get_next_departures(stop_id)
        return self._bus.get_next_departures(stop_id)


# ---------------------------------------------------------------------------
# Parking service
# ---------------------------------------------------------------------------


class OSMParkingAdapter:
    """
    Fetches real parking facilities from OpenStreetMap (Overpass API).
    Falls back to hardcoded ParkingService lots if the API is unreachable
    or returns no results.
    """

    @staticmethod
    def _parse_elements(elements: list, city: str) -> list["ParkingLot"]:
        lots = []
        for i, el in enumerate(elements[:25]):
            if el["type"] == "node":
                elat, elng = el.get("lat"), el.get("lon")
            elif el["type"] == "way" and "center" in el:
                elat, elng = el["center"]["lat"], el["center"]["lon"]
            else:
                continue
            if elat is None or elng is None:
                continue
            tags = el.get("tags", {})
            name = (tags.get("name") or tags.get("operator")
                    or tags.get("brand") or f"Parking {i + 1}")
            address = " ".join(filter(None, [
                tags.get("addr:housenumber", ""),
                tags.get("addr:street", ""),
            ])).strip()
            try:
                capacity = int(tags.get("capacity") or 0) or 80
            except ValueError:
                capacity = 80
            is_free = tags.get("fee", "yes").lower() in ("no", "false", "0")
            hourly_rate = 0.0 if is_free else float(
                tags.get("charge", "").replace("$", "").split("/")[0].strip() or "2.50"
            )
            lots.append(ParkingLot(f"OSM-{el['id']}", name, address,
                                   capacity, hourly_rate, city, elat, elng))
        return lots

    def _fetch(self, lat: float, lon: float, city: str) -> list["ParkingLot"]:
        query = f"""[out:json][timeout:15];
(
  node["amenity"="parking"](around:1500,{lat},{lon});
  way["amenity"="parking"](around:1500,{lat},{lon});
);
out center 25;"""
        data = _overpass_fetch(query)
        if not data or not data.get("elements"):
            return []
        return self._parse_elements(data["elements"], city)

    def get_lots(self, city: str) -> list["ParkingLot"]:
        coords = CITY_COORDS.get(city)
        if not coords:
            return ParkingService().get_lots(city=city)
        lots = self._fetch(coords[0], coords[1], city)
        return lots if lots else ParkingService().get_lots(city=city)

    def get_lots_near(self, lat: float, lng: float) -> list["ParkingLot"]:
        """Fetch parking lots near arbitrary coordinates (used by map button)."""
        lots = self._fetch(lat, lng, city="")
        return lots

def _simulated_available(lot_id: str, total: int) -> int:
    """
    Time-varying parking availability.
    Occupancy follows a realistic daily profile; each lot has a consistent
    offset seeded from its ID so they don't all move in lockstep.
    """
    hour = datetime.now().hour
    if 8 <= hour <= 10 or 16 <= hour <= 19:
        base_occ = 0.80          # rush hours
    elif 11 <= hour <= 15:
        base_occ = 0.65          # midday
    elif 20 <= hour <= 22:
        base_occ = 0.45          # evening
    else:
        base_occ = 0.20          # overnight

    seed = int(hashlib.md5(f"{lot_id}{hour}".encode()).hexdigest(), 16)
    variance = (seed % 31 - 15) / 100   # ±15 %
    occupancy = max(0.0, min(1.0, base_occ + variance))
    return max(0, int(total * (1 - occupancy)))


class ParkingLot:
    def __init__(self, lot_id: str, name: str, address: str,
                 total_spots: int, hourly_rate: float, city: str = "MTL",
                 lat: float = 0.0, lng: float = 0.0):
        self.lot_id = lot_id
        self.name = name
        self.address = address
        self.total_spots = total_spots
        self.hourly_rate = hourly_rate
        self.city = city
        self.lat = lat
        self.lng = lng
        self.available_spots = _simulated_available(lot_id, total_spots)

    @property
    def occupancy_pct(self) -> int:
        if self.total_spots == 0:
            return 0
        return round((1 - self.available_spots / self.total_spots) * 100)


class ParkingService:
    """Returns real Quebec parking lots with time-varying simulated availability."""

    # (lot_id, name, address, total_spots, hourly_rate, city, lat, lng)
    _LOTS = [
        # Montreal
        ("P1",  "Complexe Desjardins",        "150 Rue Sainte-Catherine O",  320, 3.50, "MTL", 45.5088, -73.5618),
        ("P2",  "Place Ville Marie",           "1 Pl. Ville Marie",           500, 4.00, "MTL", 45.5006, -73.5697),
        ("P3",  "Quartier des Spectacles",     "175 Rue Sainte-Catherine E",   80, 2.50, "MTL", 45.5113, -73.5598),
        ("P4",  "Vieux-Montréal / Commune",    "50 Rue de la Commune E",      180, 5.00, "MTL", 45.5065, -73.5536),
        # Laval
        ("P5",  "Galeries Laval",              "1600 Boul. Le Corbusier",     450, 2.75, "LAV", 45.5634, -73.6920),
        ("P6",  "Centropolis Laval",           "2 Rue du Centropolis",        200, 3.00, "LAV", 45.5580, -73.7200),
        # Longueuil
        ("P7",  "Promenades Saint-Bruno",      "1855 Boul. Pelletier",        380, 2.00, "LON", 45.5370, -73.3610),
        ("P8",  "Station Longueuil P+R",       "200 Rue de la Province",      600, 1.50, "LON", 45.5257, -73.5190),
        # Quebec City
        ("P9",  "Place de la Cité",            "2600 Boul. Laurier",          600, 3.75, "QC",  46.7780, -71.2840),
        ("P10", "Les Galeries de la Capitale", "5401 Boul. des Galeries",     700, 2.50, "QC",  46.8360, -71.2460),
        ("P11", "Vieux-Port de Québec",        "100 Rue Saint-André",         200, 4.50, "QC",  46.8180, -71.2020),
        # Gatineau
        ("P12", "Les Promenades Gatineau",     "50 Boul. Lorrain",            300, 2.25, "GAT", 45.4490, -75.7320),
        ("P13", "Centre-ville Gatineau",       "25 Rue Laurier",              150, 2.00, "GAT", 45.4840, -75.7010),
        # Sherbrooke
        ("P14", "Carrefour de l'Estrie",       "3050 Boul. de Portland",      400, 2.00, "SHE", 45.3810, -71.9260),
        ("P15", "Centre-ville Sherbrooke",     "1 Rue Wellington N",          120, 1.75, "SHE", 45.4020, -71.8900),
    ]

    def get_lots(self, city: str | None = None) -> list[ParkingLot]:
        return [
            ParkingLot(lid, name, addr, total, rate, c, lat, lng)
            for lid, name, addr, total, rate, c, lat, lng in self._LOTS
            if city is None or c == city
        ]

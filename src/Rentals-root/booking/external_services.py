"""
External service adapters — Adapter pattern.

TransitProvider defines the interface.
GTFSAdapter and CityAPIAdapter serve bus/metro stops from STM GTFS static data
(booking/static_data/gtfs_stops.txt) with Overpass fallback for other cities.
STMGTFSRTAdapter fetches real departure times from STM iBUS GTFS-RT v2.
ORSTransitAdapter handles end-to-end public-transport routing via ORS.
TransitFacade aggregates all of the above into one unified interface.

ParkingService returns hardcoded Quebec lots with time-varying simulated
occupancy (no public real-time parking API exists for these cities).
"""
import csv
import hashlib
import json
import math
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

_STATIC_DATA_DIR = os.path.join(os.path.dirname(__file__), "static_data")

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
    req.add_header("User-Agent", "SUMMS/1.0 (university project; danielganchev649@gmail.com)")
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
# STM GTFS static data caches (singletons, loaded once at first use)
# ---------------------------------------------------------------------------

class STMStopsCache:
    """
    Parses STM GTFS stops.txt into in-memory structures for fast proximity
    queries.  Shared singleton — loaded once, reused across requests.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._loaded = False
                    inst._bus_stops = []       # list[{id,name,lat,lon}]
                    inst._metro_stations = []  # location_type=1
                    inst._metro_platforms = {} # station_id -> [platform_stop_id]
                    inst._load()
                    cls._instance = inst
        return cls._instance

    def _load(self):
        path = os.path.join(_STATIC_DATA_DIR, "gtfs_stops.txt")
        try:
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    loc_type = row.get("location_type", "").strip()
                    parent   = row.get("parent_station", "").strip()
                    sid      = row["stop_id"].strip()
                    lat      = float(row["stop_lat"])
                    lon      = float(row["stop_lon"])
                    name     = row["stop_name"].strip()

                    if loc_type == "1":
                        self._metro_stations.append(
                            {"id": sid, "name": name, "lat": lat, "lon": lon})
                    elif parent.startswith("STATION_M"):
                        self._metro_platforms.setdefault(parent, []).append(sid)
                    else:
                        self._bus_stops.append(
                            {"id": sid, "name": name, "lat": lat, "lon": lon})
            self._loaded = True
        except (OSError, KeyError, ValueError):
            pass  # file missing — adapters fall back to Overpass

    def get_nearby_bus(self, lat: float, lon: float,
                       radius_m: int = 700) -> list[dict]:
        results = []
        for s in self._bus_stops:
            d = _dist_m(lat, lon, s["lat"], s["lon"])
            if d <= radius_m:
                results.append({**s, "distance_m": d})
        return sorted(results, key=lambda x: x["distance_m"])[:10]

    def get_nearby_metro(self, lat: float, lon: float,
                         radius_m: int = 2000) -> list[dict]:
        results = [{**s, "distance_m": _dist_m(lat, lon, s["lat"], s["lon"])}
                   for s in self._metro_stations]
        results.sort(key=lambda x: x["distance_m"])
        within = [s for s in results if s["distance_m"] <= radius_m]
        return (within or results[:1])[:5]

    def get_platform_ids(self, station_id: str) -> list[str]:
        """Return numeric platform stop_ids for a metro station."""
        return self._metro_platforms.get(station_id, [])


class STMShapesCache:
    """
    Loads STM GTFS shapes.txt (~578 route polylines) into memory.
    Provides proximity-based geometry lookup: given start/end coordinates,
    finds the shape that passes closest to both and returns the clipped segment.
    Singleton — loaded once at first use (~100 ms startup cost).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._shapes = {}   # shape_id -> [[lat, lon], ...]
                    inst._bboxes = {}   # shape_id -> (min_lat, min_lon, max_lat, max_lon)
                    inst._load()
                    cls._instance = inst
        return cls._instance

    def _load(self):
        path = os.path.join(_STATIC_DATA_DIR, "shapes.txt")
        raw = {}  # shape_id -> [(seq, lat, lon)]
        try:
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    sid = row["shape_id"].strip()
                    raw.setdefault(sid, []).append((
                        int(row["shape_pt_sequence"]),
                        float(row["shape_pt_lat"]),
                        float(row["shape_pt_lon"]),
                    ))
        except (OSError, KeyError, ValueError):
            return
        for sid, pts in raw.items():
            pts.sort()
            coords = [[p[1], p[2]] for p in pts]
            self._shapes[sid] = coords
            lats = [c[0] for c in coords]
            lngs = [c[1] for c in coords]
            self._bboxes[sid] = (min(lats), min(lngs), max(lats), max(lngs))

    def find_geometry(self, slat: float, slng: float,
                      elat: float, elng: float,
                      radius_m: int = 800) -> list | None:
        """
        Find the shape passing nearest to both (slat,slng) and (elat,elng).
        Returns a [[lat,lon],...] list clipped between those two points, or None.
        Uses squared-euclidean approximation for the inner loop (fast) and
        precise haversine only on the best candidate.
        """
        margin = 0.015  # ~1.5 km bbox pre-filter
        q_min_lat = min(slat, elat) - margin
        q_max_lat = max(slat, elat) + margin
        q_min_lng = min(slng, elng) - margin
        q_max_lng = max(slng, elng) + margin

        # Scale factors for fast euclidean approximation (m/degree at this latitude)
        _lat_m = 111_000.0
        _lng_m = 111_000.0 * math.cos(math.radians((slat + elat) / 2))
        r2 = float(radius_m ** 2)

        best_shape = None
        best_score = float("inf")

        for sid, points in self._shapes.items():
            b = self._bboxes[sid]
            if b[0] > q_max_lat or b[2] < q_min_lat or b[1] > q_max_lng or b[3] < q_min_lng:
                continue

            s_d2, s_idx = float("inf"), 0
            e_d2, e_idx = float("inf"), 0
            for i, (plat, plng) in enumerate(points):
                dslat = (plat - slat) * _lat_m; dslng = (plng - slng) * _lng_m
                delat = (plat - elat) * _lat_m; delng = (plng - elng) * _lng_m
                ds2 = dslat * dslat + dslng * dslng
                de2 = delat * delat + delng * delng
                if ds2 < s_d2:
                    s_d2, s_idx = ds2, i
                if de2 < e_d2:
                    e_d2, e_idx = de2, i

            if s_d2 > r2 or e_d2 > r2 or s_idx == e_idx:
                continue

            score = s_d2 + e_d2
            if score < best_score:
                best_score = score
                lo, hi = min(s_idx, e_idx), max(s_idx, e_idx)
                best_shape = points[lo: hi + 1]

        return best_shape


class STMRoutesCache:
    """Parses STM GTFS routes.txt; maps route_id → display name."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._routes = {}
                    inst._load()
                    cls._instance = inst
        return cls._instance

    def _load(self):
        path = os.path.join(_STATIC_DATA_DIR, "gtfs_routes.txt")
        try:
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._routes[row["route_id"].strip()] = {
                        "short": row.get("route_short_name", "").strip(),
                        "long":  row.get("route_long_name",  "").strip(),
                        "type":  row.get("route_type",       "").strip(),
                    }
        except (OSError, KeyError):
            pass

    def display_name(self, route_id: str) -> str:
        r = self._routes.get(str(route_id))
        if not r:
            return str(route_id)
        if r["type"] == "1":      # metro
            return r["long"] or r["short"]
        return r["short"] or r["long"]


# ---------------------------------------------------------------------------
# STM iBUS GTFS-RT v2 adapter
# ---------------------------------------------------------------------------

class STMGTFSRTAdapter:
    """
    Fetches real departure times from STM iBUS GTFS-RT v2 trip-updates feed.
    Requires: pip install gtfs-realtime-bindings

    Raw protobuf is cached for 30 seconds to reduce API load.
    Falls back silently (returns []) if the library is missing, the key is
    absent, or the feed is unreachable.
    """
    _URL      = "https://api.stm.info/pub/od/gtfs-rt/ic/v2/tripUpdates"
    _CACHE_KEY = "stm_gtfs_rt_bytes"
    _CACHE_TTL = 30  # seconds

    def __init__(self, api_key: str):
        self._api_key = api_key

    def _fetch_feed(self) -> bytes | None:
        from django.core.cache import cache
        cached = cache.get(self._CACHE_KEY)
        if cached is not None:
            return cached
        req = urllib.request.Request(self._URL)
        req.add_header("apiKey", self._api_key)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
        except (urllib.error.URLError, OSError):
            return None
        cache.set(self._CACHE_KEY, data, self._CACHE_TTL)
        return data

    def get_next_departures(self, stop_id: str, n: int = 5) -> list[dict]:
        if not self._api_key:
            return []
        try:
            from google.transit import gtfs_realtime_pb2
        except ImportError:
            return []

        raw = self._fetch_feed()
        if not raw:
            return []

        feed = gtfs_realtime_pb2.FeedMessage()
        try:
            feed.ParseFromString(raw)
        except Exception:
            return []

        now = datetime.now().timestamp()
        routes = STMRoutesCache()
        departures = []

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            tu = entity.trip_update
            route_name = routes.display_name(tu.trip.route_id)

            for stu in tu.stop_time_update:
                if str(stu.stop_id) != str(stop_id):
                    continue
                dep_time = None
                if stu.HasField("departure") and stu.departure.time:
                    dep_time = stu.departure.time
                elif stu.HasField("arrival") and stu.arrival.time:
                    dep_time = stu.arrival.time
                if dep_time is None:
                    continue
                minutes = round((dep_time - now) / 60)
                if minutes < 0:
                    continue
                departures.append({
                    "route": route_name,
                    "destination": "",
                    "minutes": minutes,
                })

        departures.sort(key=lambda d: d["minutes"])
        return departures[:n]


# ---------------------------------------------------------------------------
# Transit adapters
# ---------------------------------------------------------------------------

class TransitProvider:
    """Interface all transit adapters must implement."""

    def get_nearby_stops(self, lat: float, lon: float, radius_m: int = 1000) -> list[dict]:
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

    def get_nearby_stops(self, lat: float, lon: float, radius_m: int = 700) -> list[dict]:
        # Try real STM GTFS data first (Montreal/Laval coverage)
        stops = STMStopsCache().get_nearby_bus(lat, lon, radius_m)
        if stops:
            return stops

        # Overpass fallback for non-STM cities
        query = f"""[out:json][timeout:12];
node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
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

    def get_nearby_stops(self, lat: float, lon: float, radius_m: int = 1500) -> list[dict]:
        # Try real STM GTFS metro stations first
        stops = STMStopsCache().get_nearby_metro(lat, lon, radius_m)
        if stops:
            return stops

        # Overpass fallback
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


class ORSTransitAdapter:
    """
    OpenRouteService public-transport routing.
    Free tier: 2000 req/day — register at openrouteservice.org.
    Returns None when unconfigured, unreachable, or no route found.
    Responses are cached for 5 minutes to conserve the free quota.
    """
    _URL = "https://api.openrouteservice.org/v2/directions/public-transport"
    _TIMEOUT = 15
    _CACHE_TTL = 300  # 5 minutes

    def __init__(self, api_key: str):
        self._api_key = api_key

    def get_journey(self, slat: float, slng: float,
                    elat: float, elng: float) -> list[dict] | None:
        if not self._api_key:
            return None

        from django.core.cache import cache
        cache_key = "ors_pt_" + hashlib.md5(
            f"{slat:.4f}{slng:.4f}{elat:.4f}{elng:.4f}".encode()
        ).hexdigest()
        cached = cache.get(cache_key)
        if cached is not None:
            return cached or None  # None stored as sentinel for "no route"

        payload = json.dumps({
            "coordinates": [[slng, slat], [elng, elat]],
        }).encode()
        req = urllib.request.Request(self._URL, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {self._api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, application/geo+json")

        try:
            with urllib.request.urlopen(req, timeout=self._TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None

        routes = data.get("routes", [])
        if not routes:
            cache.set(cache_key, [], self._CACHE_TTL)  # cache miss
            return None

        legs = self._parse_legs(routes[0].get("legs", []))
        cache.set(cache_key, legs or [], self._CACHE_TTL)
        return legs or None

    def _parse_legs(self, legs_raw: list) -> list[dict]:
        legs = []
        for leg in legs_raw:
            leg_type = (leg.get("type") or "").upper()
            from_loc = leg.get("from") or {}
            to_loc   = leg.get("to")   or {}

            try:
                flat = float(from_loc["lat"]); flng = float(from_loc["lon"])
                tlat = float(to_loc["lat"]);   tlng = float(to_loc["lon"])
            except (KeyError, TypeError, ValueError):
                continue

            from_name   = from_loc.get("name") or "Stop"
            to_name     = to_loc.get("name")   or "Stop"
            duration_s  = leg.get("duration") or 0
            duration_min = max(1, round(duration_s / 60))
            dist_km     = round(_dist_m(flat, flng, tlat, tlng) / 1000, 2)

            # Extract geometry (GeoJSON LineString, ORS returns [lng, lat])
            geom_raw = (leg.get("geometry") or {}).get("coordinates", [])
            geometry = [[c[1], c[0]] for c in geom_raw if len(c) >= 2] or None

            if leg_type == "WALK":
                entry = {
                    "mode": "walk",
                    "label": f"Walk to {to_name}",
                    "from": {"lat": flat, "lng": flng, "name": from_name},
                    "to":   {"lat": tlat, "lng": tlng, "name": to_name},
                    "detail": f"~{duration_min} min on foot",
                    "dist_km": dist_km,
                }
                if geometry:
                    entry["geometry"] = geometry
                legs.append(entry)
            elif leg_type == "PT":
                short    = leg.get("route_short_name") or ""
                headsign = leg.get("headsign") or leg.get("trip_headsign") or ""
                agency   = leg.get("agency_name") or ""
                if short and headsign:
                    detail = f"{short} → {headsign} · ~{duration_min} min"
                elif short:
                    detail = f"{agency + ' ' if agency else ''}{short} · ~{duration_min} min"
                else:
                    detail = f"~{duration_min} min"
                entry = {
                    "mode": "transit",
                    "label": f"Take {short or 'transit'}",
                    "from": {"lat": flat, "lng": flng, "name": from_name},
                    "to":   {"lat": tlat, "lng": tlng, "name": to_name},
                    "detail": detail,
                    "dist_km": dist_km,
                }
                if geometry:
                    entry["geometry"] = geometry
                legs.append(entry)
        return legs


class TransitFacade:
    """Aggregates GTFSAdapter and CityAPIAdapter into one unified interface."""

    def __init__(self):
        self._bus = GTFSAdapter()
        self._metro = CityAPIAdapter()

    def get_nearby_stops(self, lat: float = 45.5017, lon: float = -73.5673, radius_m: int = 1000) -> list[dict]:
        results = self._bus.get_nearby_stops(lat, lon, radius_m) + self._metro.get_nearby_stops(lat, lon, radius_m)
        return sorted(results, key=lambda s: s["distance_m"])

    def get_next_departures(self, stop_id: str) -> list[dict]:
        from django.conf import settings
        api_key = getattr(settings, "STM_API_KEY", "")

        if api_key:
            rt = STMGTFSRTAdapter(api_key)
            if stop_id and stop_id.startswith("STATION_M"):
                # Metro station: query all platform stop_ids
                platform_ids = STMStopsCache().get_platform_ids(stop_id)
                departures = []
                for pid in platform_ids:
                    departures.extend(rt.get_next_departures(pid, n=3))
                if departures:
                    departures.sort(key=lambda d: d["minutes"])
                    return departures[:5]
            else:
                departures = rt.get_next_departures(stop_id, n=5)
                if departures:
                    return departures

        # Simulated fallback (covers non-MTL cities and test runs)
        if stop_id and stop_id.startswith("STATION_M"):
            return self._metro.get_next_departures(stop_id)
        if stop_id and stop_id.startswith("MTL-"):
            return self._metro.get_next_departures(stop_id)
        return self._bus.get_next_departures(stop_id)

    def get_journey(self, slat: float, slng: float,
                    elat: float, elng: float) -> list[dict] | None:
        """
        Return real transit journey legs via ORS, or None if unavailable/unconfigured.
        Falls back gracefully — callers should handle None by using nearest-stop logic.
        """
        from django.conf import settings
        api_key = getattr(settings, "OPENROUTESERVICE_API_KEY", "")
        if not api_key:
            return None
        return ORSTransitAdapter(api_key).get_journey(slat, slng, elat, elng)


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

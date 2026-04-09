"""
Multimodal itinerary planning strategies — Strategy pattern.

ItineraryStrategy defines the interface.  Concrete strategies build
trip legs from origin to destination using different modal combinations.

Used by trip_views.trip_plan to generate multiple route options.
"""
import abc
import math

from django.urls import reverse

from .external_services import ParkingService, TransitFacade
from .models import Vehicle


def _vehicle_coords(v):
    from .views.map_views import _vehicle_coords as _vc
    return _vc(v)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def nearest_vehicle(lat: float, lng: float,
                    exclude_id: int | None = None,
                    max_km: float = 2.0,
                    kind: str | None = None):
    """
    Return (Vehicle, vlat, vlng) of the closest available vehicle within
    max_km, or (None, None, None) if none qualifies.
    """
    qs = Vehicle.objects.filter(vehicle_status=Vehicle.STATUS_AVAILABLE)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    if kind:
        qs = qs.filter(vehicle_kind=kind)
    best, best_d, best_lat, best_lng = None, float("inf"), None, None
    for v in qs:
        vlat, vlng = _vehicle_coords(v)
        d = _haversine_km(lat, lng, vlat, vlng)
        if d < best_d:
            best, best_d, best_lat, best_lng = v, d, vlat, vlng
    if best_d > max_km:
        return None, None, None
    return best, best_lat, best_lng


def nearest_parking(lat: float, lng: float):
    """Return the closest ParkingLot or None."""
    best, best_d = None, float("inf")
    for lot in ParkingService().get_lots():
        if lot.lat == 0.0:
            continue
        d = _haversine_km(lat, lng, lot.lat, lot.lng)
        if d < best_d:
            best, best_d = lot, d
    return best


# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------

class ItineraryStrategy(abc.ABC):
    """Abstract base for multimodal itinerary planners."""

    @abc.abstractmethod
    def plan(self, slat: float, slng: float,
             elat: float, elng: float) -> dict | None:
        """
        Build a trip plan from (slat, slng) to (elat, elng).

        Returns a dict::

            {
                "type":  str,         # e.g. "transit_vehicle"
                "label": str,         # human-readable tab label
                "legs":  list[dict],  # ordered leg descriptors
            }

        Returns None if the strategy is not feasible for the given inputs.
        """
        raise NotImplementedError

    # -- shared leg builder ------------------------------------------------
    @staticmethod
    def _leg(mode: str, label: str,
             from_lat: float, from_lng: float, from_name: str,
             to_lat: float,   to_lng: float,   to_name: str,
             detail: str,
             vehicle_url: str | None = None,
             vehicle_detail_url: str | None = None) -> dict:
        leg = {
            "mode":   mode,
            "label":  label,
            "from":   {"lat": from_lat, "lng": from_lng, "name": from_name},
            "to":     {"lat": to_lat,   "lng": to_lng,   "name": to_name},
            "detail": detail,
            "dist_km": round(_haversine_km(from_lat, from_lng, to_lat, to_lng), 2),
        }
        if vehicle_url:
            leg["vehicle_url"] = vehicle_url
        if vehicle_detail_url:
            leg["vehicle_detail_url"] = vehicle_detail_url
        return leg


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class VehicleOnlyStrategy(ItineraryStrategy):
    """
    Walk to the nearest available vehicle → drive straight to the destination.
    Nearby parking is shown as map overlays by the trip_plan view.
    """

    def plan(self, slat, slng, elat, elng):
        vehicle, vlat, vlng = nearest_vehicle(slat, slng)
        if not vehicle:
            return None

        ride_mode = "drive" if vehicle.vehicle_kind == Vehicle.KIND_CAR else "ride"
        ride_verb = "Drive" if vehicle.vehicle_kind == Vehicle.KIND_CAR else "Ride"

        return {
            "type": "vehicle_only",
            "label": "Vehicle Only",
            "legs": [
                self._leg("walk", "Walk to vehicle",
                          slat, slng, "Start",
                          vlat, vlng, vehicle.display_name(),
                          f"{vehicle.display_name()} · ${vehicle.daily_rate}/day"),
                self._leg(ride_mode, f"{ride_verb} to destination",
                          vlat, vlng, vehicle.display_name(),
                          elat, elng, "Destination",
                          f"${vehicle.daily_rate}/day · parking shown on map",
                          vehicle_url=reverse("reserve_vehicle", args=[vehicle.id]),
                          vehicle_detail_url=reverse("vehicle_detail", args=[vehicle.id])),
            ],
        }


class TransitFirstStrategy(ItineraryStrategy):
    """
    Walk to the nearest transit stop → take transit toward the destination →
    walk from the end stop to the nearest available vehicle →
    drive to parking near the destination → walk the last stretch.

    Returns None if no transit stops are found near either endpoint.
    """

    def plan(self, slat, slng, elat, elng):
        from concurrent.futures import ThreadPoolExecutor
        facade = TransitFacade()
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_start = ex.submit(facade.get_nearby_stops, slat, slng, 800)
            f_end   = ex.submit(facade.get_nearby_stops, elat, elng, 800)
            start_stops = f_start.result()
            end_stops   = f_end.result()

        if not start_stops or not end_stops:
            return None  # no transit coverage — caller falls back

        start_stop = start_stops[0]
        end_stop   = end_stops[0]

        # Find the nearest available vehicle to the end transit stop
        vehicle, vlat, vlng = nearest_vehicle(end_stop["lat"], end_stop["lon"])
        if not vehicle:
            return None

        parking   = nearest_parking(elat, elng)
        park_lat  = parking.lat  if parking else elat
        park_lng  = parking.lng  if parking else elng
        park_name = parking.name if parking else "Destination"

        # Rough transit time estimate: assume 20 km/h average speed + 2 min boarding
        transit_km  = _haversine_km(start_stop["lat"], start_stop["lon"],
                                    end_stop["lat"],   end_stop["lon"])
        transit_min = max(5, round(transit_km / 20 * 60) + 2)

        legs = [
            self._leg("walk", "Walk to transit stop",
                      slat, slng, "Start",
                      start_stop["lat"], start_stop["lon"], start_stop["name"],
                      f"{start_stop['distance_m']}m on foot"),
            self._leg("transit", "Take transit",
                      start_stop["lat"], start_stop["lon"], start_stop["name"],
                      end_stop["lat"],   end_stop["lon"],   end_stop["name"],
                      f"~{transit_min} min · {end_stop['name']}"),
            self._leg("walk", "Walk to vehicle",
                      end_stop["lat"], end_stop["lon"], end_stop["name"],
                      vlat, vlng, vehicle.display_name(),
                      f"{vehicle.display_name()} · ${vehicle.daily_rate}/day"),
            self._leg("drive", f"Drive {vehicle.display_name()}",
                      vlat, vlng, vehicle.display_name(),
                      park_lat, park_lng, park_name,
                      (f"{parking.name} · {parking.available_spots} spots free"
                       if parking else "Drive to destination"),
                      vehicle_url=reverse("vehicle_detail", args=[vehicle.id])),
        ]
        if parking:
            legs.append(self._leg("walk", "Walk to destination",
                                  parking.lat, parking.lng, parking.name,
                                  elat, elng, "Destination",
                                  f"~{round(_haversine_km(parking.lat, parking.lng, elat, elng) * 1000)}m on foot"))

        return {"type": "transit_vehicle", "label": "Transit + Vehicle", "legs": legs}


class TransitOnlyStrategy(ItineraryStrategy):
    """
    Walk to the nearest transit stop → take transit → walk to destination.
    Uses ORS public-transport routing when configured; falls back to a
    nearest-stop approximation when the key is absent or unavailable.
    """

    def plan(self, slat, slng, elat, elng):
        facade = TransitFacade()

        # ── Real routing via ORS ─────────────────────────────────────────────
        legs = facade.get_journey(slat, slng, elat, elng)
        if legs:
            return {"type": "transit_only", "label": "Transit", "legs": legs}

        # ── Nearest-stop fallback ────────────────────────────────────────────
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_start = ex.submit(facade.get_nearby_stops, slat, slng, 800)
            f_end   = ex.submit(facade.get_nearby_stops, elat, elng, 800)
            start_stops = f_start.result()
            end_stops   = f_end.result()

        if not start_stops or not end_stops:
            return None

        start_stop = start_stops[0]
        end_stop   = end_stops[0]
        transit_km  = _haversine_km(start_stop["lat"], start_stop["lon"],
                                     end_stop["lat"],   end_stop["lon"])
        transit_min = max(5, round(transit_km / 20 * 60) + 2)

        transit_leg = self._leg(
            "transit", f"Transit to {end_stop['name']}",
            start_stop["lat"], start_stop["lon"], start_stop["name"],
            end_stop["lat"],   end_stop["lon"],   end_stop["name"],
            f"~{transit_min} min",
        )

        # Attach real route geometry from GTFS shapes
        from .external_services import STMShapesCache
        geom = STMShapesCache().find_geometry(
            start_stop["lat"], start_stop["lon"],
            end_stop["lat"],   end_stop["lon"],
        )
        if geom:
            transit_leg["geometry"] = geom

        return {
            "type": "transit_only",
            "label": "Transit",
            "legs": [
                self._leg("walk", "Walk to stop",
                          slat, slng, "Start",
                          start_stop["lat"], start_stop["lon"], start_stop["name"],
                          f"{start_stop['distance_m']} m on foot"),
                transit_leg,
                self._leg("walk", "Walk to destination",
                          end_stop["lat"], end_stop["lon"], end_stop["name"],
                          elat, elng, "Destination",
                          f"~{round(_haversine_km(end_stop['lat'], end_stop['lon'], elat, elng) * 1000)} m on foot"),
            ],
        }

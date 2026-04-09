from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from ..external_services import ParkingService
from ..models import Vehicle
from ..trip_strategies import (
    TransitOnlyStrategy,
    TransitFirstStrategy,
    VehicleOnlyStrategy,
    _haversine_km,
    nearest_vehicle,
)
from .map_views import _vehicle_coords

_STRATEGY_ORDER = ["transit_only", "transit_vehicle", "vehicle_only"]


@login_required
def trip_view(request):
    return render(request, "booking/trip.html")


@login_required
def trip_plan(request):
    try:
        slat = float(request.GET["slat"])
        slng = float(request.GET["slng"])
        elat = float(request.GET["elat"])
        elng = float(request.GET["elng"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Provide slat, slng, elat, elng."}, status=400)

    # Run all strategies in parallel; collect feasible options in priority order
    strategies = [TransitOnlyStrategy(), TransitFirstStrategy(), VehicleOnlyStrategy()]
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(s.plan, slat, slng, elat, elng): s for s in strategies}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r:
                    results[r["type"]] = r
            except Exception:
                pass
    options = [results[k] for k in _STRATEGY_ORDER if k in results]

    if not options:
        return JsonResponse(
            {"error": "No route found. Make sure vehicles are seeded."},
            status=404,
        )

    # Nearby available vehicles (top 5 closest to destination) for map overlay
    nearby_vehicles = []
    vehicle_dists = []
    for v in Vehicle.objects.filter(vehicle_status=Vehicle.STATUS_AVAILABLE):
        vlat, vlng = _vehicle_coords(v)
        d = _haversine_km(elat, elng, vlat, vlng)
        vehicle_dists.append((d, v, vlat, vlng))
    vehicle_dists.sort(key=lambda x: x[0])
    for d, v, vlat, vlng in vehicle_dists[:5]:
        nearby_vehicles.append({
            "id": v.id,
            "name": v.display_name(),
            "lat": vlat,
            "lng": vlng,
            "rate": float(v.daily_rate),
            "url": reverse("vehicle_detail", args=[v.id]),
            "kind": v.vehicle_kind,
        })

    # Nearby parking near destination (within 2 km)
    nearby_parking = []
    for lot in ParkingService().get_lots():
        if lot.lat == 0.0:
            continue
        d = _haversine_km(elat, elng, lot.lat, lot.lng)
        if d <= 2.0:
            nearby_parking.append({
                "name": lot.name,
                "lat": lot.lat,
                "lng": lot.lng,
                "available": lot.available_spots,
                "rate": lot.hourly_rate,
            })
    nearby_parking.sort(key=lambda p: _haversine_km(elat, elng, p["lat"], p["lng"]))

    return JsonResponse({
        "options": options,
        "nearby_vehicles": nearby_vehicles,
        "nearby_parking": nearby_parking[:5],
    })

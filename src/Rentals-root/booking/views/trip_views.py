import math

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from ..external_services import CITY_COORDS, ParkingService
from ..models import Vehicle
from ..views.map_views import _vehicle_coords


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


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

    # 1. Find closest available vehicle to start
    vehicles = Vehicle.objects.filter(vehicle_status=Vehicle.STATUS_AVAILABLE)
    best_vehicle = None
    best_vehicle_dist = float("inf")
    best_vlat = best_vlng = None

    for v in vehicles:
        vlat, vlng = _vehicle_coords(v)
        d = _haversine_km(slat, slng, vlat, vlng)
        if d < best_vehicle_dist:
            best_vehicle_dist = d
            best_vehicle = v
            best_vlat, best_vlng = vlat, vlng

    if not best_vehicle:
        return JsonResponse({"error": "No available vehicles found."}, status=404)

    # 2. Find closest parking lot to end
    service = ParkingService()
    best_lot = None
    best_lot_dist = float("inf")

    for lot in service.get_lots():
        if lot.lat == 0.0:
            continue
        d = _haversine_km(elat, elng, lot.lat, lot.lng)
        if d < best_lot_dist:
            best_lot_dist = d
            best_lot = lot

    # Build itinerary legs
    legs = [
        {
            "mode": "walk",
            "label": "Walk to vehicle",
            "from": {"lat": slat, "lng": slng, "name": "Your start"},
            "to":   {"lat": best_vlat, "lng": best_vlng, "name": best_vehicle.display_name()},
            "detail": f"{best_vehicle.display_name()} · ${best_vehicle.daily_rate}/day",
            "dist_km": round(best_vehicle_dist, 2),
        },
        {
            "mode": "drive",
            "label": f"Drive {best_vehicle.display_name()}",
            "from": {"lat": best_vlat, "lng": best_vlng, "name": best_vehicle.display_name()},
            "to":   {"lat": best_lot.lat, "lng": best_lot.lng, "name": best_lot.name} if best_lot else {"lat": elat, "lng": elng, "name": "Destination"},
            "detail": best_lot.name + f" · {best_lot.available_spots} spots free" if best_lot else "Drive to destination",
            "dist_km": round(_haversine_km(best_vlat, best_vlng,
                                           best_lot.lat if best_lot else elat,
                                           best_lot.lng if best_lot else elng), 2),
            "vehicle_url": reverse("vehicle_detail", args=[best_vehicle.id]),
        },
    ]

    if best_lot:
        legs.append({
            "mode": "walk",
            "label": "Walk to destination",
            "from": {"lat": best_lot.lat, "lng": best_lot.lng, "name": best_lot.name},
            "to":   {"lat": elat, "lng": elng, "name": "Your destination"},
            "detail": f"~{round(best_lot_dist * 1000)}m on foot",
            "dist_km": round(best_lot_dist, 2),
        })

    return JsonResponse({"legs": legs})

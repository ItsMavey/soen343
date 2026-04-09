from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from ..external_services import OSMParkingAdapter, ParkingService, TransitFacade, CITY_COORDS 

_CITY_CHOICES = [
    ("MTL", "Montreal"), ("LAV", "Laval"), ("LON", "Longueuil"),
    ("QC", "Quebec City"), ("GAT", "Gatineau"), ("SHE", "Sherbrooke"),
]


@login_required
def parking(request):
    city = request.GET.get("city") or getattr(request.user, "preferred_city", "") or "MTL"
    lots = OSMParkingAdapter().get_lots(city=city)
    return render(request, "booking/parking.html", {
        "lots": lots, "city": city, "city_choices": _CITY_CHOICES,
    })


@login_required
def parking_nearby(request):
    try:
        lat = float(request.GET["lat"])
        lng = float(request.GET["lng"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Provide lat and lng."}, status=400)
    lots = OSMParkingAdapter().get_lots_near(lat, lng) 
    return JsonResponse({"lots": [
        {"idx": i, "name": l.name, "address": l.address,
         "available": l.available_spots, "total": l.total_spots,
         "rate": l.hourly_rate, "occupancy": l.occupancy_pct,
         "lat": l.lat, "lng": l.lng}
        for i, l in enumerate(lots)
    ]})


@login_required
def transit(request):
    city = request.GET.get("city") or getattr(request.user, "preferred_city", "") or "MTL"
    lat, lon = CITY_COORDS.get(city, CITY_COORDS["MTL"])
    facade = TransitFacade()
    stops = facade.get_nearby_stops(lat=lat, lon=lon)
    stop_id = request.GET.get("stop_id")
    departures = facade.get_next_departures(stop_id) if stop_id else []

    if request.GET.get("format") == "json":
        return JsonResponse({"departures": departures})

    return render(request, "booking/transit.html", {
        "stops": stops, "departures": departures, "stop_id": stop_id,
        "city": city, "city_choices": _CITY_CHOICES,
        "center_lat": lat, "center_lng": lon,
    })


@login_required
def transit_nearby(request):
    try:
        lat = float(request.GET["lat"])
        lng = float(request.GET["lng"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Provide lat and lng."}, status=400)
    stops = TransitFacade().get_nearby_stops(lat=lat, lon=lng, radius_m=1500)
    return JsonResponse({"stops": [
        {"id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"],
         "distance_m": s["distance_m"]}
        for s in stops
    ]})

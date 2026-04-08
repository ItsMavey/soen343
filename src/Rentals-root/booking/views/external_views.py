from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..services import ParkingService, TransitFacade, CITY_COORDS

_CITY_CHOICES = [
    ("MTL", "Montreal"), ("LAV", "Laval"), ("LON", "Longueuil"),
    ("QC", "Quebec City"), ("GAT", "Gatineau"), ("SHE", "Sherbrooke"),
]


@login_required
def parking(request):
    city = request.GET.get("city") or getattr(request.user, "preferred_city", "") or "MTL"
    lots = ParkingService().get_lots(city=city)
    return render(request, "booking/parking.html", {
        "lots": lots, "city": city, "city_choices": _CITY_CHOICES,
    })


@login_required
def transit(request):
    city = getattr(request.user, "preferred_city", "") or "MTL"
    lat, lon = CITY_COORDS.get(city, CITY_COORDS["MTL"])
    facade = TransitFacade()
    stops = facade.get_nearby_stops(lat=lat, lon=lon)
    stop_id = request.GET.get("stop_id")
    departures = facade.get_next_departures(stop_id) if stop_id else []
    return render(request, "booking/transit.html", {
        "stops": stops, "departures": departures, "stop_id": stop_id, "city": city,
    })

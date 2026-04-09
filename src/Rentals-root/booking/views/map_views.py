import hashlib
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from ..external_services import CITY_COORDS, ParkingService, TransitFacade
from ..models import Vehicle


def _vehicle_coords(vehicle):
    base_lat, base_lng = CITY_COORDS.get(vehicle.city, (45.5017, -73.5673))
    h = int(hashlib.md5(str(vehicle.id).encode()).hexdigest(), 16)
    lat_offset = ((h >> 16) % 1000 / 1000 - 0.5) * 0.014
    lng_offset = ((h & 0xFFFF) % 1000 / 1000 - 0.5) * 0.018
    return round(base_lat + lat_offset, 6), round(base_lng + lng_offset, 6)


@login_required
def map_view(request):
    city_choices = Vehicle.CITY_CHOICES
    initial_city = getattr(request.user, "preferred_city", "") or "MTL"
    return render(request, "booking/map.html", {
        "city_choices": city_choices,
        "initial_city": initial_city,
    })


@login_required
def map_data(request):
    city = request.GET.get("city") or None
    kinds = request.GET.get("kinds", "").split(",") if request.GET.get("kinds") else []
    available_only = request.GET.get("available_only") == "1"
    show_parking = request.GET.get("parking") != "0"
    show_transit = request.GET.get("transit") != "0"

    make      = request.GET.get("make", "").strip()
    model     = request.GET.get("model", "").strip()
    fuel_type = request.GET.get("fuel_type", "").strip()
    min_rate  = request.GET.get("min_rate", "").strip()
    max_rate  = request.GET.get("max_rate", "").strip()

    # Vehicles
    qs = Vehicle.objects.all()
    if city:
        qs = qs.filter(city=city)
    if kinds:
        qs = qs.filter(vehicle_kind__in=kinds)
    if available_only:
        qs = qs.filter(vehicle_status=Vehicle.STATUS_AVAILABLE)
    if make:
        qs = qs.filter(make__icontains=make)
    if model:
        qs = qs.filter(model__icontains=model)
    if fuel_type:
        qs = qs.filter(car__fuel_type=fuel_type)
    if min_rate:
        try: qs = qs.filter(daily_rate__gte=float(min_rate))
        except ValueError: pass
    if max_rate:
        try: qs = qs.filter(daily_rate__lte=float(max_rate))
        except ValueError: pass

    vehicles = []
    for v in qs:
        lat, lng = _vehicle_coords(v)
        vehicles.append({
            "id": v.id,
            "name": v.display_name(),
            "kind": v.vehicle_kind,
            "city": v.city,
            "status": v.vehicle_status,
            "rate": float(v.daily_rate),
            "lat": lat,
            "lng": lng,
            "url": reverse("vehicle_detail", args=[v.id]),
        })

    # Parking
    parking = []
    if show_parking:
        service = ParkingService()
        for lot in service.get_lots(city=city):
            if lot.lat == 0.0:
                continue
            parking.append({
                "id": lot.lot_id,
                "name": lot.name,
                "address": lot.address,
                "available": lot.available_spots,
                "total": lot.total_spots,
                "rate": lot.hourly_rate,
                "occupancy": lot.occupancy_pct,
                "lat": lot.lat,
                "lng": lot.lng,
            })

    # Transit stops
    transit = []
    if show_transit and city:
        coords = CITY_COORDS.get(city)
        if coords:
            try:
                facade = TransitFacade()
                stops = facade.get_nearby_stops(lat=coords[0], lon=coords[1], radius_m=3000)
                for s in stops[:30]:
                    if s.get("lat") and s.get("lon"):
                        transit.append({
                            "id": s.get("id", ""),
                            "name": s.get("name", "Stop"),
                            "lat": float(s["lat"]),
                            "lng": float(s["lon"]),
                        })
            except Exception:
                pass

    return JsonResponse({"vehicles": vehicles, "parking": parking, "transit": transit})

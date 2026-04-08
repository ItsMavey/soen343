import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as _tz

from ..forms import VehicleSearchForm, ReservationForm
from ..models import Vehicle, Reservation
from ..pricing import SURGE_THRESHOLD
from ..services import ReservationService
from ..sustainability import loyalty_discount, reliability_score


def _attach_upcoming_reservations(vehicles):
    """Attach .upcoming_reservations list to each vehicle in-place."""
    today = _tz.localdate()
    upcoming = Reservation.objects.filter(
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
        end_date__gte=today,
    ).values("vehicle_id", "start_date", "end_date").order_by("start_date")

    res_map = {}
    for r in upcoming:
        res_map.setdefault(r["vehicle_id"], []).append(r)

    for v in vehicles:
        v.upcoming_reservations = res_map.get(v.id, [])


@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by("make", "model")
    form = VehicleSearchForm(request.GET or None)

    if form.is_valid():
        query = form.cleaned_data.get("query")
        vehicle_kind = form.cleaned_data.get("vehicle_kind")
        city = form.cleaned_data.get("city")
        fuel_type = form.cleaned_data.get("fuel_type")
        min_rate = form.cleaned_data.get("min_rate")
        max_rate = form.cleaned_data.get("max_rate")

        if query:
            vehicles = vehicles.filter(Q(make__icontains=query) | Q(model__icontains=query))
        if vehicle_kind:
            vehicles = vehicles.filter(vehicle_kind=vehicle_kind)
        if city:
            vehicles = vehicles.filter(city=city)
        if fuel_type:
            vehicles = vehicles.filter(car__fuel_type__iexact=fuel_type)
        if min_rate is not None:
            vehicles = vehicles.filter(daily_rate__gte=min_rate)
        if max_rate is not None:
            vehicles = vehicles.filter(daily_rate__lte=max_rate)

    vehicles = list(vehicles)
    _attach_upcoming_reservations(vehicles)
    return render(request, "booking/vehicle_list.html", {"vehicles": vehicles, "form": form})


@login_required
def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    subtype = vehicle.get_subtype()
    today = _tz.localdate()
    upcoming_reservations = list(
        Reservation.objects.filter(
            vehicle=vehicle,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            end_date__gte=today,
        ).values("start_date", "end_date").order_by("start_date")
    )
    active_count = len(upcoming_reservations)
    is_surge = active_count >= SURGE_THRESHOLD
    disabled_ranges = [{"from": str(r["start_date"]), "to": str(r["end_date"])} for r in upcoming_reservations]
    return render(request, "booking/vehicle_detail.html", {
        "vehicle": vehicle,
        "subtype": subtype,
        "is_surge": is_surge,
        "active_count": active_count,
        "upcoming_reservations": upcoming_reservations,
        "disabled_ranges_json": json.dumps(disabled_ranges),
    })


@login_required
def reserve_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    form = ReservationForm(request.POST or None)

    today = _tz.localdate()
    booked = list(
        Reservation.objects.filter(
            vehicle=vehicle,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            end_date__gte=today,
        ).values("start_date", "end_date").order_by("start_date")
    )
    active_count = len(booked)
    is_surge = active_count >= SURGE_THRESHOLD
    disabled_ranges = [{"from": str(r["start_date"]), "to": str(r["end_date"])} for r in booked]

    if request.method == "POST" and form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        overlapping = Reservation.objects.filter(
            vehicle=vehicle,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

        if vehicle.vehicle_status == Vehicle.STATUS_MAINTENANCE:
            form.add_error(None, "This vehicle is currently under maintenance and cannot be reserved.")
        elif overlapping:
            form.add_error(None, "This vehicle is already reserved for the selected dates.")
        else:
            reservation = ReservationService.create(request.user, vehicle, start_date, end_date, active_count)
            messages.success(request, "Vehicle reserved. Complete payment to confirm.")
            return redirect("reservation_payment", reservation_id=reservation.id)

    score = reliability_score(request.user)
    discount_rate, discount_label = loyalty_discount(score)

    return render(request, "booking/reserve_vehicle.html", {
        "vehicle": vehicle,
        "form": form,
        "is_surge": is_surge,
        "active_count": active_count,
        "disabled_ranges_json": json.dumps(disabled_ranges),
        "discount_rate": float(discount_rate),
        "discount_label": discount_label,
    })

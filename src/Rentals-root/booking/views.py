import datetime
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .factories import ProviderFactoryA, ProviderFactoryB
from .forms import VehicleSearchForm, PaymentForm, ReservationForm, ProviderVehicleForm
from .models import Vehicle, Car, Bike, Scooter, Reservation, Notification
from .pricing import select_strategy, SURGE_THRESHOLD
from .sustainability import reliability_score, apply_discount, total_co2_saved, loyalty_discount
from .services import ParkingService, TransitFacade
from .states import InvalidTransitionError


def _attach_upcoming_reservations(vehicles):
    """Attach .upcoming_reservations list to each vehicle in-place."""
    today = datetime.date.today()
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
    today = datetime.date.today()
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

    today = datetime.date.today()
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
            strategy = select_strategy(start_date, active_count)
            total_amount = strategy.calculate(vehicle.daily_rate, start_date, end_date)
            score = reliability_score(request.user)
            total_amount, discount_amt, _ = apply_discount(total_amount, score)
            reservation = Reservation.objects.create(
                user=request.user,
                vehicle=vehicle,
                start_date=start_date,
                end_date=end_date,
                total_amount=total_amount,
                pricing_strategy=strategy.name,
            )
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


@login_required
def reservation_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("vehicle_list")
    form = PaymentForm(request.POST or None)

    if reservation.status != Reservation.STATUS_PENDING:
        messages.info(request, "This reservation is no longer pending payment.")
        return redirect("reservation_detail", reservation_id=reservation.id)

    if request.method == "POST" and form.is_valid():
        reservation.status = Reservation.STATUS_CONFIRMED
        reservation.paid_at = timezone.now()
        reservation.save(update_fields=["status", "paid_at"])
        messages.success(request, "Payment completed. Reservation confirmed.")
        return redirect("reservation_detail", reservation_id=reservation.id)

    return render(request, "booking/payment.html", {"reservation": reservation, "form": form})


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("vehicle_list")
    return render(request, "booking/reservation_detail.html", {"reservation": reservation})


@login_required
def return_vehicle(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("vehicle_list")
    if request.method == "POST":
        if reservation.status == Reservation.STATUS_CONFIRMED:
            vehicle = reservation.vehicle
            vehicle.total_trips += 1
            vehicle.save(update_fields=["total_trips"])
            reservation.status = Reservation.STATUS_RETURNED
            reservation.returned_at = timezone.now()
            reservation.save(update_fields=["status", "returned_at"])
            vehicle._notify_observers("RETURNED")
            messages.success(request, "Vehicle return completed.")
        else:
            messages.error(request, "Only confirmed reservations can be returned.")
    return redirect("reservation_detail", reservation_id=reservation.id)


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(user=request.user).select_related("vehicle")
    return render(request, "booking/my_reservations.html", {"reservations": reservations})


@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("vehicle_list")
    if request.method == "POST":
        if reservation.status == Reservation.STATUS_PENDING:
            reservation.status = Reservation.STATUS_CANCELLED
            reservation.save(update_fields=["status"])
            reservation.vehicle.vehicle_status = reservation.vehicle.STATUS_AVAILABLE
            reservation.vehicle.save(update_fields=["vehicle_status"])
            messages.success(request, "Reservation cancelled.")
            return redirect("my_reservations")
        else:
            messages.error(request, "Only pending reservations can be cancelled.")
    return redirect("reservation_detail", reservation_id=reservation.id)


# ---------------------------------------------------------------------------
# Provider Fleet Management
# ---------------------------------------------------------------------------

def _require_provider(request):
    """Returns None if ok, or a redirect response if not a provider."""
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_provider:
        messages.error(request, "Access restricted to Mobility Providers.")
        return redirect("role_dashboard")
    return None


@login_required
def provider_fleet(request):
    guard = _require_provider(request)
    if guard:
        return guard
    vehicles = Vehicle.objects.filter(owner=request.user).order_by("make", "model")
    return render(request, "booking/provider_fleet.html", {"vehicles": vehicles})


@login_required
def provider_add_vehicle(request):
    guard = _require_provider(request)
    if guard:
        return guard

    form = ProviderVehicleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        kind = form.cleaned_data["vehicle_kind"]
        factory = ProviderFactoryA() if kind == Vehicle.KIND_CAR else ProviderFactoryB()
        common = {
            "make": form.cleaned_data["make"],
            "model": form.cleaned_data["model"],
            "year": form.cleaned_data["year"],
            "daily_rate": form.cleaned_data["daily_rate"],
            "owner": request.user,
            "provider": request.user.username,
        }
        city = form.cleaned_data.get("city", Vehicle.CITY_MTL)
        if kind == Vehicle.KIND_CAR:
            factory.create_car(
                fuel_type=form.cleaned_data.get("fuel_type", "GASOLINE"),
                body_style=form.cleaned_data.get("body_style", ""),
                **common,
            )
        elif kind == Vehicle.KIND_BIKE:
            factory.create_bike(
                bike_type=form.cleaned_data.get("bike_type", "STANDARD"),
                has_motor=form.cleaned_data.get("has_motor", False),
                **common,
            )
        else:
            factory.create_scooter(
                engine_cc=form.cleaned_data.get("engine_cc", 50),
                is_electric=form.cleaned_data.get("is_electric", False),
                **common,
            )
        # Set city on the newly created vehicle
        from booking.models import Vehicle as V
        V.objects.filter(make=common["make"], model=common["model"], year=common["year"], owner=request.user).update(city=city)
        messages.success(request, "Vehicle added to your fleet.")
        return redirect("provider_fleet")

    return render(request, "booking/provider_vehicle_form.html", {"form": form, "action": "Add"})


@login_required
def provider_edit_vehicle(request, vehicle_id):
    guard = _require_provider(request)
    if guard:
        return guard

    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    subtype = vehicle.get_subtype()

    initial = {
        "vehicle_kind": vehicle.vehicle_kind,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "daily_rate": vehicle.daily_rate,
        "city": vehicle.city,
    }
    if vehicle.vehicle_kind == Vehicle.KIND_CAR:
        initial.update({"fuel_type": subtype.fuel_type, "body_style": subtype.body_style})
    elif vehicle.vehicle_kind == Vehicle.KIND_BIKE:
        initial.update({"bike_type": subtype.bike_type, "has_motor": subtype.has_motor})
    elif vehicle.vehicle_kind == Vehicle.KIND_SCOOTER:
        initial.update({"engine_cc": subtype.engine_cc, "is_electric": subtype.is_electric})

    form = ProviderVehicleForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        vehicle.make = form.cleaned_data["make"]
        vehicle.model = form.cleaned_data["model"]
        vehicle.year = form.cleaned_data["year"]
        vehicle.daily_rate = form.cleaned_data["daily_rate"]
        vehicle.city = form.cleaned_data.get("city", vehicle.city)
        vehicle.save(update_fields=["make", "model", "year", "daily_rate", "city"])

        if vehicle.vehicle_kind == Vehicle.KIND_CAR:
            subtype.fuel_type = form.cleaned_data.get("fuel_type", subtype.fuel_type)
            subtype.body_style = form.cleaned_data.get("body_style", subtype.body_style)
            subtype.save(update_fields=["fuel_type", "body_style"])
        elif vehicle.vehicle_kind == Vehicle.KIND_BIKE:
            subtype.bike_type = form.cleaned_data.get("bike_type", subtype.bike_type)
            subtype.has_motor = form.cleaned_data.get("has_motor", subtype.has_motor)
            subtype.save(update_fields=["bike_type", "has_motor"])
        elif vehicle.vehicle_kind == Vehicle.KIND_SCOOTER:
            subtype.engine_cc = form.cleaned_data.get("engine_cc", subtype.engine_cc)
            subtype.is_electric = form.cleaned_data.get("is_electric", subtype.is_electric)
            subtype.save(update_fields=["engine_cc", "is_electric"])

        messages.success(request, "Vehicle updated.")
        return redirect("provider_fleet")

    return render(request, "booking/provider_vehicle_form.html", {
        "form": form, "action": "Edit", "vehicle": vehicle,
    })


@login_required
def provider_maintenance(request, vehicle_id):
    guard = _require_provider(request)
    if guard:
        return guard
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    if request.method == "POST":
        try:
            vehicle.send_to_maintenance()
            messages.success(request, f"{vehicle.display_name()} sent to maintenance.")
        except InvalidTransitionError as e:
            messages.error(request, str(e))
    return redirect("provider_fleet")


@login_required
def provider_complete_maintenance(request, vehicle_id):
    guard = _require_provider(request)
    if guard:
        return guard
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    if request.method == "POST":
        try:
            vehicle.complete_maintenance()
            messages.success(request, f"{vehicle.display_name()} is now available.")
        except InvalidTransitionError as e:
            messages.error(request, str(e))
    return redirect("provider_fleet")


@login_required
def provider_delete_vehicle(request, vehicle_id):
    guard = _require_provider(request)
    if guard:
        return guard

    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Vehicle removed from your fleet.")
        return redirect("provider_fleet")
    return render(request, "booking/provider_vehicle_confirm_delete.html", {"vehicle": vehicle})


# ---------------------------------------------------------------------------
# External Services
# ---------------------------------------------------------------------------

@login_required
def parking(request):
    lots = ParkingService().get_nearby_lots()
    return render(request, "booking/parking.html", {"lots": lots})


@login_required
def transit(request):
    facade = TransitFacade()
    stops = facade.get_nearby_stops()
    stop_id = request.GET.get("stop_id")
    departures = facade.get_next_departures(stop_id) if stop_id else []
    return render(request, "booking/transit.html", {"stops": stops, "departures": departures, "stop_id": stop_id})


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@login_required
def rental_analytics(request):
    user = request.user
    if not (user.is_provider or user.is_city_admin):
        messages.error(request, "Access restricted.")
        return redirect("role_dashboard")

    if user.is_provider:
        reservations = Reservation.objects.filter(vehicle__owner=user)
        vehicles = Vehicle.objects.filter(owner=user)
    else:
        reservations = Reservation.objects.all()
        vehicles = Vehicle.objects.all()

    total = reservations.count()
    confirmed = reservations.filter(
        status__in=[Reservation.STATUS_CONFIRMED, Reservation.STATUS_RETURNED]
    ).count()
    returned = reservations.filter(status=Reservation.STATUS_RETURNED).count()
    revenue = reservations.filter(
        status__in=[Reservation.STATUS_CONFIRMED, Reservation.STATUS_RETURNED]
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    by_kind = []
    for kind_code, kind_label in Vehicle.KIND_CHOICES:
        kind_res = reservations.filter(vehicle__vehicle_kind=kind_code)
        kind_rev = kind_res.filter(
            status__in=[Reservation.STATUS_CONFIRMED, Reservation.STATUS_RETURNED]
        ).aggregate(total=Sum("total_amount"))["total"] or 0
        by_kind.append({"kind": kind_label, "kind_code": kind_code, "count": kind_res.count(), "revenue": kind_rev})

    top_vehicles = vehicles.order_by("-total_trips")[:5]
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    recent = reservations.filter(created_at__gte=thirty_days_ago).count()

    rows = []
    for r in reservations.select_related("vehicle", "user").order_by("-created_at"):
        rows.append({
            "id": r.id,
            "user": r.user.get_full_name() or r.user.username,
            "vehicle": f"{r.vehicle.year} {r.vehicle.make} {r.vehicle.model}",
            "vehicle_id": r.vehicle_id,
            "kind": r.vehicle.vehicle_kind,
            "start": str(r.start_date),
            "end": str(r.end_date),
            "amount": float(r.total_amount),
            "status": r.status,
            "status_display": r.get_status_display(),
            "created": r.created_at.strftime("%Y-%m-%d"),
            "recent": r.created_at >= thirty_days_ago,
        })
    reservations_json = json.dumps(rows)

    return render(request, "booking/rental_analytics.html", {
        "total": total,
        "confirmed": confirmed,
        "returned": returned,
        "revenue": revenue,
        "by_kind": by_kind,
        "top_vehicles": top_vehicles,
        "recent": recent,
        "is_provider": user.is_provider,
        "reservations_json": reservations_json,
    })


@login_required
def gateway_analytics(request):
    if not request.user.is_city_admin:
        messages.error(request, "Access restricted to City Admins.")
        return redirect("role_dashboard")

    lots = ParkingService().get_nearby_lots()
    stops = TransitFacade().get_nearby_stops()

    total_spots = sum(lot.total_spots for lot in lots)
    available_spots = sum(lot.available_spots for lot in lots)
    occupied_spots = total_spots - available_spots
    overall_occupancy = round(occupied_spots / total_spots * 100) if total_spots else 0

    return render(request, "booking/gateway_analytics.html", {
        "lots": lots,
        "stops": stops,
        "total_spots": total_spots,
        "available_spots": available_spots,
        "occupied_spots": occupied_spots,
        "overall_occupancy": overall_occupancy,
    })


@login_required
def notifications(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    notifs = Notification.objects.filter(user=request.user).select_related("vehicle")[:50]
    return render(request, "booking/notifications.html", {"notifs": notifs})

@login_required
def my_rewards(request):
    if not request.user.is_commuter:
        return redirect("role_dashboard")
    from .sustainability import (
        reliability_score, total_co2_saved, loyalty_discount,
        co2_saved_kg, DISCOUNT_TIERS, BASELINE_KG_PER_DAY,
    )
    score = reliability_score(request.user)
    discount_rate, discount_label = loyalty_discount(score)
    co2 = total_co2_saved(request.user)

    returned = Reservation.objects.filter(
        user=request.user, status=Reservation.STATUS_RETURNED
    ).select_related("vehicle").order_by("-returned_at")

    rental_co2 = []
    for r in returned:
        days = (r.end_date - r.start_date).days + 1
        saved = co2_saved_kg(r.vehicle, days)
        rental_co2.append({"reservation": r, "days": days, "saved": saved})

    total_res = Reservation.objects.filter(user=request.user).exclude(
        status=Reservation.STATUS_PENDING
    ).count()
    returned_count = returned.count()

    tiers = [
        {"threshold": t, "rate": int(r * 100), "label": l,
         "active": score >= t and (score < DISCOUNT_TIERS[i-1][0] if i > 0 else True)}
        for i, (t, r, l) in enumerate(DISCOUNT_TIERS) if t > 0
    ]

    return render(request, "booking/my_rewards.html", {
        "score": score,
        "discount_rate": int(discount_rate * 100),
        "discount_label": discount_label,
        "co2_saved": co2,
        "rental_co2": rental_co2,
        "total_res": total_res,
        "returned_count": returned_count,
        "tiers": tiers,
    })

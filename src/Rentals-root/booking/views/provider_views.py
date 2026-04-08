from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as _tz

from ..factories import ProviderFactoryA, ProviderFactoryB
from ..forms import ProviderVehicleForm
from ..models import Vehicle, Reservation
from ..observers import fire_overdue_notifications
from ..services import VehicleService
from ..states import InvalidTransitionError


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

    vehicles = list(Vehicle.objects.filter(owner=request.user).order_by("make", "model"))
    overdue_ids = VehicleService.enrich_fleet(vehicles, request.user)

    if overdue_ids:
        overdue_res = list(Reservation.objects.filter(
            vehicle__owner=request.user,
            status=Reservation.STATUS_CONFIRMED,
            vehicle_id__in=overdue_ids,
        ).select_related("vehicle", "user"))
        fire_overdue_notifications(overdue_res)

    return render(request, "booking/provider_fleet.html", {
        "vehicles": vehicles,
        "overdue_count": len(overdue_ids),
        "today": _tz.localdate(),
    })


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
        Vehicle.objects.filter(
            make=common["make"], model=common["model"],
            year=common["year"], owner=request.user,
        ).update(city=city)
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
        VehicleService.update_subtype(vehicle, form.cleaned_data)
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

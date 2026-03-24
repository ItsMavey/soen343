from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import VehicleSearchForm, PaymentForm, ReservationForm
from .models import Vehicle, Reservation


@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by("make", "model")
    form = VehicleSearchForm(request.GET or None)

    if form.is_valid():
        query = form.cleaned_data.get("query")
        vehicle_kind = form.cleaned_data.get("vehicle_kind")
        fuel_type = form.cleaned_data.get("fuel_type")
        min_rate = form.cleaned_data.get("min_rate")
        max_rate = form.cleaned_data.get("max_rate")

        if query:
            vehicles = vehicles.filter(Q(make__icontains=query) | Q(model__icontains=query))
        if vehicle_kind:
            vehicles = vehicles.filter(vehicle_kind=vehicle_kind)
        if fuel_type:
            vehicles = vehicles.filter(car__fuel_type__iexact=fuel_type)
        if min_rate is not None:
            vehicles = vehicles.filter(daily_rate__gte=min_rate)
        if max_rate is not None:
            vehicles = vehicles.filter(daily_rate__lte=max_rate)

    return render(request, "booking/vehicle_list.html", {"vehicles": vehicles, "form": form})


@login_required
def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    subtype = vehicle.get_subtype()
    return render(request, "booking/vehicle_detail.html", {"vehicle": vehicle, "subtype": subtype})


@login_required
def reserve_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    form = ReservationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        overlapping = Reservation.objects.filter(
            vehicle=vehicle,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

        if overlapping:
            form.add_error(None, "This vehicle is already reserved for the selected dates.")
        else:
            days = (end_date - start_date).days + 1
            total_amount = Decimal(days) * vehicle.daily_rate
            reservation = Reservation.objects.create(
                user=request.user,
                vehicle=vehicle,
                start_date=start_date,
                end_date=end_date,
                total_amount=total_amount,
            )
            vehicle.reserve()
            messages.success(request, "Vehicle reserved. Complete payment to confirm.")
            return redirect("reservation_payment", reservation_id=reservation.id)

    return render(request, "booking/reserve_vehicle.html", {"vehicle": vehicle, "form": form})


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
        reservation.vehicle.confirm()
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
            reservation.status = Reservation.STATUS_RETURNED
            reservation.returned_at = timezone.now()
            reservation.save(update_fields=["status", "returned_at"])
            reservation.vehicle.return_vehicle()
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

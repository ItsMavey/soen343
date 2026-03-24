from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CarSearchForm, PaymentForm, ReservationForm
from .models import Car, Reservation


@login_required
def car_list(request):
    cars = Car.objects.all().order_by("make", "model")
    form = CarSearchForm(request.GET or None)

    if form.is_valid():
        query = form.cleaned_data.get("query")
        vehicle_type = form.cleaned_data.get("vehicle_type")
        fuel_type = form.cleaned_data.get("fuel_type")
        min_rate = form.cleaned_data.get("min_rate")
        max_rate = form.cleaned_data.get("max_rate")

        if query:
            cars = cars.filter(Q(make__icontains=query) | Q(model__icontains=query))
        if vehicle_type:
            cars = cars.filter(vehicle_type__iexact=vehicle_type)
        if fuel_type:
            cars = cars.filter(fuel_type__iexact=fuel_type)
        if min_rate is not None:
            cars = cars.filter(daily_rate__gte=min_rate)
        if max_rate is not None:
            cars = cars.filter(daily_rate__lte=max_rate)

    return render(request, "booking/car_list.html", {"cars": cars, "form": form})


@login_required
def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    return render(request, "booking/car_detail.html", {"car": car})


@login_required
def reserve_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    form = ReservationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        overlapping = Reservation.objects.filter(
            car=car,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

        if overlapping:
            form.add_error(None, "This vehicle is already reserved for the selected dates.")
        else:
            days = (end_date - start_date).days + 1
            total_amount = Decimal(days) * car.daily_rate
            reservation = Reservation.objects.create(
                user=request.user,
                car=car,
                start_date=start_date,
                end_date=end_date,
                total_amount=total_amount,
            )
            car.is_available = False
            car.save(update_fields=["is_available"])
            messages.success(request, "Vehicle reserved. Complete payment to confirm.")
            return redirect("reservation_payment", reservation_id=reservation.id)

    return render(request, "booking/reserve_car.html", {"car": car, "form": form})


@login_required
def reservation_payment(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("car_list")
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
        return redirect("car_list")
    return render(request, "booking/reservation_detail.html", {"reservation": reservation})


@login_required
def return_vehicle(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("car_list")
    if request.method == "POST":
        if reservation.status == Reservation.STATUS_CONFIRMED:
            reservation.status = Reservation.STATUS_RETURNED
            reservation.returned_at = timezone.now()
            reservation.save(update_fields=["status", "returned_at"])

            car = reservation.car
            car.is_available = True
            car.total_trips += 1
            car.save(update_fields=["is_available", "total_trips"])
            messages.success(request, "Vehicle return completed.")
        else:
            messages.error(request, "Only confirmed reservations can be returned.")
    return redirect("reservation_detail", reservation_id=reservation.id)


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(user=request.user).select_related("car")
    return render(request, "booking/my_reservations.html", {"reservations": reservations})


@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.user_id != request.user.id:
        messages.error(request, "You cannot access another user's reservation.")
        return redirect("car_list")
    if request.method == "POST":
        if reservation.status == Reservation.STATUS_PENDING:
            reservation.status = Reservation.STATUS_CANCELLED
            reservation.save(update_fields=["status"])
            car = reservation.car
            car.is_available = True
            car.save(update_fields=["is_available"])
            messages.success(request, "Reservation cancelled.")
            return redirect("my_reservations")
        else:
            messages.error(request, "Only pending reservations can be cancelled.")
    return redirect("reservation_detail", reservation_id=reservation.id)

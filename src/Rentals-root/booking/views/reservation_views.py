from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils import timezone as _tz

from ..forms import PaymentForm
from ..models import Reservation
from ..observers import fire_overdue_notifications


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
    reservations = list(
        Reservation.objects.filter(user=request.user)
        .select_related("vehicle")
        .order_by("-created_at")
    )
    today = _tz.localdate()
    fire_overdue_notifications(reservations)
    return render(request, "booking/my_reservations.html", {"reservations": reservations, "today": today})


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

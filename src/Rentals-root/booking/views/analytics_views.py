import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import Vehicle, Reservation, Notification
from ..services import ParkingService, TransitFacade, CITY_COORDS
from ..sustainability import (
    reliability_score, total_co2_saved, loyalty_discount,
    co2_saved_kg, DISCOUNT_TIERS,
)


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

    lots = ParkingService().get_lots()
    lat, lon = CITY_COORDS["MTL"]
    stops = TransitFacade().get_nearby_stops(lat=lat, lon=lon)

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

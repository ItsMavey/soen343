"""
Dashboard service.

Owns data aggregation for the commuter and city admin dashboards.
Views call these methods and handle only HTTP/template concerns.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from booking.external_services import ParkingService
from booking.models import Notification, Vehicle, Reservation
from booking.sustainability import reliability_score, total_co2_saved, loyalty_discount


class DashboardService:

    @staticmethod
    def get_commuter_context(user) -> dict:
        """Compute all context needed for the commuter dashboard."""
        score = reliability_score(user)
        discount_rate, discount_label = loyalty_discount(score)
        co2 = total_co2_saved(user)

        recommendation = None
        # build quick recommendation
        pref_city = user.preferred_city
        pref_type = user.preferred_mobility_type
        if pref_city and pref_type:
            count = Vehicle.objects.filter(
                city=pref_city,
                vehicle_kind=pref_type,
                vehicle_status=Vehicle.STATUS_AVAILABLE,
            ).count()
            if count > 0:
                city_label = dict(user.CITY_CHOICES).get(pref_city, pref_city)
                kind_label = (
                    dict(user.MOBILITY_CHOICES).get(pref_type, pref_type)
                    + ("s" if not pref_type.endswith("S") else "")
                )
                recommendation = f"{count} {kind_label} available in {city_label} right now. Reserve one now."

        return {
            "reliability_score": score,
            "discount_label": discount_label,
            "discount_pct": int(discount_rate * 100),
            "co2_saved": co2,
            "recommendation": recommendation,
        }

    @staticmethod
    def get_admin_context(city_filter: str = "") -> dict:
        """Compute all context needed for the city admin dashboard."""
        UserModel = get_user_model()
        today = timezone.localdate()
        city_labels = dict(Vehicle.CITY_CHOICES)

        # Tile counts
        total_users = UserModel.objects.count()
        active_rentals = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).count()
        trips_today = Reservation.objects.filter(
            status=Reservation.STATUS_RETURNED, returned_at__date=today
        ).count()
        bikes_rented = Reservation.objects.filter(
            vehicle__vehicle_kind=Vehicle.KIND_BIKE, status=Reservation.STATUS_CONFIRMED
        ).count()
        scooters_rented = Reservation.objects.filter(
            vehicle__vehicle_kind=Vehicle.KIND_SCOOTER, status=Reservation.STATUS_CONFIRMED
        ).count()

        # 10 most recent users
        recent_users = list(UserModel.objects.order_by("-date_joined")[:10].values(
            "username", "email", "role", "date_joined"
        ))
        role_map = {r[0]: r[1] for r in UserModel.ROLE_CHOICES}
        for u in recent_users:
            u["role_label"] = role_map.get(u["role"], u["role"])

        # Active rentals list with optional city filter
        active_qs = Reservation.objects.filter(
            status=Reservation.STATUS_CONFIRMED
        ).select_related("vehicle", "user")
        if city_filter:
            active_qs = active_qs.filter(vehicle__city=city_filter)
        # recent active rentals
        active_list = [
            {
                "id": r.id,
                "user": r.user.get_full_name() or r.user.username,
                "vehicle": r.vehicle.display_name(),
                "city": city_labels.get(r.vehicle.city, r.vehicle.city),
                "start": r.start_date,
                "end": r.end_date,
                "overdue": r.end_date < today,
            }
            for r in active_qs.order_by("-created_at")[:50]
        ]
        overdue_active = sum(1 for r in active_list if r["overdue"])

        # Trips completed today
        trips_today_list = [
            {
                "id": r.id,
                "user": r.user.get_full_name() or r.user.username,
                "vehicle": r.vehicle.display_name(),
                "city": city_labels.get(r.vehicle.city, r.vehicle.city),
                "returned_at": r.returned_at,
            }
            for r in Reservation.objects.filter(
                status=Reservation.STATUS_RETURNED, returned_at__date=today
            ).select_related("vehicle", "user").order_by("-returned_at")
        ]

        # Parking utilization by city
        lots = ParkingService().get_lots()
        city_parking = {}
        # group lots by city
        for lot in lots:
            c = lot.city
            if c not in city_parking:
                city_parking[c] = {"city_label": city_labels.get(c, c), "total": 0, "available": 0}
            city_parking[c]["total"] += lot.total_spots
            city_parking[c]["available"] += lot.available_spots
        for cp in city_parking.values():
            occupied = cp["total"] - cp["available"]
            cp["occupancy_pct"] = round(occupied / cp["total"] * 100) if cp["total"] else 0
        parking_by_city = sorted(city_parking.values(), key=lambda x: -x["occupancy_pct"])

        # Active rentals grouped by city
        by_city = list(
            Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED)
            .values("vehicle__city").annotate(cnt=Count("id")).order_by("-cnt")
        )
        for row in by_city:
            row["city_label"] = city_labels.get(row["vehicle__city"], row["vehicle__city"])

        recent_activity = Notification.objects.select_related("vehicle").order_by("-created_at")[:10]

        return {
            "recent_activity": recent_activity,
            "total_users": total_users,
            "active_rentals": active_rentals,
            "trips_today": trips_today,
            "bikes_rented": bikes_rented,
            "scooters_rented": scooters_rented,
            "recent_users": recent_users,
            "active_list": active_list,
            "city_filter": city_filter,
            "city_choices": Vehicle.CITY_CHOICES,
            "trips_today_list": trips_today_list,
            "parking_by_city": parking_by_city,
            "by_city": by_city,
            "overdue_active": overdue_active,
        }

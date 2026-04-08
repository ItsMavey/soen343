"""
Analytics service.

Owns all data aggregation and transformation for rental and gateway dashboards.
Views receive ready-to-render context dicts.
"""
import datetime
import json

from django.db.models import Sum
from django.utils import timezone

from ..external_services import ParkingService, TransitFacade, CITY_COORDS
from ..models import Vehicle, Reservation


class AnalyticsService:

    @staticmethod
    def get_rental_dashboard(user) -> dict:
        """
        Build the full rental analytics context for a provider or admin user.
        Returns a dict ready to pass directly to the template.
        """
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
            by_kind.append({
                "kind": kind_label, "kind_code": kind_code,
                "count": kind_res.count(), "revenue": kind_rev,
            })

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

        return {
            "total": total,
            "confirmed": confirmed,
            "returned": returned,
            "revenue": revenue,
            "by_kind": by_kind,
            "top_vehicles": top_vehicles,
            "recent": recent,
            "is_provider": user.is_provider,
            "reservations_json": json.dumps(rows),
        }

    @staticmethod
    def get_gateway_dashboard() -> dict:
        """
        Build the gateway analytics context (parking + transit).
        Returns a dict ready to pass directly to the template.
        """
        lots = ParkingService().get_lots()
        lat, lon = CITY_COORDS["MTL"]
        stops = TransitFacade().get_nearby_stops(lat=lat, lon=lon)

        total_spots = sum(lot.total_spots for lot in lots)
        available_spots = sum(lot.available_spots for lot in lots)
        occupied_spots = total_spots - available_spots
        overall_occupancy = round(occupied_spots / total_spots * 100) if total_spots else 0

        return {
            "lots": lots,
            "stops": stops,
            "total_spots": total_spots,
            "available_spots": available_spots,
            "occupied_spots": occupied_spots,
            "overall_occupancy": overall_occupancy,
        }

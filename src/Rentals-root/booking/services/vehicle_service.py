"""
Vehicle service.

Owns fleet enrichment, subtype update logic, and observer dispatch.
Moves these concerns out of views and the Vehicle model.
"""
from django.utils import timezone as _tz

from ..models import Reservation, Vehicle


class VehicleService:

    @staticmethod
    def enrich_fleet(vehicles, owner):
        """
        Annotate each vehicle with .is_overdue — True if it has a confirmed
        reservation whose end_date is in the past.
        Returns the set of overdue vehicle IDs for further processing.
        """
        today = _tz.localdate()
        overdue_ids = set(
            Reservation.objects.filter(
                vehicle__owner=owner,
                status=Reservation.STATUS_CONFIRMED,
                end_date__lt=today,
            ).values_list("vehicle_id", flat=True)
        )
        for v in vehicles:
            v.is_overdue = v.id in overdue_ids
        return overdue_ids

    @staticmethod
    def update_subtype(vehicle: Vehicle, form_data: dict) -> None:
        """
        Persist subtype-specific fields for Car, Bike, or Scooter after an edit.
        """
        subtype = vehicle.get_subtype()
        if vehicle.vehicle_kind == Vehicle.KIND_CAR:
            subtype.fuel_type = form_data.get("fuel_type", subtype.fuel_type)
            subtype.body_style = form_data.get("body_style", subtype.body_style)
            subtype.save(update_fields=["fuel_type", "body_style"])
        elif vehicle.vehicle_kind == Vehicle.KIND_BIKE:
            subtype.bike_type = form_data.get("bike_type", subtype.bike_type)
            subtype.has_motor = form_data.get("has_motor", subtype.has_motor)
            subtype.save(update_fields=["bike_type", "has_motor"])
        elif vehicle.vehicle_kind == Vehicle.KIND_SCOOTER:
            subtype.engine_cc = form_data.get("engine_cc", subtype.engine_cc)
            subtype.is_electric = form_data.get("is_electric", subtype.is_electric)
            subtype.save(update_fields=["engine_cc", "is_electric"])

    @staticmethod
    def notify_observers(vehicle: Vehicle, event: str) -> None:
        """
        Fire all registered observers for a vehicle event.
        Extracted from Vehicle._notify_observers to keep model thin.
        """
        from ..observers import UserNotifier, AdminDashboard, RecommendationService
        observers = [UserNotifier(), AdminDashboard()]
        if event == "AVAILABLE":
            observers.append(RecommendationService())
        for observer in observers:
            observer.update(event, vehicle)

"""
Reservation workflow service.

Owns all business logic for creating, confirming, returning, and cancelling
reservations. Views delegate to these methods and handle only HTTP concerns.
"""
from django.utils import timezone

from ..models import Reservation, Vehicle
from ..pricing import select_strategy
from ..sustainability import reliability_score, apply_discount


class ReservationService:

    @staticmethod
    def create(user, vehicle, start_date, end_date, active_count: int) -> Reservation:
        """
        Select pricing strategy, apply loyalty discount, create and return
        a PENDING reservation.
        """
        strategy = select_strategy(start_date, active_count)
        total_amount = strategy.calculate(vehicle.daily_rate, start_date, end_date)
        score = reliability_score(user)
        total_amount, _discount, _ = apply_discount(total_amount, score)
        return Reservation.objects.create(
            user=user,
            vehicle=vehicle,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            pricing_strategy=strategy.name,
        )

    @staticmethod
    def confirm_payment(reservation: Reservation) -> None:
        """Transition reservation from PENDING to CONFIRMED."""
        reservation.status = Reservation.STATUS_CONFIRMED
        reservation.paid_at = timezone.now()
        reservation.save(update_fields=["status", "paid_at"])

    @staticmethod
    def return_vehicle(reservation: Reservation) -> None:
        """Mark reservation RETURNED, increment trip counter, fire observer."""
        vehicle = reservation.vehicle
        vehicle.total_trips += 1
        vehicle.save(update_fields=["total_trips"])
        reservation.status = Reservation.STATUS_RETURNED
        reservation.returned_at = timezone.now()
        reservation.save(update_fields=["status", "returned_at"])
        from ..services.vehicle_service import VehicleService
        VehicleService.notify_observers(vehicle, "RETURNED")

    @staticmethod
    def cancel(reservation: Reservation) -> None:
        """Cancel a PENDING reservation and release the vehicle."""
        reservation.status = Reservation.STATUS_CANCELLED
        reservation.save(update_fields=["status"])
        reservation.vehicle.vehicle_status = Vehicle.STATUS_AVAILABLE
        reservation.vehicle.save(update_fields=["vehicle_status"])

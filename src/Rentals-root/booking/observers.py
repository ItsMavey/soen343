"""
Notification system — Observer pattern.

Observer defines the interface. Subject manages a list of observers and
calls notify(). VehicleSubject wraps Vehicle as a subject. UserNotifier,
AdminDashboard, and RecommendationService are concrete observers.
"""

from abc import ABC, abstractmethod


class Observer(ABC):
    @abstractmethod
    def update(self, event: str, vehicle) -> None:
        pass


class Subject:
    def __init__(self):
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify(self, event: str) -> None:
        for observer in self._observers:
            observer.update(event, self)


# ---------------------------------------------------------------------------
# Concrete observers
# ---------------------------------------------------------------------------

class UserNotifier(Observer):
    """Notifies commuters who have confirmed reservations on the affected vehicle."""

    def update(self, event: str, vehicle) -> None:
        from .models import Reservation, Notification

        if event == "MAINTENANCE":
            affected = Reservation.objects.filter(
                vehicle=vehicle,
                status=Reservation.STATUS_CONFIRMED,
            ).select_related("user")
            for r in affected:
                Notification.objects.create(
                    user=r.user,
                    message=(
                        f"Your reservation for {vehicle.display_name()} "
                        f"may be affected — the vehicle has been sent to maintenance."
                    ),
                    event_type=event,
                    vehicle=vehicle,
                    reservation=r,
                )

        elif event == "AVAILABLE":
            # Notify users with active reservations that the vehicle is back in service
            active = Reservation.objects.filter(
                vehicle=vehicle,
                status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            ).select_related("user")
            seen = set()
            for r in active:
                if r.user_id not in seen:
                    seen.add(r.user_id)
                    Notification.objects.create(
                        user=r.user,
                        message=(
                            f"Good news — {vehicle.display_name()} has returned from maintenance "
                            f"and your reservation is back on track."
                        ),
                        event_type=event,
                        vehicle=vehicle,
                        reservation=r,
                    )
            # Also notify users whose previous booking was cancelled
            cancelled = (
                Reservation.objects.filter(
                    vehicle=vehicle,
                    status=Reservation.STATUS_CANCELLED,
                )
                .select_related("user")
                .order_by("-created_at")[:5]
            )
            for r in cancelled:
                if r.user_id not in seen:
                    seen.add(r.user_id)
                    Notification.objects.create(
                        user=r.user,
                        message=f"{vehicle.display_name()} is now available again.",
                        event_type=event,
                        vehicle=vehicle,
                    )


class AdminDashboard(Observer):
    """Logs all vehicle state-change events as notifications for city admins."""

    MESSAGES = {
        "MAINTENANCE": "was sent to maintenance.",
        "AVAILABLE":   "is back in service.",
        "RETURNED":    "was returned by a commuter.",
    }

    def update(self, event: str, vehicle) -> None:
        from .models import Notification
        from django.contrib.auth import get_user_model

        User = get_user_model()
        msg = f"{vehicle.display_name()} {self.MESSAGES.get(event, f'event: {event}')}"
        for admin in User.objects.filter(role=User.ROLE_ADMIN):
            Notification.objects.create(
                user=admin,
                message=msg,
                event_type=event,
                vehicle=vehicle,
            )


class RecommendationService(Observer):
    """Recommends a newly-available vehicle to users who previously cancelled a booking on it."""

    def update(self, event: str, vehicle) -> None:
        if event != "AVAILABLE":
            return
        from .models import Reservation, Notification

        user_ids = (
            Reservation.objects.filter(
                vehicle=vehicle,
                status=Reservation.STATUS_CANCELLED,
            )
            .values_list("user", flat=True)
            .distinct()[:3]
        )
        for uid in user_ids:
            Notification.objects.create(
                user_id=uid,
                message=(
                    f"A vehicle you previously booked — {vehicle.display_name()} "
                    f"— is available again. Book now before it fills up."
                ),
                event_type="RECOMMENDATION",
                vehicle=vehicle,
            )


def fire_overdue_notifications(reservations):
    """
    For each overdue CONFIRMED reservation (end_date < today), fire a single
    OVERDUE notification to the renter. Idempotent — skips if already sent.
    """
    import datetime
    from django.utils import timezone
    from .models import Notification

    today = timezone.localdate()
    for r in reservations:
        if r.status != "CONFIRMED":
            continue
        if r.end_date >= today:
            continue
        already = Notification.objects.filter(
            reservation=r, event_type="OVERDUE"
        ).exists()
        if already:
            continue
        Notification.objects.create(
            user=r.user,
            vehicle=r.vehicle,
            reservation=r,
            message=(
                f"Your rental of {r.vehicle.display_name()} was due back on "
                f"{r.end_date}. Please return the vehicle as soon as possible."
            ),
            event_type="OVERDUE",
        )
        # Also notify admins via AdminDashboard observer pattern
        from .models import Notification as N
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for admin in User.objects.filter(role="ADMIN"):
            if not N.objects.filter(reservation=r, event_type="OVERDUE", user=admin).exists():
                N.objects.create(
                    user=admin,
                    vehicle=r.vehicle,
                    reservation=r,
                    message=(
                        f"Overdue rental: {r.user.username} has not returned "
                        f"{r.vehicle.display_name()} (due {r.end_date})."
                    ),
                    event_type="OVERDUE",
                )

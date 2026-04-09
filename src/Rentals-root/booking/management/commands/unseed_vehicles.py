"""
Delete all vehicles (and their reservations/notifications via cascade).
Usage: python manage.py unseed_vehicles
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete all vehicles, reservations, and notifications"

    def handle(self, *args, **kwargs):
        from booking.models import Vehicle, Reservation, Notification
        n, r, v = (
            Notification.objects.all().delete()[0],
            Reservation.objects.all().delete()[0],
            Vehicle.objects.all().delete()[0],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {v} vehicles, {r} reservations, {n} notifications."
        ))

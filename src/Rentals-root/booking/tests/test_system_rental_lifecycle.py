"""
System / Acceptance Test — Full Rental Lifecycle

Covers the complete use case flow from vehicle addition through
reservation, payment, return, and cancellation using the Django test
client. No mocks — exercises the full stack end-to-end.
"""
import datetime

from django.test import TestCase
from django.urls import reverse

from booking.models import Vehicle, Reservation, Notification
from .helpers import make_user, make_car


class RentalLifecycleSystemTest(TestCase):
    """
    Use case: Provider adds a vehicle. Commuter searches, reserves,
    pays, and returns it. Validates status transitions at every step.
    """

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.commuter = make_user("commuter", role="COMMUTER")
        make_user("admin", role="ADMIN")   # required by AdminDashboard observer

    # ── Step 1: Provider adds a vehicle ──────────────────────────────────────

    def _provider_add_car(self):
        self.client.force_login(self.provider)
        self.client.post(reverse("provider_add_vehicle"), {
            "vehicle_kind": "CAR",
            "make": "Lifecycle",
            "model": "TestCar",
            "year": 2024,
            "daily_rate": "80.00",
            "city": "MTL",
            "fuel_type": "GASOLINE",
            "body_style": "Sedan",
        })
        return Vehicle.objects.get(make="Lifecycle")

    def test_full_lifecycle(self):
        # 1. Provider adds vehicle
        car = self._provider_add_car()
        self.assertIsNotNone(car)
        self.assertEqual(car.owner, self.provider)
        self.assertEqual(car.vehicle_status, Vehicle.STATUS_AVAILABLE)

        # 2. Commuter logs in and searches for vehicles
        self.client.force_login(self.commuter)
        response = self.client.get(reverse("vehicle_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(car, response.context["vehicles"])

        # 3. Commuter reserves the vehicle
        start = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        end = (datetime.date.today() + datetime.timedelta(days=4)).isoformat()
        response = self.client.post(reverse("reserve_vehicle", args=[car.id]), {
            "start_date": start, "end_date": end,
        })
        res = Reservation.objects.get(user=self.commuter, vehicle=car)
        self.assertEqual(res.status, Reservation.STATUS_PENDING)
        self.assertRedirects(response, reverse("reservation_payment", args=[res.id]))

        # 4. Commuter pays
        self.client.post(reverse("reservation_payment", args=[res.id]),
                         {"confirm_payment": True})
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CONFIRMED)
        self.assertIsNotNone(res.paid_at)

        # 5. Commuter returns the vehicle
        self.client.post(reverse("return_vehicle", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_RETURNED)
        self.assertIsNotNone(res.returned_at)

        # 6. Vehicle trip counter incremented
        car.refresh_from_db()
        self.assertEqual(car.total_trips, 1)

        # 7. Vehicle back to available
        self.assertEqual(car.vehicle_status, Vehicle.STATUS_AVAILABLE)

    def test_cancel_pending_reservation_releases_vehicle(self):
        car = self._provider_add_car()
        self.client.force_login(self.commuter)

        start = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        end = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        self.client.post(reverse("reserve_vehicle", args=[car.id]), {
            "start_date": start, "end_date": end,
        })
        res = Reservation.objects.get(user=self.commuter, vehicle=car)
        self.assertEqual(res.status, Reservation.STATUS_PENDING)

        # Cancel before payment
        self.client.post(reverse("cancel_reservation", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CANCELLED)

        car.refresh_from_db()
        self.assertEqual(car.vehicle_status, Vehicle.STATUS_AVAILABLE)

    def test_my_reservations_shows_lifecycle_history(self):
        car = self._provider_add_car()
        self.client.force_login(self.commuter)

        start = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        end = (datetime.date.today() + datetime.timedelta(days=4)).isoformat()
        self.client.post(reverse("reserve_vehicle", args=[car.id]), {
            "start_date": start, "end_date": end,
        })
        response = self.client.get(reverse("my_reservations"))
        self.assertEqual(len(response.context["reservations"]), 1)

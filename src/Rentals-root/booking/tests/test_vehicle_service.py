import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from booking.models import Vehicle, Reservation
from booking.services.vehicle_service import VehicleService
from .helpers import make_user, make_car, make_bike, make_scooter, make_reservation


class EnrichFleetTests(TestCase):

    def setUp(self):
        self.owner = make_user("owner", role="PROVIDER")
        self.car = make_car()
        self.car.owner = self.owner
        self.car.save()

    def test_non_overdue_annotated_false(self):
        make_reservation(self.owner, self.car, start_offset=1, status=Reservation.STATUS_CONFIRMED)
        vehicles = list(Vehicle.objects.filter(owner=self.owner))
        VehicleService.enrich_fleet(vehicles, self.owner)
        self.assertFalse(vehicles[0].is_overdue)

    def test_overdue_annotated_true(self):
        today = timezone.localdate()
        past_start = today - datetime.timedelta(days=4)
        past_end = today - datetime.timedelta(days=2)
        Reservation.objects.create(
            user=self.owner, vehicle=self.car,
            start_date=past_start, end_date=past_end,
            total_amount=Decimal("100.00"),
            status=Reservation.STATUS_CONFIRMED,
        )
        vehicles = list(Vehicle.objects.filter(owner=self.owner))
        overdue_ids = VehicleService.enrich_fleet(vehicles, self.owner)
        self.assertTrue(vehicles[0].is_overdue)
        self.assertIn(self.car.id, overdue_ids)

    def test_returns_correct_overdue_id_set(self):
        today = timezone.localdate()
        Reservation.objects.create(
            user=self.owner, vehicle=self.car,
            start_date=today - datetime.timedelta(days=3),
            end_date=today - datetime.timedelta(days=1),
            total_amount=Decimal("100.00"),
            status=Reservation.STATUS_CONFIRMED,
        )
        vehicles = list(Vehicle.objects.filter(owner=self.owner))
        overdue_ids = VehicleService.enrich_fleet(vehicles, self.owner)
        self.assertEqual(overdue_ids, {self.car.id})

    def test_no_reservations_all_not_overdue(self):
        vehicles = list(Vehicle.objects.filter(owner=self.owner))
        overdue_ids = VehicleService.enrich_fleet(vehicles, self.owner)
        self.assertFalse(vehicles[0].is_overdue)
        self.assertEqual(len(overdue_ids), 0)


class UpdateSubtypeTests(TestCase):

    def test_updates_car_fields(self):
        car = make_car(fuel_type="GASOLINE")
        VehicleService.update_subtype(car, {"fuel_type": "ELECTRIC", "body_style": "SUV"})
        car.car.refresh_from_db()
        self.assertEqual(car.car.fuel_type, "ELECTRIC")
        self.assertEqual(car.car.body_style, "SUV")

    def test_preserves_car_field_if_key_absent(self):
        car = make_car(fuel_type="HYBRID")
        VehicleService.update_subtype(car, {})
        car.car.refresh_from_db()
        self.assertEqual(car.car.fuel_type, "HYBRID")

    def test_updates_bike_fields(self):
        bike = make_bike(bike_type="STANDARD")
        VehicleService.update_subtype(bike, {"bike_type": "EBIKE", "has_motor": True})
        bike.bike.refresh_from_db()
        self.assertEqual(bike.bike.bike_type, "EBIKE")
        self.assertTrue(bike.bike.has_motor)

    def test_updates_scooter_fields(self):
        scooter = make_scooter(engine_cc=50)
        VehicleService.update_subtype(scooter, {"engine_cc": 125, "is_electric": True})
        scooter.scooter.refresh_from_db()
        self.assertEqual(scooter.scooter.engine_cc, 125)
        self.assertTrue(scooter.scooter.is_electric)


class NotifyObserversTests(TestCase):

    def setUp(self):
        self.car = make_car()

    @patch("booking.observers.AdminDashboard")
    @patch("booking.observers.UserNotifier")
    def test_maintenance_fires_user_notifier_and_admin(self, MockUN, MockAD):
        VehicleService.notify_observers(self.car, "MAINTENANCE")
        MockUN.return_value.update.assert_called_once_with("MAINTENANCE", self.car)
        MockAD.return_value.update.assert_called_once_with("MAINTENANCE", self.car)

    @patch("booking.observers.RecommendationService")
    @patch("booking.observers.AdminDashboard")
    @patch("booking.observers.UserNotifier")
    def test_available_also_fires_recommendation_service(self, MockUN, MockAD, MockRS):
        VehicleService.notify_observers(self.car, "AVAILABLE")
        MockRS.return_value.update.assert_called_once_with("AVAILABLE", self.car)

    @patch("booking.observers.RecommendationService")
    @patch("booking.observers.AdminDashboard")
    @patch("booking.observers.UserNotifier")
    def test_returned_does_not_fire_recommendation_service(self, MockUN, MockAD, MockRS):
        VehicleService.notify_observers(self.car, "RETURNED")
        MockRS.return_value.update.assert_not_called()

# basic tests
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase

from booking.models import Reservation
from booking.services.analytics_service import AnalyticsService
from .helpers import make_user, make_car, make_reservation


class RentalDashboardProviderTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.other_provider = make_user("other", role="PROVIDER")
        self.commuter = make_user("commuter", role="COMMUTER")

        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()

        self.other_car = make_car(make="Honda", model="Civic")
        self.other_car.owner = self.other_provider
        self.other_car.save()

    def test_provider_sees_only_own_reservations(self):
        make_reservation(self.commuter, self.car, status=Reservation.STATUS_RETURNED)
        make_reservation(self.commuter, self.other_car, status=Reservation.STATUS_RETURNED)
        ctx = AnalyticsService.get_rental_dashboard(self.provider)
        self.assertEqual(ctx["total"], 1)

    def test_provider_total_count(self):
        make_reservation(self.commuter, self.car, start_offset=1, status=Reservation.STATUS_CONFIRMED)
        make_reservation(self.commuter, self.car, start_offset=10, status=Reservation.STATUS_RETURNED)
        ctx = AnalyticsService.get_rental_dashboard(self.provider)
        self.assertEqual(ctx["total"], 2)

    def test_revenue_excludes_pending_and_cancelled(self):
        make_reservation(self.commuter, self.car, start_offset=1, status=Reservation.STATUS_PENDING)
        make_reservation(self.commuter, self.car, start_offset=10, status=Reservation.STATUS_CANCELLED)
        ctx = AnalyticsService.get_rental_dashboard(self.provider)
        self.assertEqual(ctx["revenue"], 0)

    def test_revenue_includes_confirmed_and_returned(self):
        make_reservation(self.commuter, self.car, days=2, status=Reservation.STATUS_CONFIRMED)
        make_reservation(self.commuter, self.car, start_offset=10, days=2, status=Reservation.STATUS_RETURNED)
        ctx = AnalyticsService.get_rental_dashboard(self.provider)
        self.assertGreater(ctx["revenue"], 0)

    def test_is_provider_flag_set(self):
        ctx = AnalyticsService.get_rental_dashboard(self.provider)
        self.assertTrue(ctx["is_provider"])


class RentalDashboardAdminTests(TestCase):

    def setUp(self):
        self.admin = make_user("admin", role="ADMIN")
        self.provider = make_user("provider", role="PROVIDER")
        self.commuter = make_user("commuter", role="COMMUTER")
        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()

    def test_admin_sees_all_reservations(self):
        make_reservation(self.commuter, self.car, status=Reservation.STATUS_RETURNED)
        ctx = AnalyticsService.get_rental_dashboard(self.admin)
        self.assertEqual(ctx["total"], 1)

    def test_is_provider_flag_false_for_admin(self):
        ctx = AnalyticsService.get_rental_dashboard(self.admin)
        self.assertFalse(ctx["is_provider"])

    def test_by_kind_contains_all_vehicle_types(self):
        ctx = AnalyticsService.get_rental_dashboard(self.admin)
        kinds = [item["kind_code"] for item in ctx["by_kind"]]
        self.assertIn("CAR", kinds)
        self.assertIn("BIKE", kinds)
        self.assertIn("SCOOTER", kinds)


class GatewayDashboardTests(TestCase):

    @patch("booking.services.analytics_service.TransitFacade")
    @patch("booking.services.analytics_service.ParkingService")
    def test_returns_expected_keys(self, MockPS, MockTF):
        MockPS.return_value.get_lots.return_value = []
        MockTF.return_value.get_nearby_stops.return_value = []
        ctx = AnalyticsService.get_gateway_dashboard()
        for key in ("lots", "stops", "total_spots", "available_spots", "occupied_spots", "overall_occupancy"):
            self.assertIn(key, ctx)

    @patch("booking.services.analytics_service.TransitFacade")
    @patch("booking.services.analytics_service.ParkingService")
    def test_occupancy_zero_when_no_spots(self, MockPS, MockTF):
        MockPS.return_value.get_lots.return_value = []
        MockTF.return_value.get_nearby_stops.return_value = []
        ctx = AnalyticsService.get_gateway_dashboard()
        self.assertEqual(ctx["overall_occupancy"], 0)

    @patch("booking.services.analytics_service.TransitFacade")
    @patch("booking.services.analytics_service.ParkingService")
    def test_occupancy_calculated_correctly(self, MockPS, MockTF):
        lot = MagicMock()
        lot.total_spots = 100
        lot.available_spots = 40
        MockPS.return_value.get_lots.return_value = [lot]
        MockTF.return_value.get_nearby_stops.return_value = []
        ctx = AnalyticsService.get_gateway_dashboard()
        self.assertEqual(ctx["total_spots"], 100)
        self.assertEqual(ctx["available_spots"], 40)
        self.assertEqual(ctx["occupied_spots"], 60)
        self.assertEqual(ctx["overall_occupancy"], 60)

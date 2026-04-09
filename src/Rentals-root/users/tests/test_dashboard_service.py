import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from booking.external_services import ParkingLot
from booking.models import Notification, Reservation, Vehicle
from booking.tests.helpers import make_bike, make_car, make_reservation, make_user
from users.dashboard_service import DashboardService


class CommuterDashboardServiceTests(TestCase):

    @patch("users.dashboard_service.total_co2_saved", return_value=12.5)
    @patch("users.dashboard_service.loyalty_discount", return_value=(0.10, "10% off"))
    @patch("users.dashboard_service.reliability_score", return_value=87)
    def test_recommendation_includes_available_preferred_vehicle_count(
        self, _mock_score, _mock_discount, _mock_co2
    ):
        user = make_user("commuter")
        user.preferred_city = "MTL"
        user.preferred_mobility_type = Vehicle.KIND_CAR
        user.save(update_fields=["preferred_city", "preferred_mobility_type"])

        for city in ("MTL", "MTL", "LAV"):
            car = make_car()
            car.city = city
            car.save(update_fields=["city"])

        context = DashboardService.get_commuter_context(user)

        self.assertEqual(context["reliability_score"], 87)
        self.assertEqual(context["discount_label"], "10% off")
        self.assertEqual(context["discount_pct"], 10)
        self.assertEqual(context["co2_saved"], 12.5)
        self.assertEqual(
            context["recommendation"],
            "2 Cars available in Montreal right now. Reserve one now.",
        )

    @patch("users.dashboard_service.total_co2_saved", return_value=3.2)
    @patch("users.dashboard_service.loyalty_discount", return_value=(0.05, "5% off"))
    @patch("users.dashboard_service.reliability_score", return_value=55)
    def test_recommendation_absent_without_matching_available_vehicle(
        self, _mock_score, _mock_discount, _mock_co2
    ):
        user = make_user("commuter2")
        user.preferred_city = "MTL"
        user.preferred_mobility_type = Vehicle.KIND_SCOOTER
        user.save(update_fields=["preferred_city", "preferred_mobility_type"])

        unavailable = make_car()
        unavailable.city = "MTL"
        unavailable.vehicle_status = Vehicle.STATUS_MAINTENANCE
        unavailable.save(update_fields=["city", "vehicle_status"])

        context = DashboardService.get_commuter_context(user)

        self.assertIsNone(context["recommendation"])


class AdminDashboardServiceTests(TestCase):

    @patch("users.dashboard_service.ParkingService")
    def test_city_filter_limits_active_list_and_counts_overdue(self, mock_parking_service):
        mock_parking_service.return_value.get_lots.return_value = [
            ParkingLot("L1", "Lot 1", "Addr", 10, 2.5, "MTL"),
            ParkingLot("L2", "Lot 2", "Addr", 20, 3.0, "LAV"),
        ]

        admin = make_user("admin", role="ADMIN")
        commuter = make_user("commuter-admin")
        provider = make_user("provider", role="PROVIDER")

        montreal_vehicle = make_car()
        montreal_vehicle.owner = provider
        montreal_vehicle.city = "MTL"
        montreal_vehicle.save(update_fields=["owner", "city"])

        laval_vehicle = make_bike()
        laval_vehicle.owner = provider
        laval_vehicle.city = "LAV"
        laval_vehicle.save(update_fields=["owner", "city"])

        today = timezone.localdate()
        overdue = Reservation.objects.create(
            user=commuter,
            vehicle=montreal_vehicle,
            start_date=today - datetime.timedelta(days=4),
            end_date=today - datetime.timedelta(days=1),
            total_amount=100,
            status=Reservation.STATUS_CONFIRMED,
        )
        Reservation.objects.create(
            user=commuter,
            vehicle=laval_vehicle,
            start_date=today,
            end_date=today + datetime.timedelta(days=1),
            total_amount=40,
            status=Reservation.STATUS_CONFIRMED,
        )
        returned = Reservation.objects.create(
            user=commuter,
            vehicle=montreal_vehicle,
            start_date=today - datetime.timedelta(days=2),
            end_date=today - datetime.timedelta(days=1),
            total_amount=75,
            status=Reservation.STATUS_RETURNED,
            returned_at=timezone.now(),
        )
        Notification.objects.create(
            user=admin,
            vehicle=montreal_vehicle,
            reservation=overdue,
            message="Vehicle overdue",
            event_type=Notification.EVENT_MAINTENANCE,
        )

        context = DashboardService.get_admin_context(city_filter="MTL")

        self.assertEqual(context["active_rentals"], 2)
        self.assertEqual(len(context["active_list"]), 1)
        self.assertEqual(context["active_list"][0]["city"], "Montreal")
        self.assertTrue(context["active_list"][0]["overdue"])
        self.assertEqual(context["overdue_active"], 1)
        self.assertEqual(context["trips_today"], 1)
        self.assertEqual(context["trips_today_list"][0]["id"], returned.id)
        self.assertEqual(context["city_filter"], "MTL")
        self.assertEqual(context["recent_activity"].count(), 1)

    @patch("users.dashboard_service.ParkingService")
    def test_parking_and_city_breakdowns_are_aggregated(self, mock_parking_service):
        lot1 = ParkingLot("L1", "Lot 1", "Addr", 10, 2.5, "MTL")
        lot1.available_spots = 4
        lot2 = ParkingLot("L2", "Lot 2", "Addr", 15, 2.5, "MTL")
        lot2.available_spots = 3
        lot3 = ParkingLot("L3", "Lot 3", "Addr", 20, 2.5, "LAV")
        lot3.available_spots = 10
        mock_parking_service.return_value.get_lots.return_value = [lot1, lot2, lot3]

        commuter = make_user("city-breakdown")
        provider = make_user("provider-breakdown", role="PROVIDER")

        car = make_car()
        car.owner = provider
        car.city = "MTL"
        car.save(update_fields=["owner", "city"])

        bike = make_bike()
        bike.owner = provider
        bike.city = "LAV"
        bike.save(update_fields=["owner", "city"])

        make_reservation(commuter, car, status=Reservation.STATUS_CONFIRMED)
        make_reservation(commuter, bike, status=Reservation.STATUS_CONFIRMED)

        context = DashboardService.get_admin_context()

        by_city = {row["vehicle__city"]: row["cnt"] for row in context["by_city"]}
        parking = {row["city_label"]: row for row in context["parking_by_city"]}

        self.assertEqual(by_city["MTL"], 1)
        self.assertEqual(by_city["LAV"], 1)
        self.assertEqual(parking["Montreal"]["total"], 25)
        self.assertEqual(parking["Montreal"]["available"], 7)
        self.assertEqual(parking["Montreal"]["occupancy_pct"], 72)
        self.assertEqual(parking["Laval"]["occupancy_pct"], 50)

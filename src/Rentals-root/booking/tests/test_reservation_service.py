import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from booking.models import Reservation, Vehicle
from booking.services.reservation_service import ReservationService
from .helpers import make_user, make_car, make_reservation


class ReservationServiceCreateTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car(daily_rate="100.00")
        self.start = datetime.date(2030, 6, 2)   # Monday (standard)
        self.end = datetime.date(2030, 6, 4)     # Wednesday  (3 days)

    def test_creates_pending_reservation(self):
        res = ReservationService.create(self.user, self.car, self.start, self.end, active_count=0)
        self.assertEqual(res.status, Reservation.STATUS_PENDING)

    def test_reservation_stored_in_db(self):
        ReservationService.create(self.user, self.car, self.start, self.end, active_count=0)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_total_amount_is_positive(self):
        res = ReservationService.create(self.user, self.car, self.start, self.end, active_count=0)
        self.assertGreater(res.total_amount, Decimal("0.00"))

    def test_pricing_strategy_name_stored(self):
        res = ReservationService.create(self.user, self.car, self.start, self.end, active_count=0)
        self.assertIn(res.pricing_strategy, ["STANDARD", "WEEKEND", "SURGE"])

    def test_paid_at_is_none_on_creation(self):
        res = ReservationService.create(self.user, self.car, self.start, self.end, active_count=0)
        self.assertIsNone(res.paid_at)


class ReservationServiceConfirmTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car()
        self.res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)

    def test_status_becomes_confirmed(self):
        ReservationService.confirm_payment(self.res)
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, Reservation.STATUS_CONFIRMED)

    def test_paid_at_is_set(self):
        ReservationService.confirm_payment(self.res)
        self.res.refresh_from_db()
        self.assertIsNotNone(self.res.paid_at)


class ReservationServiceReturnTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car()
        self.res = make_reservation(self.user, self.car, status=Reservation.STATUS_CONFIRMED)
        self.initial_trips = self.car.total_trips

    def test_status_becomes_returned(self):
        ReservationService.return_vehicle(self.res)
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, Reservation.STATUS_RETURNED)

    def test_returned_at_is_set(self):
        ReservationService.return_vehicle(self.res)
        self.res.refresh_from_db()
        self.assertIsNotNone(self.res.returned_at)

    def test_trip_counter_incremented(self):
        ReservationService.return_vehicle(self.res)
        self.car.refresh_from_db()
        self.assertEqual(self.car.total_trips, self.initial_trips + 1)


class ReservationServiceCancelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car()
        self.res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)
        self.car.vehicle_status = Vehicle.STATUS_RESERVED
        self.car.save()

    def test_status_becomes_cancelled(self):
        ReservationService.cancel(self.res)
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, Reservation.STATUS_CANCELLED)

    def test_vehicle_released_to_available(self):
        ReservationService.cancel(self.res)
        self.car.refresh_from_db()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_AVAILABLE)

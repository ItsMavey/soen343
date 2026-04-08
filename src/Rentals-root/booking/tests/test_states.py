from django.test import TestCase

from booking.models import Vehicle
from booking.states import AvailableState, InvalidTransitionError
from .helpers import make_car


class VehicleStateTests(TestCase):

    def setUp(self):
        self.car = make_car()

    def test_initial_state_is_available(self):
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_AVAILABLE)
        self.assertIsInstance(self.car.state, AvailableState)

    def test_reserve_from_available(self):
        self.car.reserve()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_RESERVED)

    def test_send_to_maintenance_from_available(self):
        self.car.send_to_maintenance()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_MAINTENANCE)

    def test_complete_maintenance(self):
        self.car.send_to_maintenance()
        self.car.complete_maintenance()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_AVAILABLE)

    def test_cannot_reserve_from_maintenance(self):
        self.car.send_to_maintenance()
        with self.assertRaises(InvalidTransitionError):
            self.car.reserve()

    def test_cannot_complete_maintenance_when_available(self):
        with self.assertRaises(InvalidTransitionError):
            self.car.complete_maintenance()

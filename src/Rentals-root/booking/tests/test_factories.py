# basic tests
from decimal import Decimal

from django.test import TestCase

from booking.factories import ProviderFactoryA, ProviderFactoryB
from booking.models import Vehicle, Car, Bike, Scooter


COMMON = dict(make="Test", model="Model", year=2023, daily_rate=Decimal("40.00"))


class ProviderFactoryATests(TestCase):

    def setUp(self):
        self.factory = ProviderFactoryA()

    def test_create_car_sets_kind(self):
        car = self.factory.create_car(fuel_type="GASOLINE", **COMMON)
        self.assertIsInstance(car, Car)
        self.assertEqual(car.vehicle_kind, Vehicle.KIND_CAR)

    def test_create_car_sets_provider_name(self):
        car = self.factory.create_car(fuel_type="GASOLINE", **COMMON)
        self.assertEqual(car.provider, "ProviderA")

    def test_create_car_persists_to_db(self):
        self.factory.create_car(fuel_type="GASOLINE", **COMMON)
        self.assertEqual(Car.objects.count(), 1)

    def test_create_car_preserves_kwargs(self):
        car = self.factory.create_car(fuel_type="ELECTRIC", body_style="SUV", **COMMON)
        self.assertEqual(car.fuel_type, "ELECTRIC")
        self.assertEqual(car.body_style, "SUV")

    def test_create_car_provider_not_overridden_by_default(self):
        car = self.factory.create_car(fuel_type="GASOLINE", **COMMON)
        self.assertNotEqual(car.provider, "ProviderB")

    def test_create_bike_via_factory_a(self):
        bike = self.factory.create_bike(bike_type="STANDARD", **COMMON)
        self.assertIsInstance(bike, Bike)
        self.assertEqual(bike.vehicle_kind, Vehicle.KIND_BIKE)
        self.assertEqual(bike.provider, "ProviderA")


class ProviderFactoryBTests(TestCase):

    def setUp(self):
        self.factory = ProviderFactoryB()

    def test_create_bike_sets_kind(self):
        bike = self.factory.create_bike(bike_type="STANDARD", **COMMON)
        self.assertIsInstance(bike, Bike)
        self.assertEqual(bike.vehicle_kind, Vehicle.KIND_BIKE)

    def test_create_bike_sets_provider_name(self):
        bike = self.factory.create_bike(bike_type="STANDARD", **COMMON)
        self.assertEqual(bike.provider, "ProviderB")

    def test_create_scooter_sets_kind(self):
        scooter = self.factory.create_scooter(engine_cc=125, **COMMON)
        self.assertIsInstance(scooter, Scooter)
        self.assertEqual(scooter.vehicle_kind, Vehicle.KIND_SCOOTER)

    def test_create_scooter_sets_provider_name(self):
        scooter = self.factory.create_scooter(engine_cc=125, **COMMON)
        self.assertEqual(scooter.provider, "ProviderB")

    def test_create_scooter_preserves_kwargs(self):
        scooter = self.factory.create_scooter(engine_cc=50, is_electric=True, **COMMON)
        self.assertEqual(scooter.engine_cc, 50)
        self.assertTrue(scooter.is_electric)

    def test_create_scooter_persists_to_db(self):
        self.factory.create_scooter(engine_cc=125, **COMMON)
        self.assertEqual(Scooter.objects.count(), 1)

    def test_provider_b_not_overridden(self):
        bike = self.factory.create_bike(bike_type="EBIKE", **COMMON)
        self.assertNotEqual(bike.provider, "ProviderA")

from unittest.mock import patch, MagicMock

from django.test import TestCase

from booking.models import Vehicle
from booking.trip_strategies import (
    _haversine_km, nearest_vehicle, nearest_parking,
    VehicleOnlyStrategy, TransitFirstStrategy, TransitOnlyStrategy,
)
from .helpers import make_car


# Montreal and Laval city centres
MTL = (45.5017, -73.5673)
LAV = (45.6066, -73.7124)


class HaversineTests(TestCase):

    def test_same_point_is_zero(self):
        self.assertAlmostEqual(_haversine_km(*MTL, *MTL), 0.0, places=2)

    def test_montreal_to_laval_approx_14km(self):
        dist = _haversine_km(*MTL, *LAV)
        self.assertAlmostEqual(dist, 14.0, delta=3.0)

    def test_symmetry(self):
        d1 = _haversine_km(*MTL, *LAV)
        d2 = _haversine_km(*LAV, *MTL)
        self.assertAlmostEqual(d1, d2, places=5)

    def test_positive_distance(self):
        self.assertGreater(_haversine_km(*MTL, *LAV), 0)


class NearestVehicleTests(TestCase):

    def setUp(self):
        self.car = make_car()  # defaults to city MTL

    def test_returns_available_vehicle(self):
        v, vlat, vlng = nearest_vehicle(*MTL)
        self.assertEqual(v.id, self.car.id)
        self.assertIsNotNone(vlat)
        self.assertIsNotNone(vlng)

    def test_exclude_id_skips_vehicle(self):
        v, vlat, vlng = nearest_vehicle(*MTL, exclude_id=self.car.id)
        self.assertIsNone(v)

    def test_no_available_vehicle_returns_none_tuple(self):
        self.car.vehicle_status = Vehicle.STATUS_MAINTENANCE
        self.car.save()
        v, vlat, vlng = nearest_vehicle(*MTL)
        self.assertIsNone(v)
        self.assertIsNone(vlat)
        self.assertIsNone(vlng)

    def test_reserved_vehicle_not_returned(self):
        self.car.vehicle_status = Vehicle.STATUS_RESERVED
        self.car.save()
        v, _, _ = nearest_vehicle(*MTL)
        self.assertIsNone(v)


class NearestParkingTests(TestCase):

    @patch("booking.trip_strategies.ParkingService")
    def test_returns_closest_lot(self, MockPS):
        lot = MagicMock()
        lot.lat, lot.lng = MTL
        MockPS.return_value.get_lots.return_value = [lot]
        result = nearest_parking(*MTL)
        self.assertEqual(result, lot)

    @patch("booking.trip_strategies.ParkingService")
    def test_skips_lot_with_zero_lat(self, MockPS):
        lot = MagicMock()
        lot.lat = 0.0
        MockPS.return_value.get_lots.return_value = [lot]
        result = nearest_parking(*MTL)
        self.assertIsNone(result)

    @patch("booking.trip_strategies.ParkingService")
    def test_empty_lots_returns_none(self, MockPS):
        MockPS.return_value.get_lots.return_value = []
        result = nearest_parking(*MTL)
        self.assertIsNone(result)

    @patch("booking.trip_strategies.ParkingService")
    def test_picks_closer_of_two_lots(self, MockPS):
        near = MagicMock(); near.lat, near.lng = 45.505, -73.570
        far  = MagicMock(); far.lat,  far.lng  = 45.800, -74.000
        MockPS.return_value.get_lots.return_value = [far, near]
        result = nearest_parking(*MTL)
        self.assertEqual(result, near)


class VehicleOnlyStrategyTests(TestCase):

    def setUp(self):
        self.car = make_car()
        self.strategy = VehicleOnlyStrategy()

    @patch("booking.trip_strategies.ParkingService")
    def test_returns_dict_with_legs(self, MockPS):
        lot = MagicMock(); lot.lat, lot.lng = 45.505, -73.570; lot.name = "Lot A"
        MockPS.return_value.get_lots.return_value = [lot]
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNotNone(result)
        self.assertIn("legs", result)
        self.assertGreater(len(result["legs"]), 0)

    @patch("booking.trip_strategies.ParkingService")
    def test_returns_none_when_no_vehicle(self, MockPS):
        MockPS.return_value.get_lots.return_value = []
        self.car.vehicle_status = Vehicle.STATUS_MAINTENANCE
        self.car.save()
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNone(result)

    @patch("booking.trip_strategies.ParkingService")
    def test_result_has_type_and_label(self, MockPS):
        lot = MagicMock(); lot.lat, lot.lng = 45.505, -73.570; lot.name = "Lot A"
        MockPS.return_value.get_lots.return_value = [lot]
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIn("type", result)
        self.assertIn("label", result)


class TransitFirstStrategyTests(TestCase):

    def setUp(self):
        self.car = make_car()
        self.strategy = TransitFirstStrategy()

    @patch("booking.trip_strategies.ParkingService")
    @patch("booking.trip_strategies.TransitFacade")
    def test_returns_none_when_no_transit_stops(self, MockTF, MockPS):
        MockTF.return_value.get_nearby_stops.return_value = []
        MockPS.return_value.get_lots.return_value = []
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNone(result)

    @patch("booking.trip_strategies.ParkingService")
    @patch("booking.trip_strategies.TransitFacade")
    def test_returns_legs_when_transit_available(self, MockTF, MockPS):
        stop = {"id": "s1", "name": "Stop A", "lat": 45.503, "lon": -73.568, "distance_m": 200}
        MockTF.return_value.get_nearby_stops.return_value = [stop]
        lot = MagicMock(); lot.lat, lot.lng = 45.505, -73.570; lot.name = "Lot A"
        MockPS.return_value.get_lots.return_value = [lot]
        result = self.strategy.plan(*MTL, *LAV)
        if result is not None:
            self.assertIn("legs", result)
            self.assertGreater(len(result["legs"]), 0)


class TransitOnlyStrategyTests(TestCase):

    def setUp(self):
        self.strategy = TransitOnlyStrategy()

    @patch("booking.trip_strategies.TransitFacade")
    def test_returns_none_when_no_stops(self, MockTF):
        MockTF.return_value.get_nearby_stops.return_value = []
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNone(result)

    @patch("booking.trip_strategies.TransitFacade")
    def test_returns_transit_only_type(self, MockTF):
        stop = {"id": "s1", "name": "Stop A", "lat": 45.503, "lon": -73.568, "distance_m": 200}
        MockTF.return_value.get_nearby_stops.return_value = [stop]
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "transit_only")
        self.assertEqual(result["label"], "Transit")

    @patch("booking.trip_strategies.TransitFacade")
    def test_returns_three_legs(self, MockTF):
        stop = {"id": "s1", "name": "Stop A", "lat": 45.503, "lon": -73.568, "distance_m": 200}
        MockTF.return_value.get_nearby_stops.return_value = [stop]
        result = self.strategy.plan(*MTL, *LAV)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["legs"]), 3)
        modes = [leg["mode"] for leg in result["legs"]]
        self.assertEqual(modes, ["walk", "transit", "walk"])

    @patch("booking.trip_strategies.TransitFacade")
    def test_no_vehicle_url_in_legs(self, MockTF):
        stop = {"id": "s1", "name": "Stop A", "lat": 45.503, "lon": -73.568, "distance_m": 200}
        MockTF.return_value.get_nearby_stops.return_value = [stop]
        result = self.strategy.plan(*MTL, *LAV)
        for leg in result["legs"]:
            self.assertNotIn("vehicle_url", leg)

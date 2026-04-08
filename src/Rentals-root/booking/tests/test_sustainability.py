from decimal import Decimal

from django.test import TestCase

from booking.models import Reservation
from booking.sustainability import reliability_score, co2_saved_kg, loyalty_discount, apply_discount
from .helpers import make_user, make_car, make_reservation


class ReliabilityScoreTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car()

    def test_new_user_gets_100(self):
        self.assertEqual(reliability_score(self.user), 100)

    def test_all_returned_gets_100(self):
        make_reservation(self.user, self.car, status=Reservation.STATUS_RETURNED)
        self.assertEqual(reliability_score(self.user), 100)

    def test_partial_returns_lower_score(self):
        make_reservation(self.user, self.car, start_offset=1, status=Reservation.STATUS_RETURNED)
        make_reservation(self.user, self.car, start_offset=10, status=Reservation.STATUS_CONFIRMED)
        score = reliability_score(self.user)
        self.assertLess(score, 100)
        self.assertGreater(score, 0)

    def test_cancelled_reduces_score(self):
        make_reservation(self.user, self.car, start_offset=1, status=Reservation.STATUS_CANCELLED)
        score = reliability_score(self.user)
        self.assertLess(score, 100)


class LoyaltyDiscountTests(TestCase):

    def test_score_below_50_no_discount(self):
        rate, _ = loyalty_discount(40)
        self.assertEqual(rate, Decimal("0.00"))

    def test_score_50_gives_5_percent(self):
        rate, _ = loyalty_discount(50)
        self.assertEqual(rate, Decimal("0.05"))

    def test_score_75_gives_10_percent(self):
        rate, _ = loyalty_discount(75)
        self.assertEqual(rate, Decimal("0.10"))

    def test_score_90_gives_15_percent(self):
        rate, _ = loyalty_discount(90)
        self.assertEqual(rate, Decimal("0.15"))

    def test_apply_discount_reduces_amount(self):
        discounted, saved, _ = apply_discount(Decimal("100.00"), 90)
        self.assertEqual(discounted, Decimal("85.00"))
        self.assertEqual(saved, Decimal("15.00"))

    def test_apply_discount_no_change_below_threshold(self):
        discounted, saved, _ = apply_discount(Decimal("100.00"), 30)
        self.assertEqual(discounted, Decimal("100.00"))
        self.assertEqual(saved, Decimal("0.00"))


class CO2SavingsTests(TestCase):

    def test_electric_car_saves_more_than_gasoline(self):
        gasoline_car = make_car(fuel_type="GASOLINE")
        electric_car = make_car(make="Tesla", model="Model 3", fuel_type="ELECTRIC")
        self.assertGreater(co2_saved_kg(electric_car, 1), co2_saved_kg(gasoline_car, 1))

    def test_gasoline_saves_zero(self):
        car = make_car(fuel_type="GASOLINE")
        self.assertEqual(co2_saved_kg(car, 1), 0)

    def test_electric_saves_positive(self):
        car = make_car(fuel_type="ELECTRIC")
        self.assertGreater(co2_saved_kg(car, 1), 0)

    def test_savings_scale_with_days(self):
        car = make_car(fuel_type="ELECTRIC")
        self.assertEqual(co2_saved_kg(car, 4), co2_saved_kg(car, 2) * 2)

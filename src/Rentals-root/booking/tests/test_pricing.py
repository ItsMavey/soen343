from decimal import Decimal

from django.test import TestCase

from booking.pricing import StandardPricing, WeekendPricing, SurgePricing
from .helpers import _dates


class PricingStrategyTests(TestCase):

    def test_standard_pricing_no_change(self):
        strategy = StandardPricing()
        start, end = _dates(3)
        self.assertEqual(strategy.calculate(Decimal("100.00"), start, end), Decimal("300.00"))

    def test_weekend_pricing_adds_surcharge(self):
        strategy = WeekendPricing()
        base = Decimal("100.00")
        start, end = _dates(3)
        result = strategy.calculate(base, start, end)
        self.assertEqual(result, (base * Decimal("1.25") * 3).quantize(Decimal("0.01")))

    def test_surge_pricing_adds_surcharge(self):
        strategy = SurgePricing()
        base = Decimal("100.00")
        start, end = _dates(3)
        result = strategy.calculate(base, start, end)
        self.assertEqual(result, (base * Decimal("1.50") * 3).quantize(Decimal("0.01")))

    def test_standard_single_day(self):
        strategy = StandardPricing()
        start, end = _dates(1)
        self.assertEqual(strategy.calculate(Decimal("75.00"), start, end), Decimal("75.00"))

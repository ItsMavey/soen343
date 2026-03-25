"""
Pricing strategies — Strategy pattern.

PricingStrategy defines the interface. StandardPricing, WeekendPricing,
and SurgePricing are concrete strategies. select_strategy() picks the
right one at runtime based on demand and rental dates.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class PricingStrategy(ABC):
    name = ""
    label = ""
    description = ""
    multiplier = Decimal("1.00")

    @abstractmethod
    def calculate(self, daily_rate: Decimal, start_date, end_date) -> Decimal:
        pass


class StandardPricing(PricingStrategy):
    name = "STANDARD"
    label = "Standard Rate"
    description = "Base daily rate, no surcharges."
    multiplier = Decimal("1.00")

    def calculate(self, daily_rate: Decimal, start_date, end_date) -> Decimal:
        days = (end_date - start_date).days + 1
        return (daily_rate * days).quantize(Decimal("0.01"))


class WeekendPricing(PricingStrategy):
    name = "WEEKEND"
    label = "Weekend Rate"
    description = "25% surcharge applied — rental starts on a weekend."
    multiplier = Decimal("1.25")

    def calculate(self, daily_rate: Decimal, start_date, end_date) -> Decimal:
        days = (end_date - start_date).days + 1
        return (daily_rate * days * self.multiplier).quantize(Decimal("0.01"))


class SurgePricing(PricingStrategy):
    name = "SURGE"
    label = "Surge Pricing"
    description = "50% surcharge applied — high demand for this vehicle."
    multiplier = Decimal("1.50")

    def calculate(self, daily_rate: Decimal, start_date, end_date) -> Decimal:
        days = (end_date - start_date).days + 1
        return (daily_rate * days * self.multiplier).quantize(Decimal("0.01"))


# Surge threshold: number of active reservations that triggers surge pricing
SURGE_THRESHOLD = 3


def select_strategy(start_date, active_reservation_count: int) -> PricingStrategy:
    """
    Pick the pricing strategy based on demand and rental start date.
    Surge takes priority over weekend pricing.
    """
    if active_reservation_count >= SURGE_THRESHOLD:
        return SurgePricing()
    if start_date.weekday() >= 5:   # Saturday=5, Sunday=6
        return WeekendPricing()
    return StandardPricing()

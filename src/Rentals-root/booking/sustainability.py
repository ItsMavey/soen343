"""
Sustainability and gamification services — Pure Fabrication pattern.

These are stateless computed services with no direct domain object
ownership. They read Reservation/Vehicle data and return derived metrics.
"""

from decimal import Decimal


# ---------------------------------------------------------------------------
# CO2 model (kg per rental day, based on vehicle type/fuel)
# Baseline: gasoline car at ~120g CO2/km × 50km/day ≈ 6 kg/day
# ---------------------------------------------------------------------------

BASELINE_KG_PER_DAY = 6.0  # gasoline reference vehicle

_CAR_FUEL_KG = {
    "GASOLINE": 6.0,
    "DIESEL":   5.0,
    "HYBRID":   3.0,
    "ELECTRIC": 0.8,
}


def _co2_kg_per_day(vehicle) -> float:
    sub = vehicle.get_subtype()
    if hasattr(sub, "fuel_type"):
        return _CAR_FUEL_KG.get(sub.fuel_type, BASELINE_KG_PER_DAY)
    if vehicle.vehicle_kind == "BIKE":
        return 0.0
    if vehicle.vehicle_kind == "SCOOTER":
        return 0.3 if getattr(sub, "is_electric", False) else 2.0
    return BASELINE_KG_PER_DAY


def co2_emitted_kg(vehicle, days: int) -> float:
    """Total CO2 emitted (kg) for a given vehicle and trip length."""
    return round(_co2_kg_per_day(vehicle) * days, 2)


def co2_saved_kg(vehicle, days: int) -> float:
    """CO2 saved (kg) vs a baseline gasoline car for the same trip."""
    return round(max(0.0, (BASELINE_KG_PER_DAY - _co2_kg_per_day(vehicle)) * days), 2)


def total_co2_saved(user) -> float:
    """Cumulative CO2 saved (kg) across all of a user's completed rentals."""
    from .models import Reservation
    returned = Reservation.objects.filter(
        user=user, status=Reservation.STATUS_RETURNED
    ).select_related("vehicle")
    total = 0.0
    for r in returned:
        days = (r.end_date - r.start_date).days + 1
        total += co2_saved_kg(r.vehicle, days)
    return round(total, 1)


# ---------------------------------------------------------------------------
# Reliability score (0–100)
# ---------------------------------------------------------------------------

def reliability_score(user) -> int:
    """
    Score based on ratio of successfully returned reservations to all
    non-pending reservations. New users start at 100.
    """
    from .models import Reservation
    qs = Reservation.objects.filter(
        user=user,
        status__in=[
            Reservation.STATUS_CONFIRMED,
            Reservation.STATUS_RETURNED,
            Reservation.STATUS_CANCELLED,
        ],
    )
    total = qs.count()
    if total == 0:
        return 100
    returned = qs.filter(status=Reservation.STATUS_RETURNED).count()
    return round((returned / total) * 100)


# ---------------------------------------------------------------------------
# Loyalty discount tiers
# ---------------------------------------------------------------------------

DISCOUNT_TIERS = [
    (90, Decimal("0.15"), "15% loyalty discount"),
    (75, Decimal("0.10"), "10% loyalty discount"),
    (50, Decimal("0.05"), "5% loyalty discount"),
    (0,  Decimal("0.00"), "No discount yet"),
]


def loyalty_discount(score: int) -> tuple[Decimal, str]:
    """Returns (discount_rate, label) for a given reliability score."""
    for threshold, rate, label in DISCOUNT_TIERS:
        if score >= threshold:
            return rate, label
    return Decimal("0.00"), "No discount yet"


def apply_discount(amount: Decimal, score: int) -> tuple[Decimal, Decimal, str]:
    """
    Returns (discounted_amount, discount_amount, label).
    """
    rate, label = loyalty_discount(score)
    discount_amount = (amount * rate).quantize(Decimal("0.01"))
    return amount - discount_amount, discount_amount, label

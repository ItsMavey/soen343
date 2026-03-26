import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Vehicle, Car, Reservation, Notification
from .pricing import StandardPricing, WeekendPricing, SurgePricing
from .states import AvailableState, ReservedState, MaintenanceState, InvalidTransitionError
from .sustainability import reliability_score, co2_saved_kg, loyalty_discount, apply_discount

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="testuser", role="COMMUTER"):
    return User.objects.create_user(
        username=username, password="pass", email=f"{username}@test.com", role=role
    )


def make_car(make="Toyota", model="Corolla", year=2022, daily_rate="50.00", fuel_type="GASOLINE"):
    return Car.objects.create(
        make=make, model=model, year=year,
        daily_rate=Decimal(daily_rate),
        fuel_type=fuel_type,
        vehicle_kind=Vehicle.KIND_CAR,
    )


def make_reservation(user, vehicle, start_offset=1, days=3, status=Reservation.STATUS_CONFIRMED):
    today = timezone.localdate()
    start = today + datetime.timedelta(days=start_offset)
    end = start + datetime.timedelta(days=days - 1)
    return Reservation.objects.create(
        user=user, vehicle=vehicle,
        start_date=start, end_date=end,
        total_amount=vehicle.daily_rate * days,
        status=status,
    )


# ---------------------------------------------------------------------------
# Strategy Pattern — Pricing
# ---------------------------------------------------------------------------

def _dates(days):
    """Return (start, end) date pair spanning `days` days starting 2024-01-01."""
    start = datetime.date(2024, 1, 1)
    end = start + datetime.timedelta(days=days - 1)
    return start, end


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


# ---------------------------------------------------------------------------
# State Pattern — Vehicle lifecycle
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sustainability / Gamification
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Observer Pattern — Notifications
# ---------------------------------------------------------------------------

class ObserverNotificationTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.commuter = make_user("commuter", role="COMMUTER")
        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()

    def test_maintenance_creates_notification(self):
        make_user("admin", role="ADMIN")
        self.car.send_to_maintenance()
        self.assertTrue(Notification.objects.filter(event_type="MAINTENANCE").exists())

    def test_available_after_maintenance_notifies_commuter(self):
        make_reservation(self.commuter, self.car, status=Reservation.STATUS_CONFIRMED)
        self.car.send_to_maintenance()
        self.car.complete_maintenance()
        self.assertTrue(
            Notification.objects.filter(user=self.commuter, event_type="AVAILABLE").exists()
        )

    def test_returned_creates_notification(self):
        make_user("admin_user", role="ADMIN")
        self.car._notify_observers("RETURNED")
        self.assertTrue(Notification.objects.filter(event_type="RETURNED").exists())


# ---------------------------------------------------------------------------
# Overdue detection
# ---------------------------------------------------------------------------

class OverdueTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.car = make_car()

    def _make_overdue(self):
        today = timezone.localdate()
        past = today - datetime.timedelta(days=2)
        return Reservation.objects.create(
            user=self.user, vehicle=self.car,
            start_date=past - datetime.timedelta(days=1),
            end_date=past,
            total_amount=Decimal("100.00"),
            status=Reservation.STATUS_CONFIRMED,
        )

    def test_overdue_reservation_detected(self):
        r = self._make_overdue()
        self.assertLess(r.end_date, timezone.localdate())
        self.assertEqual(r.status, Reservation.STATUS_CONFIRMED)

    def test_fire_overdue_notifications_creates_notification(self):
        from .observers import fire_overdue_notifications
        r = self._make_overdue()
        fire_overdue_notifications([r])
        self.assertTrue(
            Notification.objects.filter(reservation=r, event_type="OVERDUE", user=self.user).exists()
        )

    def test_fire_overdue_notifications_is_idempotent(self):
        from .observers import fire_overdue_notifications
        r = self._make_overdue()
        fire_overdue_notifications([r])
        fire_overdue_notifications([r])
        count = Notification.objects.filter(
            reservation=r, event_type="OVERDUE", user=self.user
        ).count()
        self.assertEqual(count, 1)

    def test_non_overdue_not_notified(self):
        from .observers import fire_overdue_notifications
        r = make_reservation(self.user, self.car, start_offset=1, status=Reservation.STATUS_CONFIRMED)
        fire_overdue_notifications([r])
        self.assertFalse(
            Notification.objects.filter(reservation=r, event_type="OVERDUE").exists()
        )

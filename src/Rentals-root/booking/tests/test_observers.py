# basic tests
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from booking.models import Reservation, Notification
from booking.observers import fire_overdue_notifications
from .helpers import make_user, make_car, make_reservation


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
        r = self._make_overdue()
        fire_overdue_notifications([r])
        self.assertTrue(
            Notification.objects.filter(reservation=r, event_type="OVERDUE", user=self.user).exists()
        )

    def test_fire_overdue_notifications_is_idempotent(self):
        r = self._make_overdue()
        fire_overdue_notifications([r])
        fire_overdue_notifications([r])
        count = Notification.objects.filter(
            reservation=r, event_type="OVERDUE", user=self.user
        ).count()
        self.assertEqual(count, 1)

    def test_non_overdue_not_notified(self):
        r = make_reservation(self.user, self.car, start_offset=1, status=Reservation.STATUS_CONFIRMED)
        fire_overdue_notifications([r])
        self.assertFalse(
            Notification.objects.filter(reservation=r, event_type="OVERDUE").exists()
        )

"""
Security Tests — Authorization and access control.

Verifies that users cannot access resources belonging to other users,
and that role-based restrictions are enforced on all protected views.
"""
from django.test import TestCase
from django.urls import reverse

from booking.models import Reservation, Vehicle
from .helpers import make_user, make_car, make_reservation


class CrossUserReservationTests(TestCase):
    """Commuter A must not be able to act on Commuter B's reservations."""

    def setUp(self):
        self.user_a = make_user("user_a")
        self.user_b = make_user("user_b")
        self.car = make_car()
        self.res = make_reservation(self.user_a, self.car, status=Reservation.STATUS_PENDING)
        self.client.force_login(self.user_b)

    def test_cannot_view_payment_page(self):
        response = self.client.get(reverse("reservation_payment", args=[self.res.id]))
        self.assertRedirects(response, reverse("vehicle_list"))

    def test_cannot_post_payment(self):
        self.client.post(reverse("reservation_payment", args=[self.res.id]),
                         {"confirm_payment": True})
        self.res.refresh_from_db()
        self.assertNotEqual(self.res.status, Reservation.STATUS_CONFIRMED)

    def test_cannot_view_detail(self):
        response = self.client.get(reverse("reservation_detail", args=[self.res.id]))
        self.assertRedirects(response, reverse("vehicle_list"))

    def test_cannot_return_vehicle(self):
        self.res.status = Reservation.STATUS_CONFIRMED
        self.res.save()
        self.client.post(reverse("return_vehicle", args=[self.res.id]))
        self.res.refresh_from_db()
        self.assertNotEqual(self.res.status, Reservation.STATUS_RETURNED)

    def test_cannot_cancel_reservation(self):
        self.client.post(reverse("cancel_reservation", args=[self.res.id]))
        self.res.refresh_from_db()
        self.assertNotEqual(self.res.status, Reservation.STATUS_CANCELLED)


class UnauthenticatedAccessTests(TestCase):
    """Unauthenticated users must be redirected to login for all protected URLs."""

    def setUp(self):
        self.user = make_user()
        self.car = make_car()
        self.res = make_reservation(self.user, self.car)

    def _assert_redirects_to_login(self, url):
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 301])
        self.assertIn("/login/", response["Location"])

    def test_vehicle_list_requires_login(self):
        self._assert_redirects_to_login(reverse("vehicle_list"))

    def test_vehicle_detail_requires_login(self):
        self._assert_redirects_to_login(reverse("vehicle_detail", args=[self.car.id]))

    def test_reserve_vehicle_requires_login(self):
        self._assert_redirects_to_login(reverse("reserve_vehicle", args=[self.car.id]))

    def test_my_reservations_requires_login(self):
        self._assert_redirects_to_login(reverse("my_reservations"))

    def test_provider_fleet_requires_login(self):
        self._assert_redirects_to_login(reverse("provider_fleet"))

    def test_analytics_requires_login(self):
        self._assert_redirects_to_login(reverse("rental_analytics"))

    def test_gateway_analytics_requires_login(self):
        self._assert_redirects_to_login(reverse("gateway_analytics"))


class RoleBasedAnalyticsAccessTests(TestCase):
    """Analytics pages must enforce role restrictions."""

    def test_commuter_cannot_access_rental_analytics(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("rental_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_commuter_cannot_access_gateway_analytics(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("gateway_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_provider_cannot_access_gateway_analytics(self):
        provider = make_user("provider", role="PROVIDER")
        self.client.force_login(provider)
        response = self.client.get(reverse("gateway_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)


class CrossProviderFleetTests(TestCase):
    """Provider must not be able to edit or delete another provider's vehicles."""

    def setUp(self):
        self.provider_a = make_user("provider_a", role="PROVIDER")
        self.provider_b = make_user("provider_b", role="PROVIDER")
        self.car = make_car()
        self.car.owner = self.provider_a
        self.car.save()
        self.client.force_login(self.provider_b)

    def test_cannot_edit_other_providers_vehicle(self):
        response = self.client.get(reverse("provider_edit_vehicle", args=[self.car.id]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_providers_vehicle(self):
        self.client.post(reverse("provider_delete_vehicle", args=[self.car.id]))
        self.assertTrue(Vehicle.objects.filter(id=self.car.id).exists())

    def test_cannot_send_other_providers_vehicle_to_maintenance(self):
        self.client.post(reverse("provider_maintenance", args=[self.car.id]))
        self.car.refresh_from_db()
        self.assertNotEqual(self.car.vehicle_status, Vehicle.STATUS_MAINTENANCE)

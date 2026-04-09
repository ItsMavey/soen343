from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from booking.models import Notification
from .helpers import make_user, make_car, make_reservation


class RentalAnalyticsViewTests(TestCase):

    def test_provider_can_access(self):
        provider = make_user("provider", role="PROVIDER")
        self.client.force_login(provider)
        response = self.client.get(reverse("rental_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access(self):
        admin = make_user("admin", role="ADMIN")
        self.client.force_login(admin)
        response = self.client.get(reverse("rental_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_commuter_is_redirected(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("rental_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("rental_analytics"))
        self.assertRedirects(response, f"/login/?next={reverse('rental_analytics')}")


class GatewayAnalyticsViewTests(TestCase):

    @patch("booking.services.analytics_service.TransitFacade")
    @patch("booking.services.analytics_service.ParkingService")
    def test_admin_can_access(self, MockPS, MockTF):
        MockPS.return_value.get_lots.return_value = []
        MockTF.return_value.get_nearby_stops.return_value = []
        admin = make_user("admin", role="ADMIN")
        self.client.force_login(admin)
        response = self.client.get(reverse("gateway_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_provider_is_redirected(self):
        provider = make_user("provider", role="PROVIDER")
        self.client.force_login(provider)
        response = self.client.get(reverse("gateway_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_commuter_is_redirected(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("gateway_analytics"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)


class NotificationsViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()

    def test_returns_200(self):
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)

    def test_marks_notifications_as_read(self):
        Notification.objects.create(
            user=self.user, message="Test", event_type="AVAILABLE", is_read=False
        )
        self.client.get(reverse("notifications"))
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_shows_only_own_notifications(self):
        other = make_user("other")
        Notification.objects.create(user=self.user, message="Mine", event_type="AVAILABLE")
        Notification.objects.create(user=other, message="Theirs", event_type="AVAILABLE")
        response = self.client.get(reverse("notifications"))
        for n in response.context["notifs"]:
            self.assertEqual(n.user, self.user)

    def test_returns_at_most_50_notifications(self):
        for i in range(60):
            Notification.objects.create(
                user=self.user, message=f"msg {i}", event_type="AVAILABLE"
            )
        response = self.client.get(reverse("notifications"))
        self.assertLessEqual(len(response.context["notifs"]), 50)


class MyRewardsViewTests(TestCase):

    def test_commuter_can_access(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("my_rewards"))
        self.assertEqual(response.status_code, 200)

    def test_provider_is_redirected(self):
        provider = make_user("provider", role="PROVIDER")
        self.client.force_login(provider)
        response = self.client.get(reverse("my_rewards"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

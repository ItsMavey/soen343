from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def make_user(username, role="COMMUTER", password="pass"):
    return User.objects.create_user(
        username=username, password=password,
        email=f"{username}@test.com", role=role,
    )


class LoginViewTests(TestCase):

    def setUp(self):
        self.user = make_user("testuser")

    def test_get_returns_200(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser", "password": "pass",
        })
        # login redirects to role_dashboard which itself redirects to the role-specific page
        self.assertEqual(response.status_code, 302)
        self.assertIn("dashboard", response["Location"])

    def test_valid_login_creates_session(self):
        self.client.post(reverse("login"), {"username": "testuser", "password": "pass"})
        self.assertIn("_auth_user_id", self.client.session)

    def test_invalid_password_returns_form_error(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser", "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_user_returns_form_error(self):
        response = self.client.post(reverse("login"), {
            "username": "nobody", "password": "pass",
        })
        self.assertEqual(response.status_code, 200)


class LogoutViewTests(TestCase):

    def setUp(self):
        self.user = make_user("testuser")
        self.client.force_login(self.user)

    def test_post_clears_session(self):
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_not_allowed(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)


class RoleDashboardRoutingTests(TestCase):

    def test_commuter_routed_to_commuter_dashboard(self):
        make_user("commuter", role="COMMUTER")
        self.client.login(username="commuter", password="pass")
        response = self.client.get(reverse("role_dashboard"))
        self.assertRedirects(response, reverse("commuter_dashboard"))

    def test_provider_routed_to_provider_dashboard(self):
        make_user("provider", role="PROVIDER")
        self.client.login(username="provider", password="pass")
        response = self.client.get(reverse("role_dashboard"))
        self.assertRedirects(response, reverse("provider_dashboard"))

    def test_admin_routed_to_city_admin_dashboard(self):
        make_user("admin", role="ADMIN")
        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("role_dashboard"))
        self.assertRedirects(response, reverse("city_admin_dashboard"))


class RoleDashboardAccessControlTests(TestCase):

    def test_commuter_cannot_access_provider_dashboard(self):
        make_user("commuter", role="COMMUTER")
        self.client.login(username="commuter", password="pass")
        response = self.client.get(reverse("provider_dashboard"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_provider_cannot_access_commuter_dashboard(self):
        make_user("provider", role="PROVIDER")
        self.client.login(username="provider", password="pass")
        response = self.client.get(reverse("commuter_dashboard"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_commuter_cannot_access_admin_dashboard(self):
        make_user("commuter", role="COMMUTER")
        self.client.login(username="commuter", password="pass")
        response = self.client.get(reverse("city_admin_dashboard"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)


class RegistrationTests(TestCase):

    VALID_DATA = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "Strongpass123!",
        "confirm_password": "Strongpass123!",
        "role": "COMMUTER",
        "preferred_city": "",
        "preferred_mobility_type": "",
    }

    def test_valid_registration_creates_user(self):
        self.client.post(reverse("register"), self.VALID_DATA)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_valid_registration_redirects_to_success(self):
        response = self.client.post(reverse("register"), self.VALID_DATA)
        self.assertRedirects(response, reverse("registration_success"))

    def test_duplicate_username_shows_form_error(self):
        make_user("newuser")
        response = self.client.post(reverse("register"), self.VALID_DATA)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser", email="newuser@example.com").exists())

    def test_password_mismatch_shows_form_error(self):
        data = {**self.VALID_DATA, "confirm_password": "different123!"}
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_registration_success_page_returns_200(self):
        response = self.client.get(reverse("registration_success"))
        self.assertEqual(response.status_code, 200)

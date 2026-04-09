from django.test import TestCase
from django.urls import reverse

from booking.models import Vehicle
from .helpers import make_user, make_car


class ProviderFleetAccessTests(TestCase):

    def test_provider_can_access_fleet(self):
        provider = make_user("provider", role="PROVIDER")
        self.client.force_login(provider)
        response = self.client.get(reverse("provider_fleet"))
        self.assertEqual(response.status_code, 200)

    def test_commuter_is_redirected(self):
        commuter = make_user("commuter", role="COMMUTER")
        self.client.force_login(commuter)
        response = self.client.get(reverse("provider_fleet"))
        self.assertRedirects(response, reverse("role_dashboard"), target_status_code=302)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("provider_fleet"))
        self.assertRedirects(response, f"/login/?next={reverse('provider_fleet')}")

    def test_fleet_shows_only_own_vehicles(self):
        provider = make_user("provider", role="PROVIDER")
        other = make_user("other_provider", role="PROVIDER")
        car = make_car()
        car.owner = provider
        car.save()
        other_car = make_car(make="Honda", model="Civic")
        other_car.owner = other
        other_car.save()
        self.client.force_login(provider)
        response = self.client.get(reverse("provider_fleet"))
        ids = [v.id for v in response.context["vehicles"]]
        self.assertIn(car.id, ids)
        self.assertNotIn(other_car.id, ids)


class ProviderAddVehicleTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.client.force_login(self.provider)
        self.form_data = {
            "vehicle_kind": "CAR",
            "make": "Toyota",
            "model": "Camry",
            "year": 2023,
            "daily_rate": "60.00",
            "city": "MTL",
            "fuel_type": "GASOLINE",
            "body_style": "Sedan",
        }

    def test_post_creates_vehicle(self):
        self.client.post(reverse("provider_add_vehicle"), self.form_data)
        self.assertEqual(Vehicle.objects.filter(make="Toyota").count(), 1)

    def test_created_vehicle_owned_by_provider(self):
        self.client.post(reverse("provider_add_vehicle"), self.form_data)
        car = Vehicle.objects.get(make="Toyota")
        self.assertEqual(car.owner, self.provider)

    def test_post_redirects_to_fleet(self):
        response = self.client.post(reverse("provider_add_vehicle"), self.form_data)
        self.assertRedirects(response, reverse("provider_fleet"))

    def test_get_returns_200(self):
        response = self.client.get(reverse("provider_add_vehicle"))
        self.assertEqual(response.status_code, 200)


class ProviderEditVehicleTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()
        self.client.force_login(self.provider)

    def test_post_updates_vehicle(self):
        self.client.post(reverse("provider_edit_vehicle", args=[self.car.id]), {
            "vehicle_kind": "CAR",
            "make": "Honda",
            "model": "Civic",
            "year": 2021,
            "daily_rate": "45.00",
            "city": "MTL",
            "fuel_type": "HYBRID",
            "body_style": "Sedan",
        })
        self.car.refresh_from_db()
        self.assertEqual(self.car.make, "Honda")
        self.assertEqual(self.car.model, "Civic")

    def test_other_provider_cannot_edit(self):
        other = make_user("other", role="PROVIDER")
        self.client.force_login(other)
        response = self.client.get(reverse("provider_edit_vehicle", args=[self.car.id]))
        self.assertEqual(response.status_code, 404)


class ProviderDeleteVehicleTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()
        self.client.force_login(self.provider)

    def test_post_deletes_vehicle(self):
        self.client.post(reverse("provider_delete_vehicle", args=[self.car.id]))
        self.assertFalse(Vehicle.objects.filter(id=self.car.id).exists())

    def test_other_provider_cannot_delete(self):
        other = make_user("other", role="PROVIDER")
        self.client.force_login(other)
        self.client.post(reverse("provider_delete_vehicle", args=[self.car.id]))
        self.assertTrue(Vehicle.objects.filter(id=self.car.id).exists())


class ProviderMaintenanceTests(TestCase):

    def setUp(self):
        self.provider = make_user("provider", role="PROVIDER")
        self.car = make_car()
        self.car.owner = self.provider
        self.car.save()
        self.client.force_login(self.provider)

    def test_send_to_maintenance(self):
        self.client.post(reverse("provider_maintenance", args=[self.car.id]))
        self.car.refresh_from_db()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_MAINTENANCE)

    def test_complete_maintenance(self):
        self.car.vehicle_status = Vehicle.STATUS_MAINTENANCE
        self.car.save()
        self.client.post(reverse("provider_complete_maintenance", args=[self.car.id]))
        self.car.refresh_from_db()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_AVAILABLE)

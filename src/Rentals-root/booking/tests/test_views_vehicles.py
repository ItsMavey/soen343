import datetime

from django.test import TestCase
from django.urls import reverse

from booking.models import Vehicle, Reservation
from booking.pricing import SURGE_THRESHOLD
from .helpers import make_user, make_car, make_reservation


class VehicleListViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()

    def test_returns_200(self):
        response = self.client.get(reverse("vehicle_list"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("vehicle_list"))
        self.assertRedirects(response, f"/login/?next={reverse('vehicle_list')}")

    def test_shows_available_vehicles(self):
        response = self.client.get(reverse("vehicle_list"))
        ids = [v.id for v in response.context["vehicles"]]
        self.assertIn(self.car.id, ids)

    def test_filter_by_kind(self):
        response = self.client.get(reverse("vehicle_list"), {"vehicle_kind": "CAR"})
        self.assertEqual(response.status_code, 200)
        for v in response.context["vehicles"]:
            self.assertEqual(v.vehicle_kind, "CAR")

    def test_filter_by_city(self):
        response = self.client.get(reverse("vehicle_list"), {"city": "MTL"})
        self.assertEqual(response.status_code, 200)

    def test_filter_by_max_rate(self):
        expensive = make_car(make="BMW", model="X5", daily_rate="500.00")
        response = self.client.get(reverse("vehicle_list"), {"max_rate": "100"})
        ids = [v.id for v in response.context["vehicles"]]
        self.assertNotIn(expensive.id, ids)
        self.assertIn(self.car.id, ids)

    def test_filter_by_min_rate(self):
        cheap = make_car(make="Fiat", model="500", daily_rate="10.00")
        response = self.client.get(reverse("vehicle_list"), {"min_rate": "30"})
        ids = [v.id for v in response.context["vehicles"]]
        self.assertNotIn(cheap.id, ids)


class VehicleDetailViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()

    def test_returns_200(self):
        response = self.client.get(reverse("vehicle_detail", args=[self.car.id]))
        self.assertEqual(response.status_code, 200)

    def test_invalid_id_returns_404(self):
        response = self.client.get(reverse("vehicle_detail", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_is_surge_false_below_threshold(self):
        response = self.client.get(reverse("vehicle_detail", args=[self.car.id]))
        self.assertFalse(response.context["is_surge"])

    def test_is_surge_true_at_threshold(self):
        commuter = make_user("commuter2")
        today = datetime.date.today()
        for i in range(SURGE_THRESHOLD):
            start = today + datetime.timedelta(days=i + 1)
            end = start + datetime.timedelta(days=1)
            Reservation.objects.create(
                user=commuter, vehicle=self.car,
                start_date=start, end_date=end,
                total_amount=self.car.daily_rate,
                status=Reservation.STATUS_CONFIRMED,
            )
        response = self.client.get(reverse("vehicle_detail", args=[self.car.id]))
        self.assertTrue(response.context["is_surge"])


class ReserveVehicleViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()
        self.start = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        self.end = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()

    def test_get_returns_200(self):
        response = self.client.get(reverse("reserve_vehicle", args=[self.car.id]))
        self.assertEqual(response.status_code, 200)

    def test_post_creates_reservation(self):
        self.client.post(reverse("reserve_vehicle", args=[self.car.id]), {
            "start_date": self.start, "end_date": self.end,
        })
        self.assertEqual(Reservation.objects.filter(user=self.user, vehicle=self.car).count(), 1)

    def test_post_redirects_to_payment(self):
        response = self.client.post(reverse("reserve_vehicle", args=[self.car.id]), {
            "start_date": self.start, "end_date": self.end,
        })
        res = Reservation.objects.get(user=self.user)
        self.assertRedirects(response, reverse("reservation_payment", args=[res.id]))

    def test_post_blocked_when_vehicle_in_maintenance(self):
        self.car.vehicle_status = Vehicle.STATUS_MAINTENANCE
        self.car.save()
        self.client.post(reverse("reserve_vehicle", args=[self.car.id]), {
            "start_date": self.start, "end_date": self.end,
        })
        self.assertEqual(Reservation.objects.count(), 0)

    def test_post_blocked_when_dates_overlap(self):
        make_reservation(self.user, self.car, start_offset=2, days=4,
                         status=Reservation.STATUS_CONFIRMED)
        response = self.client.post(reverse("reserve_vehicle", args=[self.car.id]), {
            "start_date": self.start, "end_date": self.end,
        })
        # Should not create a second reservation
        self.assertEqual(Reservation.objects.count(), 1)

# basic tests
from django.test import TestCase
from django.urls import reverse

from booking.models import Reservation, Vehicle
from .helpers import make_user, make_car, make_reservation


class ReservationPaymentViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()
        self.res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)

    def test_get_returns_200(self):
        response = self.client.get(reverse("reservation_payment", args=[self.res.id]))
        self.assertEqual(response.status_code, 200)

    def test_post_confirms_reservation(self):
        self.client.post(reverse("reservation_payment", args=[self.res.id]),
                         {"confirm_payment": True})
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, Reservation.STATUS_CONFIRMED)

    def test_post_redirects_to_detail(self):
        response = self.client.post(reverse("reservation_payment", args=[self.res.id]),
                                    {"confirm_payment": True})
        self.assertRedirects(response, reverse("reservation_detail", args=[self.res.id]))

    def test_other_user_cannot_access(self):
        other = make_user("other")
        self.client.force_login(other)
        response = self.client.get(reverse("reservation_payment", args=[self.res.id]))
        self.assertRedirects(response, reverse("vehicle_list"))


class ReturnVehicleViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()

    def test_return_confirmed_reservation(self):
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_CONFIRMED)
        self.client.post(reverse("return_vehicle", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_RETURNED)

    def test_return_non_confirmed_has_no_effect(self):
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)
        self.client.post(reverse("return_vehicle", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_PENDING)

    def test_other_user_cannot_return(self):
        other = make_user("other")
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_CONFIRMED)
        self.client.force_login(other)
        self.client.post(reverse("return_vehicle", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CONFIRMED)


class CancelReservationViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.car = make_car()

    def test_cancel_pending_reservation(self):
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)
        self.car.vehicle_status = Vehicle.STATUS_RESERVED
        self.car.save()
        self.client.post(reverse("cancel_reservation", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CANCELLED)

    def test_cancel_releases_vehicle(self):
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)
        self.car.vehicle_status = Vehicle.STATUS_RESERVED
        self.car.save()
        self.client.post(reverse("cancel_reservation", args=[res.id]))
        self.car.refresh_from_db()
        self.assertEqual(self.car.vehicle_status, Vehicle.STATUS_AVAILABLE)

    def test_cannot_cancel_confirmed_reservation(self):
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_CONFIRMED)
        self.client.post(reverse("cancel_reservation", args=[res.id]))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.STATUS_CONFIRMED)

    def test_other_user_cannot_cancel(self):
        other = make_user("other")
        res = make_reservation(self.user, self.car, status=Reservation.STATUS_PENDING)
        self.client.force_login(other)
        self.client.post(reverse("cancel_reservation", args=[res.id]))
        res.refresh_from_db()
        self.assertNotEqual(res.status, Reservation.STATUS_CANCELLED)


class MyReservationsViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.other = make_user("other")
        self.client.force_login(self.user)
        self.car = make_car()

    def test_returns_200(self):
        response = self.client.get(reverse("my_reservations"))
        self.assertEqual(response.status_code, 200)

    def test_shows_only_own_reservations(self):
        own_res = make_reservation(self.user, self.car)
        other_res = make_reservation(self.other, self.car, start_offset=10)
        response = self.client.get(reverse("my_reservations"))
        reservations = list(response.context["reservations"])
        self.assertIn(own_res, reservations)
        self.assertNotIn(other_res, reservations)

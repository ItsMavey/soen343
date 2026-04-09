from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from booking.models import Reservation
from booking.services.rewards_service import RewardsService
from .helpers import make_car, make_reservation, make_user


class RewardsServiceTests(TestCase):

    @patch("booking.services.rewards_service.co2_saved_kg", side_effect=[4.2, 6.3])
    @patch("booking.services.rewards_service.total_co2_saved", return_value=10.5)
    @patch("booking.services.rewards_service.loyalty_discount", return_value=(0.15, "15% off"))
    @patch("booking.services.rewards_service.reliability_score", return_value=85)
    def test_rewards_context_includes_only_returned_rentals_and_active_tier(
        self, _mock_score, _mock_discount, _mock_total_co2, mock_saved_kg
    ):
        user = make_user("rewards-user")
        car = make_car(daily_rate="25.00")

        older = make_reservation(user, car, start_offset=-5, days=2, status=Reservation.STATUS_RETURNED)
        older.returned_at = timezone.now() - timezone.timedelta(days=2)
        older.save(update_fields=["returned_at"])

        newer = make_reservation(user, car, start_offset=-2, days=3, status=Reservation.STATUS_RETURNED)
        newer.returned_at = timezone.now() - timezone.timedelta(days=1)
        newer.save(update_fields=["returned_at"])

        make_reservation(user, car, start_offset=1, days=1, status=Reservation.STATUS_PENDING)

        context = RewardsService.get_user_rewards(user)

        self.assertEqual(context["score"], 85)
        self.assertEqual(context["discount_rate"], 15)
        self.assertEqual(context["discount_label"], "15% off")
        self.assertEqual(context["co2_saved"], 10.5)
        self.assertEqual(context["total_res"], 2)
        self.assertEqual(context["returned_count"], 2)
        self.assertEqual(len(context["rental_co2"]), 2)
        self.assertEqual(context["rental_co2"][0]["reservation"].id, newer.id)
        self.assertEqual(context["rental_co2"][0]["days"], 3)
        self.assertEqual(context["rental_co2"][0]["saved"], 4.2)
        self.assertEqual(context["rental_co2"][1]["reservation"].id, older.id)
        self.assertEqual(context["rental_co2"][1]["days"], 2)
        self.assertEqual(context["rental_co2"][1]["saved"], 6.3)
        self.assertEqual(mock_saved_kg.call_count, 2)

        active_tiers = [tier for tier in context["tiers"] if tier["active"]]
        self.assertEqual(len(active_tiers), 1)
        self.assertEqual(active_tiers[0]["rate"], 10)

    @patch("booking.services.rewards_service.co2_saved_kg")
    @patch("booking.services.rewards_service.total_co2_saved", return_value=0)
    @patch("booking.services.rewards_service.loyalty_discount", return_value=(0, "No discount"))
    @patch("booking.services.rewards_service.reliability_score", return_value=0)
    def test_rewards_context_handles_user_with_no_completed_rentals(
        self, _mock_score, _mock_discount, _mock_total_co2, mock_saved_kg
    ):
        user = make_user("new-user")

        context = RewardsService.get_user_rewards(user)

        self.assertEqual(context["total_res"], 0)
        self.assertEqual(context["returned_count"], 0)
        self.assertEqual(context["rental_co2"], [])
        self.assertFalse(any(tier["active"] for tier in context["tiers"]))
        mock_saved_kg.assert_not_called()

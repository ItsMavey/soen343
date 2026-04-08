"""
Rewards service.

Wraps sustainability.py into a single cohesive service. Views call
get_user_rewards() and receive a complete context dict.
"""
from ..models import Reservation
from ..sustainability import (
    reliability_score, total_co2_saved, loyalty_discount,
    co2_saved_kg, DISCOUNT_TIERS,
)


class RewardsService:

    @staticmethod
    def get_user_rewards(user) -> dict:
        """
        Compute all gamification data for a commuter's rewards page.
        Returns a dict ready to pass directly to the template.
        """
        score = reliability_score(user)
        discount_rate, discount_label = loyalty_discount(score)
        co2 = total_co2_saved(user)

        returned = Reservation.objects.filter(
            user=user, status=Reservation.STATUS_RETURNED
        ).select_related("vehicle").order_by("-returned_at")

        rental_co2 = [
            {
                "reservation": r,
                "days": (r.end_date - r.start_date).days + 1,
                "saved": co2_saved_kg(r.vehicle, (r.end_date - r.start_date).days + 1),
            }
            for r in returned
        ]

        total_res = Reservation.objects.filter(user=user).exclude(
            status=Reservation.STATUS_PENDING
        ).count()

        tiers = [
            {
                "threshold": t,
                "rate": int(r * 100),
                "label": l,
                "active": score >= t and (score < DISCOUNT_TIERS[i - 1][0] if i > 0 else True),
            }
            for i, (t, r, l) in enumerate(DISCOUNT_TIERS) if t > 0
        ]

        return {
            "score": score,
            "discount_rate": int(discount_rate * 100),
            "discount_label": discount_label,
            "co2_saved": co2,
            "rental_co2": rental_co2,
            "total_res": total_res,
            "returned_count": returned.count(),
            "tiers": tiers,
        }

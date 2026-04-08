from .vehicle_views import vehicle_list, vehicle_detail, reserve_vehicle
from .reservation_views import (
    reservation_payment, reservation_detail, return_vehicle,
    my_reservations, cancel_reservation,
)
from .provider_views import (
    provider_fleet, provider_add_vehicle, provider_edit_vehicle,
    provider_maintenance, provider_complete_maintenance, provider_delete_vehicle,
)
from .external_views import parking, transit
from .analytics_views import rental_analytics, gateway_analytics, notifications, my_rewards

__all__ = [
    "vehicle_list", "vehicle_detail", "reserve_vehicle",
    "reservation_payment", "reservation_detail", "return_vehicle",
    "my_reservations", "cancel_reservation",
    "provider_fleet", "provider_add_vehicle", "provider_edit_vehicle",
    "provider_maintenance", "provider_complete_maintenance", "provider_delete_vehicle",
    "parking", "transit",
    "rental_analytics", "gateway_analytics", "notifications", "my_rewards",
]

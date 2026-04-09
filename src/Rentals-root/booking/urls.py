from django.urls import path

from . import views

urlpatterns = [
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("vehicles/<int:vehicle_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:vehicle_id>/reserve/", views.reserve_vehicle, name="reserve_vehicle"),
    path("reservations/", views.my_reservations, name="my_reservations"),
    path("reservations/<int:reservation_id>/", views.reservation_detail, name="reservation_detail"),
    path("reservations/<int:reservation_id>/payment/", views.reservation_payment, name="reservation_payment"),
    path("reservations/<int:reservation_id>/return/", views.return_vehicle, name="return_vehicle"),
    path("reservations/<int:reservation_id>/cancel/", views.cancel_reservation, name="cancel_reservation"),

    # External services
    path("parking/", views.parking, name="parking"),
    path("parking/nearby/", views.parking_nearby, name="parking_nearby"),
    path("transit/", views.transit, name="transit"),
    path("transit/nearby/", views.transit_nearby, name="transit_nearby"),
    path("map/", views.map_view, name="map"),
    path("map/data/", views.map_data, name="map_data"),
    path("trip/", views.trip_view, name="trip"),
    path("trip/plan/", views.trip_plan, name="trip_plan"),

    # Analytics
    path("analytics/rentals/", views.rental_analytics, name="rental_analytics"),
    path("analytics/gateway/", views.gateway_analytics, name="gateway_analytics"),

    # Notifications
    path("notifications/", views.notifications, name="notifications"),

    # Gamification
    path("my-rewards/", views.my_rewards, name="my_rewards"),

    # Provider fleet management
    path("provider/fleet/", views.provider_fleet, name="provider_fleet"),
    path("provider/fleet/add/", views.provider_add_vehicle, name="provider_add_vehicle"),
    path("provider/fleet/<int:vehicle_id>/edit/", views.provider_edit_vehicle, name="provider_edit_vehicle"),
    path("provider/fleet/<int:vehicle_id>/delete/", views.provider_delete_vehicle, name="provider_delete_vehicle"),
    path("provider/fleet/<int:vehicle_id>/maintenance/", views.provider_maintenance, name="provider_maintenance"),
    path("provider/fleet/<int:vehicle_id>/maintenance/complete/", views.provider_complete_maintenance, name="provider_complete_maintenance"),
]

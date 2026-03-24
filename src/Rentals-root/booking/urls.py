from django.urls import path

from . import views

urlpatterns = [
    path("cars/", views.car_list, name="car_list"),
    path("cars/<int:car_id>/", views.car_detail, name="car_detail"),
    path("cars/<int:car_id>/reserve/", views.reserve_car, name="reserve_car"),
    path("reservations/<int:reservation_id>/", views.reservation_detail, name="reservation_detail"),
    path(
        "reservations/<int:reservation_id>/payment/",
        views.reservation_payment,
        name="reservation_payment",
    ),
    path(
        "reservations/<int:reservation_id>/return/",
        views.return_vehicle,
        name="return_vehicle",
    ),
    path("reservations/", views.my_reservations, name="my_reservations"),
    path(
        "reservations/<int:reservation_id>/cancel/",
        views.cancel_reservation,
        name="cancel_reservation",
    ),
]

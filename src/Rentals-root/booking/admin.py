from django.contrib import admin

from .models import Vehicle, Car, Bike, Scooter, Reservation


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "vehicle_kind", "daily_rate", "vehicle_status", "provider")
    list_filter = ("vehicle_kind", "vehicle_status", "provider")
    search_fields = ("make", "model", "year")
    list_editable = ("vehicle_status", "daily_rate")
    list_per_page = 50


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "fuel_type", "body_style", "daily_rate", "vehicle_status")
    list_filter = ("fuel_type", "vehicle_status")
    search_fields = ("make", "model")
    list_editable = ("vehicle_status", "daily_rate")
    list_per_page = 50


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "bike_type", "has_motor", "daily_rate", "vehicle_status")
    list_filter = ("bike_type", "has_motor", "vehicle_status")
    search_fields = ("make", "model")
    list_editable = ("vehicle_status", "daily_rate")


@admin.register(Scooter)
class ScooterAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "engine_cc", "is_electric", "daily_rate", "vehicle_status")
    list_filter = ("is_electric", "vehicle_status")
    search_fields = ("make", "model")
    list_editable = ("vehicle_status", "daily_rate")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "vehicle", "start_date", "end_date", "status", "total_amount")
    list_filter = ("status", "start_date", "end_date", "vehicle__vehicle_kind")
    search_fields = ("user__username", "vehicle__make", "vehicle__model")

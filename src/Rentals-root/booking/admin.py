# rentals/admin.py
from django.contrib import admin
from .models import Car, Reservation


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'daily_rate', 'fuel_type', 'is_available')

    list_filter = ('make', 'fuel_type', 'is_available', 'year')

    search_fields = ('make', 'model', 'year')

    list_editable = ('is_available', 'daily_rate')

    list_per_page = 50


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "car", "start_date", "end_date", "status", "total_amount")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("user__username", "car__make", "car__model")
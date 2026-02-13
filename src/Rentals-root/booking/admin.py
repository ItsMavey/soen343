# rentals/admin.py
from django.contrib import admin
from .models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'daily_rate', 'fuel_type', 'is_available')

    list_filter = ('make', 'fuel_type', 'is_available', 'year')

    search_fields = ('make', 'model', 'year')

    list_editable = ('is_available', 'daily_rate')

    list_per_page = 50
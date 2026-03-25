import datetime

from django import forms

from .models import Vehicle, Car, Bike, Scooter


class VehicleSearchForm(forms.Form):
    query = forms.CharField(required=False, label="Search")
    vehicle_kind = forms.ChoiceField(
        required=False,
        choices=[("", "All Types")] + Vehicle.KIND_CHOICES,
    )
    fuel_type = forms.CharField(required=False, label="Fuel (cars only)")
    min_rate = forms.DecimalField(required=False, min_value=0)
    max_rate = forms.DecimalField(required=False, min_value=0)


class ReservationForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]
        if start_date < datetime.date.today():
            raise forms.ValidationError("Start date cannot be in the past.")
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be on or after start date.")
        return cleaned_data


class PaymentForm(forms.Form):
    confirm_payment = forms.BooleanField(required=True, label="I confirm this simulated payment")


class ProviderVehicleForm(forms.Form):
    # Common fields
    vehicle_kind = forms.ChoiceField(choices=Vehicle.KIND_CHOICES, label="Type")
    make = forms.CharField(max_length=50)
    model = forms.CharField(max_length=100)
    year = forms.IntegerField(min_value=1900, max_value=datetime.date.today().year + 1)
    daily_rate = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0)

    # Car fields
    fuel_type = forms.ChoiceField(choices=Car.FUEL_CHOICES, required=False)
    body_style = forms.CharField(max_length=50, required=False, label="Body Style (e.g. SUV, Sedan)")

    # Bike fields
    bike_type = forms.ChoiceField(choices=Bike.BIKE_TYPE_CHOICES, required=False)
    has_motor = forms.BooleanField(required=False, label="Has Motor (E-Bike)")

    # Scooter fields
    engine_cc = forms.IntegerField(min_value=1, required=False, initial=50, label="Engine (cc)")
    is_electric = forms.BooleanField(required=False, label="Electric Scooter")

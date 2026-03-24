import datetime

from django import forms


class CarSearchForm(forms.Form):
    query = forms.CharField(required=False, label="Search")
    vehicle_type = forms.CharField(required=False)
    fuel_type = forms.CharField(required=False)
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

# form setup
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Password must be at least 8 characters long.",
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    role = forms.ChoiceField(
        choices=[
            (User.ROLE_COMMUTER, "Commuter"),
            (User.ROLE_PROVIDER, "Mobility Provider"),
        ],
        initial=User.ROLE_COMMUTER,
        label="I am a",
    )

    preferred_city = forms.ChoiceField(
        choices=[("", "Select a city (optional)")] + User.CITY_CHOICES,
        required=False,
        label="Preferred city",
    )

    preferred_mobility_type = forms.ChoiceField(
        choices=[("", "Select a type (optional)")] + User.MOBILITY_CHOICES,
        required=False,
        label="Preferred mobility type",
    )

    class Meta:
        model = User
        fields = ["username", "email", "role", "preferred_city", "preferred_mobility_type", "password", "confirm_password"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("password", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        user.preferred_city = self.cleaned_data.get("preferred_city", "")
        user.preferred_mobility_type = self.cleaned_data.get("preferred_mobility_type", "")
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

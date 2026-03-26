from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, TemplateView

from .forms import UserRegistrationForm


def role_required(*roles):
    """Restrict a view to users with one of the given roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                return redirect("role_dashboard")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def home(request):
    return render(request, 'users/index.html')


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("role_dashboard")
        form.add_error(None, "Invalid username or password.")

    return render(request, "registration/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def role_dashboard(request):
    """Redirect user to their role-appropriate dashboard."""
    role = request.user.role
    if role == "PROVIDER":
        return redirect("provider_dashboard")
    if role == "ADMIN":
        return redirect("city_admin_dashboard")
    return redirect("commuter_dashboard")


@login_required
def commuter_dashboard(request):
    if not request.user.is_commuter:
        return redirect("role_dashboard")
    from booking.sustainability import reliability_score, total_co2_saved, loyalty_discount
    from booking.models import Vehicle
    score = reliability_score(request.user)
    discount_rate, discount_label = loyalty_discount(score)
    co2 = total_co2_saved(request.user)

    recommendation = None
    pref_city = request.user.preferred_city
    pref_type = request.user.preferred_mobility_type
    if pref_city and pref_type:
        count = Vehicle.objects.filter(city=pref_city, vehicle_kind=pref_type, vehicle_status=Vehicle.STATUS_AVAILABLE).count()
        if count > 0:
            city_label = dict(request.user.CITY_CHOICES).get(pref_city, pref_city)
            kind_label = dict(request.user.MOBILITY_CHOICES).get(pref_type, pref_type) + ("s" if not pref_type.endswith("S") else "")
            recommendation = f"{count} {kind_label} available in {city_label} right now. Reserve one now."

    return render(request, "users/commuter_dashboard.html", {
        "reliability_score": score,
        "discount_label": discount_label,
        "discount_pct": int(discount_rate * 100),
        "co2_saved": co2,
        "recommendation": recommendation,
    })


@login_required
def provider_dashboard(request):
    if not request.user.is_provider:
        return redirect("role_dashboard")
    return render(request, "users/provider_dashboard.html")


@login_required
def city_admin_dashboard(request):
    if not request.user.is_city_admin:
        return redirect("role_dashboard")
    from django.db.models import Count
    from django.utils import timezone
    from booking.models import Notification, Vehicle, Reservation
    from django.contrib.auth import get_user_model
    UserModel = get_user_model()

    today = timezone.now().date()
    total_users = UserModel.objects.count()
    trips_today = Reservation.objects.filter(status=Reservation.STATUS_RETURNED, returned_at__date=today).count()
    active_rentals = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).count()

    # Usage by kind
    kind_usage = {
        row["vehicle__vehicle_kind"]: row["cnt"]
        for row in Reservation.objects.values("vehicle__vehicle_kind").annotate(cnt=Count("id"))
    }
    bikes_rented = Reservation.objects.filter(
        vehicle__vehicle_kind=Vehicle.KIND_BIKE, status=Reservation.STATUS_CONFIRMED
    ).count()
    scooters_available = Vehicle.objects.filter(
        vehicle_kind=Vehicle.KIND_SCOOTER, vehicle_status=Vehicle.STATUS_AVAILABLE
    ).count()

    # Active rentals by city
    by_city = list(
        Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED)
        .values("vehicle__city")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    city_labels = dict(Vehicle.CITY_CHOICES)
    for row in by_city:
        row["city_label"] = city_labels.get(row["vehicle__city"], row["vehicle__city"])

    # Kind usage totals for comparison chart
    kind_labels = dict(Vehicle.KIND_CHOICES)
    kind_totals = [
        {"kind": kind_labels.get(k, k), "count": v}
        for k, v in kind_usage.items()
    ]

    recent_activity = Notification.objects.select_related("vehicle").order_by("-created_at")[:10]
    return render(request, "users/city_admin_dashboard.html", {
        "recent_activity": recent_activity,
        "total_users": total_users,
        "trips_today": trips_today,
        "active_rentals": active_rentals,
        "bikes_rented": bikes_rented,
        "scooters_available": scooters_available,
        "by_city": by_city,
        "kind_totals": kind_totals,
    })


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("registration_success")


class RegistrationSuccessView(TemplateView):
    template_name = "users/registration_success.html"

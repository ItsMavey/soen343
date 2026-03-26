from functools import wraps

from django.conf import settings
from django.contrib import messages
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
    from booking.services import ParkingService
    from django.contrib.auth import get_user_model
    UserModel = get_user_model()

    today = timezone.localdate()
    city_labels = dict(Vehicle.CITY_CHOICES)

    # --- Tile counts ---
    total_users = UserModel.objects.count()
    active_rentals = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).count()
    trips_today = Reservation.objects.filter(status=Reservation.STATUS_RETURNED, returned_at__date=today).count()
    bikes_rented   = Reservation.objects.filter(vehicle__vehicle_kind=Vehicle.KIND_BIKE,    status=Reservation.STATUS_CONFIRMED).count()
    scooters_rented = Reservation.objects.filter(vehicle__vehicle_kind=Vehicle.KIND_SCOOTER, status=Reservation.STATUS_CONFIRMED).count()

    # --- Detail: 10 most recent users ---
    recent_users = list(UserModel.objects.order_by("-date_joined")[:10].values(
        "username", "email", "role", "date_joined"
    ))
    role_map = {r[0]: r[1] for r in UserModel.ROLE_CHOICES}
    for u in recent_users:
        u["role_label"] = role_map.get(u["role"], u["role"])

    # --- Detail: active rentals list (with city filter) ---
    city_filter = request.GET.get("city_filter", "")
    active_qs = Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED).select_related("vehicle", "user")
    if city_filter:
        active_qs = active_qs.filter(vehicle__city=city_filter)
    active_list = [
        {
            "id": r.id,
            "user": r.user.get_full_name() or r.user.username,
            "vehicle": r.vehicle.display_name(),
            "city": city_labels.get(r.vehicle.city, r.vehicle.city),
            "start": r.start_date,
            "end": r.end_date,
            "overdue": r.end_date < today,
        }
        for r in active_qs.order_by("-created_at")[:50]
    ]
    overdue_active = sum(1 for r in active_list if r["overdue"])

    # --- Detail: trips completed today ---
    trips_today_list = [
        {
            "id": r.id,
            "user": r.user.get_full_name() or r.user.username,
            "vehicle": r.vehicle.display_name(),
            "city": city_labels.get(r.vehicle.city, r.vehicle.city),
            "returned_at": r.returned_at,
        }
        for r in Reservation.objects.filter(
            status=Reservation.STATUS_RETURNED, returned_at__date=today
        ).select_related("vehicle", "user").order_by("-returned_at")
    ]

    # --- Detail: parking utilization by city ---
    lots = ParkingService().get_lots()
    city_parking = {}
    for lot in lots:
        c = lot.city
        if c not in city_parking:
            city_parking[c] = {"city_label": city_labels.get(c, c), "total": 0, "available": 0}
        city_parking[c]["total"] += lot.total_spots
        city_parking[c]["available"] += lot.available_spots
    for cp in city_parking.values():
        occupied = cp["total"] - cp["available"]
        cp["occupancy_pct"] = round(occupied / cp["total"] * 100) if cp["total"] else 0
    parking_by_city = sorted(city_parking.values(), key=lambda x: -x["occupancy_pct"])

    # --- Detail: active rentals by city (for existing table) ---
    by_city = list(
        Reservation.objects.filter(status=Reservation.STATUS_CONFIRMED)
        .values("vehicle__city").annotate(cnt=Count("id")).order_by("-cnt")
    )
    for row in by_city:
        row["city_label"] = city_labels.get(row["vehicle__city"], row["vehicle__city"])

    recent_activity = Notification.objects.select_related("vehicle").order_by("-created_at")[:10]
    return render(request, "users/city_admin_dashboard.html", {
        "recent_activity": recent_activity,
        "total_users": total_users,
        "active_rentals": active_rentals,
        "trips_today": trips_today,
        "bikes_rented": bikes_rented,
        "scooters_rented": scooters_rented,
        "recent_users": recent_users,
        "active_list": active_list,
        "city_filter": city_filter,
        "city_choices": Vehicle.CITY_CHOICES,
        "trips_today_list": trips_today_list,
        "parking_by_city": parking_by_city,
        "by_city": by_city,
        "overdue_active": overdue_active,
    })


@login_required
def profile_settings(request):
    user = request.user
    if request.method == "POST":
        user.preferred_city = request.POST.get("preferred_city", "")
        user.preferred_mobility_type = request.POST.get("preferred_mobility_type", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save(update_fields=["preferred_city", "preferred_mobility_type", "first_name", "last_name"])
        messages.success(request, "Settings saved.")
        return redirect("profile_settings")
    return render(request, "users/profile_settings.html", {"user": user})


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("registration_success")


class RegistrationSuccessView(TemplateView):
    template_name = "users/registration_success.html"

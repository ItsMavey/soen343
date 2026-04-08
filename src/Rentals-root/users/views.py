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

from .dashboard_service import DashboardService
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
        user = authenticate(
            request,
            username=form.cleaned_data.get("username"),
            password=form.cleaned_data.get("password"),
        )
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
    context = DashboardService.get_commuter_context(request.user)
    return render(request, "users/commuter_dashboard.html", context)


@login_required
def provider_dashboard(request):
    if not request.user.is_provider:
        return redirect("role_dashboard")
    return render(request, "users/provider_dashboard.html")


@login_required
def city_admin_dashboard(request):
    if not request.user.is_city_admin:
        return redirect("role_dashboard")
    city_filter = request.GET.get("city_filter", "")
    context = DashboardService.get_admin_context(city_filter=city_filter)
    return render(request, "users/city_admin_dashboard.html", context)


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

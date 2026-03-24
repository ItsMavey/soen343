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
    return redirect("vehicle_list")


@login_required
def provider_dashboard(request):
    if not request.user.is_provider:
        return redirect("role_dashboard")
    return render(request, "users/provider_dashboard.html")


@login_required
def city_admin_dashboard(request):
    if not request.user.is_city_admin:
        return redirect("role_dashboard")
    return render(request, "users/city_admin_dashboard.html")


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("registration_success")


class RegistrationSuccessView(TemplateView):
    template_name = "users/registration_success.html"

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, TemplateView

from .forms import UserRegistrationForm


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
            return redirect(settings.LOGIN_REDIRECT_URL)
        form.add_error(None, "Invalid username or password.")

    return render(request, "registration/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("registration_success")


class RegistrationSuccessView(TemplateView):
    template_name = "users/registration_success.html"
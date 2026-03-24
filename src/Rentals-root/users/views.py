from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import UserRegistrationForm


def home(request):
    return render(request, 'users/index.html')


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("registration_success")


class RegistrationSuccessView(TemplateView):
    template_name = "users/registration_success.html"
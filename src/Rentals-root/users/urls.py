from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "register/success/",
        views.RegistrationSuccessView.as_view(),
        name="registration_success",
    ),
]
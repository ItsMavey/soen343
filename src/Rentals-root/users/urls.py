# routes
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/success/", views.RegistrationSuccessView.as_view(), name="registration_success"),
    path("dashboard/", views.role_dashboard, name="role_dashboard"),
    path("commuter/", views.commuter_dashboard, name="commuter_dashboard"),
    path("provider/", views.provider_dashboard, name="provider_dashboard"),
    path("city-admin/", views.city_admin_dashboard, name="city_admin_dashboard"),
    path("settings/", views.profile_settings, name="profile_settings"),
]
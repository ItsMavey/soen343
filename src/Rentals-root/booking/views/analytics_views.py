from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import Notification
from ..services import AnalyticsService, RewardsService


@login_required
def rental_analytics(request):
    if not (request.user.is_provider or request.user.is_city_admin):
        messages.error(request, "Access restricted.")
        return redirect("role_dashboard")
    context = AnalyticsService.get_rental_dashboard(request.user)
    return render(request, "booking/rental_analytics.html", context)


@login_required
def gateway_analytics(request):
    if not request.user.is_city_admin:
        messages.error(request, "Access restricted to City Admins.")
        return redirect("role_dashboard")
    context = AnalyticsService.get_gateway_dashboard()
    return render(request, "booking/gateway_analytics.html", context)


@login_required
def notifications(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    notifs = Notification.objects.filter(user=request.user).select_related("vehicle")[:50]
    return render(request, "booking/notifications.html", {"notifs": notifs})


@login_required
def my_rewards(request):
    if not request.user.is_commuter:
        return redirect("role_dashboard")
    context = RewardsService.get_user_rewards(request.user)
    return render(request, "booking/my_rewards.html", context)

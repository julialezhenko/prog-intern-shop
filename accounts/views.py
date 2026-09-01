from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render

from sales.models import Order

from .forms import ProfileForm, RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.groups.add(Group.objects.get_or_create(name="Customer")[0])
        login(request, user)
        messages.success(request, f"Welcome to the store, {user.username}!")
        return redirect(request.GET.get("next") or "storefront")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    orders = Order.objects.filter(customer=request.user).order_by("-created_at")[:5]
    return render(request, "accounts/profile.html", {"form": form, "orders": orders})

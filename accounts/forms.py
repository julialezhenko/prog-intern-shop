from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from sales.forms import COUNTRIES

from .models import CustomerProfile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    country = forms.ChoiceField(choices=[(c, c) for c in COUNTRIES], initial="Spain")
    city = forms.CharField(max_length=80, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, country=self.cleaned_data["country"],
                                           city=self.cleaned_data.get("city", ""), acquisition_source="direct")
        return user


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    country = forms.ChoiceField(choices=[(c, c) for c in COUNTRIES])
    city = forms.CharField(max_length=80, required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        profile = getattr(user, "customer_profile", None)
        kwargs.setdefault("initial", {
            "first_name": user.first_name, "last_name": user.last_name, "email": user.email,
            "country": getattr(profile, "country", "") or "Spain", "city": getattr(profile, "city", ""),
        })
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def save(self):
        data = self.cleaned_data
        self.user.first_name, self.user.last_name, self.user.email = data["first_name"], data["last_name"], data["email"]
        self.user.save(update_fields=["first_name", "last_name", "email"])
        CustomerProfile.objects.update_or_create(user=self.user, defaults={"country": data["country"], "city": data["city"]})
        return self.user

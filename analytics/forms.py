"""Admin-facing form for the test-data generator."""
import datetime as dt

from django import forms

from .generation.config import MAX_ORDERS_PER_USER, MAX_USERS, GeneratorConfig

USER_PRESETS = [10, 100, 500, 1000, 5000]


class GenerateTestDataForm(forms.Form):
    """Everything an administrator can choose before a generation run."""

    users = forms.IntegerField(
        min_value=1, max_value=MAX_USERS, initial=500, label="Number of users",
        help_text=f"Any number from 1 to {MAX_USERS:,}; the buttons above are shortcuts.",
        widget=forms.NumberInput(attrs={"class": "vIntegerField", "id": "id_users"}))
    min_orders_per_user = forms.IntegerField(
        min_value=0, max_value=MAX_ORDERS_PER_USER, initial=0, label="Minimum orders per user")
    max_orders_per_user = forms.IntegerField(
        min_value=0, max_value=MAX_ORDERS_PER_USER, initial=12, label="Maximum orders per user",
        help_text="The actual count per customer is drawn from a long-tailed distribution between these two bounds.")
    date_from = forms.DateField(
        label="Period from", widget=forms.DateInput(attrs={"type": "date"}),
        initial=lambda: dt.date.today() - dt.timedelta(days=540))
    date_to = forms.DateField(
        label="Period to", widget=forms.DateInput(attrs={"type": "date"}), initial=dt.date.today)
    seed = forms.IntegerField(
        required=False, initial=12345, label="Random seed",
        help_text="The same seed with the same settings reproduces the same dataset. Leave empty for a random one.")
    include_dirty_data = forms.BooleanField(
        required=False, label="Include realistic data quality issues",
        help_text="Missing cities, absent UTM tags, inconsistent capitalisation, near-duplicate customers, "
                  "double-submitted orders. Never breaks a database constraint.")
    generate_events = forms.BooleanField(
        required=False, initial=True, label="Generate behavioural events",
        help_text="Sessions, product views, add-to-cart and checkout steps, so funnel analysis is possible.")
    generate_subscriptions = forms.BooleanField(required=False, initial=True, label="Generate subscriptions")
    label = forms.CharField(required=False, max_length=120, label="Batch label",
                            help_text="Shown in the batch list, e.g. 'Cohort exercise, group B'.")

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        config = GeneratorConfig(
            users=data["users"], min_orders_per_user=data["min_orders_per_user"],
            max_orders_per_user=data["max_orders_per_user"], date_from=data["date_from"], date_to=data["date_to"],
            seed=data.get("seed"), include_dirty_data=data.get("include_dirty_data", False),
            generate_events=data.get("generate_events", True),
            generate_subscriptions=data.get("generate_subscriptions", True), label=data.get("label", ""))
        config.clean()  # raises ValidationError, which the admin renders next to the offending field
        self.config = config
        return data

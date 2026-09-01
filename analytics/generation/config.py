"""Validated generator settings."""
import datetime as dt
from dataclasses import dataclass, field, asdict

from django.core.exceptions import ValidationError

MAX_USERS = 20_000
MAX_ORDERS_PER_USER = 60
MAX_TOTAL_ORDERS = 400_000


@dataclass
class GeneratorConfig:
    """Everything the administrator can choose, already checked for consistency."""

    users: int = 500
    min_orders_per_user: int = 0
    max_orders_per_user: int = 12
    date_from: dt.date = field(default_factory=lambda: dt.date.today() - dt.timedelta(days=540))
    date_to: dt.date = field(default_factory=dt.date.today)
    seed: int | None = 12345
    include_dirty_data: bool = False
    generate_events: bool = True
    generate_subscriptions: bool = True
    label: str = ""

    def clean(self):
        if self.users < 1:
            raise ValidationError({"users": "Generate at least one user."})
        if self.users > MAX_USERS:
            raise ValidationError({"users": f"At most {MAX_USERS:,} users per run."})
        if self.min_orders_per_user < 0:
            raise ValidationError({"min_orders_per_user": "Cannot be negative."})
        if self.max_orders_per_user < self.min_orders_per_user:
            raise ValidationError({"max_orders_per_user": "Maximum must not be below the minimum."})
        if self.max_orders_per_user > MAX_ORDERS_PER_USER:
            raise ValidationError({"max_orders_per_user": f"At most {MAX_ORDERS_PER_USER} orders per user."})
        if self.date_to < self.date_from:
            raise ValidationError({"date_to": "The end of the period must not be before its start."})
        if self.date_to > dt.date.today() + dt.timedelta(days=365):
            raise ValidationError({"date_to": "The period must not reach more than a year into the future."})
        if self.users * self.max_orders_per_user > MAX_TOTAL_ORDERS:
            raise ValidationError(
                f"users x max orders would exceed {MAX_TOTAL_ORDERS:,} orders; lower one of the two.")
        return self

    @property
    def days(self):
        return (self.date_to - self.date_from).days + 1

    def as_dict(self):
        data = asdict(self)
        data["date_from"] = self.date_from.isoformat()
        data["date_to"] = self.date_to.isoformat()
        return data

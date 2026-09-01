"""Weighted, seasonal and long-tailed random helpers.

Everything is driven by one seeded ``random.Random`` so a run is reproducible.
"""
import datetime as dt
import math
from decimal import Decimal, ROUND_HALF_UP

from . import reference as ref


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Picker:
    """Thin wrapper around ``random.Random`` with the weighted helpers used all over the generator."""

    def __init__(self, rng):
        self.rng = rng

    # --- basics ----------------------------------------------------------------------
    def chance(self, probability):
        return self.rng.random() < probability

    def choice(self, seq):
        return self.rng.choice(seq)

    def weighted(self, pairs):
        """``pairs`` is a sequence of (value, weight); returns one value."""
        values = [p[0] for p in pairs]
        weights = [p[1] for p in pairs]
        return self.rng.choices(values, weights=weights, k=1)[0]

    def row(self, rows, weight_index):
        """Pick a whole tuple from a reference table, weighted by one of its columns."""
        return self.rng.choices(rows, weights=[r[weight_index] for r in rows], k=1)[0]

    def integer(self, low, high):
        return self.rng.randint(low, high)

    def jitter(self, value, spread=0.12):
        return value * (1 + self.rng.uniform(-spread, spread))

    # --- shapes ----------------------------------------------------------------------
    def power_law(self, low, high, exponent=2.4):
        """Long tail: most values sit near ``low``, a few reach ``high``."""
        if high <= low:
            return low
        u = self.rng.random()
        return low + int((high - low) * (u ** exponent))

    def lognormal_factor(self, sigma=0.45):
        """Multiplier centred on 1 with a right tail — realistic for basket sizes."""
        return math.exp(self.rng.gauss(0, sigma))

    def datetime_in_day(self, day: dt.date, tz):
        """A plausible shopping moment: a morning bump, a lunch bump and an evening peak."""
        bucket = self.weighted([((7, 10), 0.18), ((10, 13), 0.22), ((13, 16), 0.16),
                                ((16, 19), 0.17), ((19, 23), 0.24), ((0, 7), 0.03)])
        hour = self.rng.randrange(*bucket)
        naive = dt.datetime.combine(day, dt.time(hour, self.rng.randrange(60), self.rng.randrange(60)))
        return naive.replace(tzinfo=tz)


def demand_factor(day: dt.date, start: dt.date) -> float:
    """How busy a given calendar day is, relative to an average day of the first month."""
    factor = ref.MONTH_FACTOR[day.month] * ref.WEEKDAY_FACTOR[day.weekday()]
    factor *= (1 + ref.MONTHLY_GROWTH) ** ref.month_index(day, start)
    for month, dom, spike in ref.SPIKE_DAYS:
        if day.month == month and day.day == dom:
            factor *= spike
    return factor


def mobile_share(day: dt.date, start: dt.date, end: dt.date) -> float:
    """Mobile traffic keeps taking share over the period."""
    span = max((end - start).days, 1)
    progress = min(max((day - start).days / span, 0.0), 1.0)
    return ref.MOBILE_SHARE_START + (ref.MOBILE_SHARE_END - ref.MOBILE_SHARE_START) * progress


def equipment_appetite(day: dt.date, start: dt.date, end: dt.date) -> float:
    """Brewing gear is a small line at the start of the period and a serious one by the end."""
    span = max((end - start).days, 1)
    progress = min(max((day - start).days / span, 0.0), 1.0)
    return 0.55 + 2.15 * progress ** 1.5


def paid_social_efficiency(day: dt.date, start: dt.date, end: dt.date) -> float:
    """Auction pressure on the social channel: stable for two thirds of the period, then it decays."""
    span = max((end - start).days, 1)
    progress = min(max((day - start).days / span, 0.0), 1.0)
    if progress < 0.62:
        return 1.0
    return 1.0 - 0.55 * ((progress - 0.62) / 0.38)


def carrier_health(carrier: str, day: dt.date, start: dt.date, end: dt.date) -> float:
    """Transit-time multiplier. One carrier's network degrades in the last third of the period."""
    span = max((end - start).days, 1)
    progress = min(max((day - start).days / span, 0.0), 1.0)
    if carrier == "GLS" and progress > 0.66:
        return 1.0 + 1.35 * ((progress - 0.66) / 0.34)
    return 1.0


def seasonal_product_boost(product, day: dt.date) -> float:
    """Iced/cold-brew style coffees sell against the seasonal grain; gift boxes ride it."""
    haystack = f"{product.name} {product.tasting_notes} {product.short_description}".lower()
    summer = day.month in (6, 7, 8)
    if "cold brew" in haystack or "iced" in haystack:
        return 2.6 if summer else 0.55
    if product.kind == "BUNDLE":
        return 2.2 if day.month in (11, 12) else 0.8
    return 1.0

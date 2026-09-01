"""Synthetic customers: auth users, CRM profiles and their attribute history."""
import datetime as dt
import unicodedata

from django.contrib.auth.models import Group, User
from django.utils import timezone

from accounts.models import CustomerProfile, CustomerSegmentHistory

from . import reference as ref
from .distributions import demand_factor, mobile_share
from .persistence import bulk_insert


def _ascii(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


class GeneratedCustomer:
    """A customer plus the traits the order builder needs; kept in memory, never stored as such."""

    __slots__ = ("user", "profile", "channel", "country", "device", "segment", "order_propensity",
                 "basket_factor", "refund_factor", "repeat_factor", "registered_at", "currency")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class UserBuilder:
    """Builds the customer base for one batch."""

    def __init__(self, config, picker, batch):
        self.config = config
        self.pick = picker
        self.batch = batch
        self.tz = timezone.get_current_timezone()
        self._used_usernames = set(
            User.objects.filter(username__contains=".").values_list("username", flat=True))

    # ------------------------------------------------------------------ registration dates
    def _registration_days(self, count):
        """Spread sign-ups over the period, following the same seasonality as demand.

        Weighted towards the start as well: a shop that opens the period with an existing customer
        base produces order volumes that reflect the season rather than the size of the base.
        """
        import math

        days = [self.config.date_from + dt.timedelta(days=i) for i in range(self.config.days)]
        span = max(self.config.days - 1, 1)
        weights = []
        for index, day in enumerate(days):
            tenure = 1 + 3.2 * math.exp(-3.0 * (index / span))
            weights.append(demand_factor(day, self.config.date_from) * tenure)
        return self.pick.rng.choices(days, weights=weights, k=count)

    # ------------------------------------------------------------------ identity
    def _identity(self, first=None, last=None):
        first = first or self.pick.choice(ref.FIRST_NAMES)
        last = last or self.pick.choice(ref.LAST_NAMES)
        stem = f"{_ascii(first)}.{_ascii(last)}".lower().replace(" ", "")
        for _ in range(40):
            username = f"{stem}.{self.pick.integer(10000, 99999)}"
            if username not in self._used_usernames:
                self._used_usernames.add(username)
                return first, last, username
        username = f"{stem}.{self.pick.integer(100000, 999999)}"
        self._used_usernames.add(username)
        return first, last, username

    # ------------------------------------------------------------------ build
    def build(self, progress=None):
        config, pick = self.config, self.pick
        dirty = config.include_dirty_data
        days = self._registration_days(config.users)
        users, drafts = [], []

        index = 0
        while index < config.users:
            registered_on = days[index]
            twin_of = None
            # A small share of the base signs up twice with a slightly different address — the same
            # person from the business point of view, two rows in the database.
            if dirty and drafts and pick.chance(0.015):
                twin_of = drafts[-1]
            if twin_of is not None:
                first, last, username = self._identity(twin_of["first"], twin_of["last"])
                registered_on = min(config.date_to, twin_of["registered_on"] + dt.timedelta(days=pick.integer(1, 60)))
            else:
                first, last, username = self._identity()

            channel = pick.row(ref.CHANNELS, 3)
            country = twin_of["country"] if twin_of else pick.row(ref.COUNTRIES, 4)
            registered_at = pick.datetime_in_day(registered_on, self.tz)
            share = mobile_share(registered_on, config.date_from, config.date_to)
            device = pick.weighted([("mobile", share), ("tablet", ref.TABLET_SHARE),
                                    ("desktop", max(0.05, 1 - share - ref.TABLET_SHARE))])
            segment = pick.weighted(ref.SEGMENTS)

            drafts.append({
                "first": first, "last": last, "username": username, "channel": channel, "country": country,
                "registered_on": registered_on, "registered_at": registered_at, "device": device,
                "segment": segment, "twin_of": twin_of,
            })
            users.append(User(
                username=username, email=f"{username}@{ref.TEST_EMAIL_DOMAIN}",
                first_name=first, last_name=last, date_joined=registered_at,
                is_active=pick.chance(0.965), is_staff=False, is_superuser=False,
                password="!",  # unusable: these accounts can never be logged into
                last_login=registered_at + dt.timedelta(days=pick.integer(0, 200)) if pick.chance(0.55) else None,
            ))
            index += 1
            if progress and index % 500 == 0:
                progress(index)

        created = bulk_insert(User, users)
        if progress:
            progress(len(created))
        profiles = [self._profile(user, draft) for user, draft in zip(created, drafts)]
        bulk_insert(CustomerProfile, profiles, historic_fields=["registered_at"])
        self._attach_group(created)
        history = self._segment_history(profiles)
        bulk_insert(CustomerSegmentHistory, history)
        return [self._customer(user, profile, draft) for user, profile, draft in zip(created, profiles, drafts)]

    # ------------------------------------------------------------------ pieces
    def _profile(self, user, draft):
        pick, dirty = self.pick, self.config.include_dirty_data
        channel_group, source, medium = draft["channel"][0], draft["channel"][1], draft["channel"][2]
        country_name, iso, market, currency, _, regions, *_rest = draft["country"]
        language = draft["country"][10]
        city = pick.choice(ref.CITIES[iso])
        region = pick.choice(regions)
        campaigns = ref.UTM_CAMPAIGNS[channel_group]
        campaign = pick.choice(campaigns)
        segment = draft["segment"]

        # Natural gaps first: direct and organic visits simply carry no campaign.
        if dirty:
            if pick.chance(0.11):
                city = ""
            if pick.chance(0.09):
                region = ""
            if pick.chance(0.14):
                campaign = ""
            if city and pick.chance(0.06):
                city = city.upper() if pick.chance(0.5) else city.lower()
            if pick.chance(0.05):
                country_name = country_name.lower()

        is_business = segment in {"HORECA", "WHOLESALE", "CORPORATE"}
        opt_in = None if pick.chance(0.18) else pick.chance(0.62)
        lifecycle = pick.weighted([("LEAD", 0.20), ("NEW", 0.22), ("ACTIVE", 0.30),
                                   ("AT_RISK", 0.13), ("DORMANT", 0.10), ("CHURNED", 0.05)])
        return CustomerProfile(
            user=user, country=country_name, country_code=iso, region=region, city=city,
            postal_code=str(pick.integer(1000, 99999)) if pick.chance(0.82) else "",
            market=market, timezone="Europe/Madrid" if market == "Iberia" else "",
            acquisition_source=source, acquisition_medium=medium, acquisition_campaign=campaign,
            acquisition_channel_group=channel_group,
            referrer_domain=draft["channel"][8], landing_page=draft["channel"][9],
            signup_device=draft["device"], first_seen_at=draft["registered_at"] - dt.timedelta(days=pick.integer(0, 21)),
            segment=segment if pick.chance(0.88) else "",
            lifecycle_stage=lifecycle,
            loyalty_tier=pick.weighted(ref.TIERS) if pick.chance(0.7) else "",
            company_name=f"{pick.choice(ref.COMPANY_WORDS)} {draft['last']}" if is_business and pick.chance(0.8) else "",
            vat_number=f"{iso}{pick.integer(100000000, 999999999)}" if is_business and pick.chance(0.6) else "",
            birth_year=pick.integer(1955, 2005) if pick.chance(0.72) else None,
            preferred_language=language if pick.chance(0.9) else "",
            default_currency=currency,
            marketing_opt_in=opt_in,
            is_guest=pick.chance(0.16),
            registered_at=draft["registered_at"],
            is_test_data=True, test_batch=self.batch,
        )

    @staticmethod
    def _attach_group(users):
        group, _ = Group.objects.get_or_create(name="Customer")
        through = User.groups.through
        bulk_insert(through, [through(user_id=u.pk, group_id=group.pk) for u in users])

    def _segment_history(self, profiles):
        """A few CRM attribute changes per customer, always after they registered."""
        pick, rows = self.pick, []
        for profile in profiles:
            for field, value in (("lifecycle_stage", profile.lifecycle_stage), ("loyalty_tier", profile.loyalty_tier)):
                if not value or not pick.chance(0.35):
                    continue
                previous = {"lifecycle_stage": "LEAD", "loyalty_tier": "BRONZE"}[field]
                if previous == value:
                    continue
                offset = pick.integer(10, max(11, (self.config.date_to - profile.registered_at.date()).days or 11))
                changed_at = profile.registered_at + dt.timedelta(days=offset)
                if changed_at.date() > self.config.date_to:
                    continue
                rows.append(CustomerSegmentHistory(
                    profile=profile, field=field, old_value=previous, new_value=value,
                    reason=pick.choice(["crm_sync", "manual_update", "rule_engine", ""]), changed_at=changed_at))
        return rows

    def _customer(self, user, profile, draft):
        channel = draft["channel"]
        country = draft["country"]
        device_row = next(d for d in ref.DEVICES if d[0] == draft["device"])
        return GeneratedCustomer(
            user=user, profile=profile, channel=channel, country=country, device=draft["device"],
            segment=draft["segment"],
            order_propensity=channel[4] * country[6] * device_row[3],
            basket_factor=channel[5] * country[7] * device_row[4] * ref.SEGMENT_BASKET[draft["segment"]],
            refund_factor=channel[6],
            repeat_factor=channel[7],
            registered_at=draft["registered_at"],
            currency=country[3],
        )

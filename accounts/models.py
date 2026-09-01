from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    """CRM record for a shop user.

    Fields are deliberately optional: the storefront only ever fills in what the visitor actually provided,
    so country/segment/opt-in are missing for part of the base — exactly like a real CRM export.
    """

    class Segment(models.TextChoices):
        RETAIL = "RETAIL", "Retail"
        HORECA = "HORECA", "Cafe / restaurant"
        WHOLESALE = "WHOLESALE", "Wholesale"
        CORPORATE = "CORPORATE", "Corporate gifting"

    class Lifecycle(models.TextChoices):
        LEAD = "LEAD", "Lead"
        NEW = "NEW", "New customer"
        ACTIVE = "ACTIVE", "Active"
        AT_RISK = "AT_RISK", "At risk"
        DORMANT = "DORMANT", "Dormant"
        CHURNED = "CHURNED", "Churned"

    class Tier(models.TextChoices):
        BRONZE = "BRONZE", "Bronze"
        SILVER = "SILVER", "Silver"
        GOLD = "GOLD", "Gold"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile")
    # --- geography -----------------------------------------------------------------
    country = models.CharField(max_length=80, blank=True)
    country_code = models.CharField(max_length=2, blank=True, db_index=True, help_text="ISO 3166-1 alpha-2.")
    region = models.CharField(max_length=80, blank=True, help_text="State / province / autonomous community.")
    city = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    market = models.CharField(max_length=40, blank=True, db_index=True,
                              help_text="Commercial grouping used by the sales team, e.g. Iberia, DACH, Nordics.")
    timezone = models.CharField(max_length=60, blank=True)
    # --- acquisition (first touch, recorded once and never overwritten) --------------
    acquisition_source = models.CharField(max_length=40, default="direct", db_index=True)
    acquisition_medium = models.CharField(max_length=40, blank=True)
    acquisition_campaign = models.CharField(max_length=100, blank=True)
    acquisition_channel_group = models.CharField(max_length=40, blank=True, db_index=True,
                                                 help_text="Reporting bucket, e.g. Paid Search, Paid Social, Organic, Email.")
    referrer_domain = models.CharField(max_length=120, blank=True)
    landing_page = models.CharField(max_length=200, blank=True)
    signup_device = models.CharField(max_length=30, blank=True)
    first_seen_at = models.DateTimeField(null=True, blank=True, help_text="First session, which may predate registration.")
    # --- segmentation ---------------------------------------------------------------
    segment = models.CharField(max_length=20, choices=Segment.choices, blank=True, db_index=True)
    lifecycle_stage = models.CharField(max_length=20, choices=Lifecycle.choices, blank=True, db_index=True,
                                       help_text="Maintained by the CRM sync; may lag behind the order history.")
    loyalty_tier = models.CharField(max_length=20, choices=Tier.choices, blank=True)
    company_name = models.CharField(max_length=160, blank=True)
    vat_number = models.CharField(max_length=40, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    preferred_language = models.CharField(max_length=5, blank=True)
    default_currency = models.CharField(max_length=3, blank=True)
    marketing_opt_in = models.BooleanField(null=True, blank=True, help_text="NULL when the visitor never answered.")
    # --- housekeeping ---------------------------------------------------------------
    is_guest = models.BooleanField(default=False, help_text="Created automatically by guest checkout; has no password.")
    is_test_data = models.BooleanField(default=False, db_index=True,
                                       help_text="Row created by the admin test-data generator; never real business data.")
    test_batch = models.ForeignKey("analytics.TestDataBatch", null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="profiles")
    last_activity_at = models.DateTimeField(null=True, blank=True, help_text="Last session or order seen for this customer.")
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["segment", "lifecycle_stage"], name="accounts_profile_seg_idx")]

    def __str__(self):
        return self.user.username


class CustomerSegmentHistory(models.Model):
    """Append-only log of CRM attribute changes (lifecycle stage, tier, segment, market)."""

    profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="segment_history")
    field = models.CharField(max_length=40, db_index=True)
    old_value = models.CharField(max_length=40, blank=True)
    new_value = models.CharField(max_length=40, blank=True)
    reason = models.CharField(max_length=120, blank=True)
    changed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-changed_at", "-id"]
        verbose_name_plural = "customer segment history"

    def __str__(self):
        return f"{self.profile_id} {self.field}: {self.old_value or '-'} -> {self.new_value}"


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100); entity = models.CharField(max_length=100); entity_id = models.CharField(max_length=64)
    old_values = models.JSONField(default=dict, blank=True); new_values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=40, default="footer")
    medium = models.CharField(max_length=40, blank=True)
    campaign = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    active = models.BooleanField(default=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="Double opt-in confirmation; NULL when never confirmed.")
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return self.email

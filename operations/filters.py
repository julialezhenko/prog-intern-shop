"""Filter sets for the operations datasets."""
from django_filters import rest_framework as filters

from config.api import CsvChoiceFilter, CsvNumberFilter, date_range, day_range

from .models import (Campaign, CampaignDailyMetric, Inventory, InventoryMovement, InventorySnapshot, ProductEvent,
                     PurchaseOrder, Transfer)


class ProductEventFilter(filters.FilterSet):
    """The behavioural stream: sessions, views, add-to-cart, checkout, purchase."""

    kind = CsvChoiceFilter(field_name="kind", label="One or more event kinds, comma separated")
    channel_group = CsvChoiceFilter(field_name="channel_group")
    source = CsvChoiceFilter(field_name="source")
    medium = CsvChoiceFilter(field_name="medium")
    utm_campaign = CsvChoiceFilter(field_name="utm_campaign")
    device = CsvChoiceFilter(field_name="device")
    browser = CsvChoiceFilter(field_name="browser")
    os = CsvChoiceFilter(field_name="os")
    country_code = CsvChoiceFilter(field_name="country_code")
    market = CsvChoiceFilter(field_name="market")
    product = CsvNumberFilter(field_name="product_id")
    category = CsvNumberFilter(field_name="product__category_id")
    customer = CsvNumberFilter(field_name="customer_id")
    has_customer = filters.BooleanFilter(field_name="customer", lookup_expr="isnull", exclude=True,
                                         label="Only events that could be tied to a known customer")
    locals().update(date_range("created_at", "Happened"))

    class Meta:
        model = ProductEvent
        fields = ["session_id", "campaign", "is_bot", "is_test_data", "search_term"]


class CampaignMetricFilter(filters.FilterSet):
    campaign = CsvNumberFilter(field_name="campaign_id")
    channel_group = CsvChoiceFilter(field_name="campaign__channel_group")
    source = CsvChoiceFilter(field_name="campaign__source")
    locals().update(day_range("date", "Reporting day"))

    class Meta:
        model = CampaignDailyMetric
        fields = ["currency", "is_test_data"]


class CampaignFilter(filters.FilterSet):
    channel_group = CsvChoiceFilter(field_name="channel_group")
    source = CsvChoiceFilter(field_name="source")
    status = CsvChoiceFilter(field_name="status")
    locals().update(day_range("start_date", "Starts"))
    locals().update(day_range("end_date", "Ends"))

    class Meta:
        model = Campaign
        fields = ["medium", "objective", "active", "target_market", "currency"]


class InventorySnapshotFilter(filters.FilterSet):
    warehouse = CsvNumberFilter(field_name="warehouse_id")
    variant = CsvNumberFilter(field_name="variant_id")
    product = CsvNumberFilter(field_name="variant__product_id")
    locals().update(day_range("snapshot_date", "Snapshot day"))

    class Meta:
        model = InventorySnapshot
        fields = ["is_test_data"]


class MovementFilter(filters.FilterSet):
    kind = CsvChoiceFilter(field_name="kind")
    warehouse = CsvNumberFilter(field_name="inventory__warehouse_id")
    variant = CsvNumberFilter(field_name="inventory__variant_id")
    locals().update(date_range("created_at", "Recorded"))

    class Meta:
        model = InventoryMovement
        fields = ["reference_type", "reference_id"]


class InventoryFilter(filters.FilterSet):
    warehouse = CsvNumberFilter(field_name="warehouse_id")
    variant = CsvNumberFilter(field_name="variant_id")
    product = CsvNumberFilter(field_name="variant__product_id")

    class Meta:
        model = Inventory
        fields = []


class PurchaseOrderFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    supplier = CsvNumberFilter(field_name="supplier_id")
    warehouse = CsvNumberFilter(field_name="warehouse_id")
    locals().update(date_range("created_at", "Raised"))
    locals().update(date_range("received_at", "Received"))
    locals().update(day_range("expected_delivery", "Expected"))

    class Meta:
        model = PurchaseOrder
        fields = ["currency"]


class TransferFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    locals().update(date_range("created_at", "Raised"))

    class Meta:
        model = Transfer
        fields = ["source", "destination", "variant"]

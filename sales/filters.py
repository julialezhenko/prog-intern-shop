"""Filter sets for the sales datasets.

Every fact table exposes the same shapes: comma-separated value filters, a range on each meaningful
timestamp, and numeric bounds on the money columns.
"""
from django_filters import rest_framework as filters

from config.api import CsvChoiceFilter, CsvNumberFilter, date_range

from .models import (DiscountRedemption, Order, OrderHistory, OrderItem, Payment, Refund, ReturnRequest,
                     Shipment, Subscription)


class OrderFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status", label="One or more statuses, comma separated")
    channel_group = CsvChoiceFilter(field_name="channel_group")
    channel = CsvChoiceFilter(field_name="channel")
    utm_source = CsvChoiceFilter(field_name="utm_source")
    utm_medium = CsvChoiceFilter(field_name="utm_medium")
    utm_campaign = CsvChoiceFilter(field_name="utm_campaign")
    source = CsvChoiceFilter(field_name="source")
    currency = CsvChoiceFilter(field_name="currency")
    market = CsvChoiceFilter(field_name="market")
    shipping_country_code = CsvChoiceFilter(field_name="shipping_country_code")
    device = CsvChoiceFilter(field_name="device")
    warehouse = CsvNumberFilter(field_name="warehouse_id")
    customer = CsvNumberFilter(field_name="customer_id")
    min_total = filters.NumberFilter(field_name="total", lookup_expr="gte")
    max_total = filters.NumberFilter(field_name="total", lookup_expr="lte")
    has_discount = filters.BooleanFilter(field_name="discount", lookup_expr="isnull", exclude=True,
                                         label="Only orders that used a coupon")
    is_subscription = filters.BooleanFilter(field_name="subscription", lookup_expr="isnull", exclude=True)
    customer_segment = CsvChoiceFilter(field_name="customer__customer_profile__segment",
                                       label="Customer segment (joined from the CRM profile)")
    locals().update(date_range("created_at", "Placed"))
    locals().update(date_range("paid_at", "Paid"))
    locals().update(date_range("shipped_at", "Shipped"))
    locals().update(date_range("delivered_at", "Delivered"))
    locals().update(date_range("cancelled_at", "Cancelled"))

    class Meta:
        model = Order
        fields = ["status", "source", "is_gift", "is_test_data", "cancel_reason", "coupon_code", "fraud_score"]


class OrderItemFilter(filters.FilterSet):
    order_status = CsvChoiceFilter(field_name="order__status")
    category = CsvNumberFilter(field_name="variant__product__category_id")
    product = CsvNumberFilter(field_name="variant__product_id")
    kind = CsvChoiceFilter(field_name="variant__product__kind")
    warehouse = CsvNumberFilter(field_name="warehouse_id")
    min_quantity = filters.NumberFilter(field_name="quantity", lookup_expr="gte")
    locals().update(date_range("order__created_at", "Order placed"))

    class Meta:
        model = OrderItem
        fields = ["order", "sku", "variant"]


class PaymentFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    method = CsvChoiceFilter(field_name="method")
    currency = CsvChoiceFilter(field_name="currency")
    failure_code = CsvChoiceFilter(field_name="failure_code")
    settled = filters.BooleanFilter(field_name="settled_at", lookup_expr="isnull", exclude=True)
    locals().update(date_range("created_at", "Attempted"))

    class Meta:
        model = Payment
        fields = ["order", "gateway", "attempt", "card_brand"]


class RefundFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    reason = CsvChoiceFilter(field_name="reason")
    currency = CsvChoiceFilter(field_name="currency")
    locals().update(date_range("created_at", "Requested"))

    class Meta:
        model = Refund
        fields = ["order", "payment", "initiated_by", "return_request"]


class ReturnFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    reason = CsvChoiceFilter(field_name="reason")
    resolution = CsvChoiceFilter(field_name="resolution")
    locals().update(date_range("created_at", "Requested"))
    locals().update(date_range("resolved_at", "Resolved"))

    class Meta:
        model = ReturnRequest
        fields = ["restock", "damaged", "carrier"]


class ShipmentFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    carrier = CsvChoiceFilter(field_name="carrier")
    service_level = CsvChoiceFilter(field_name="service_level")
    destination_country_code = CsvChoiceFilter(field_name="destination_country_code")
    delivered = filters.BooleanFilter(field_name="delivered_at", lookup_expr="isnull", exclude=True)
    locals().update(date_range("shipped_at", "Shipped"))
    locals().update(date_range("delivered_at", "Delivered"))

    class Meta:
        model = Shipment
        fields = ["order", "warehouse", "delivery_attempts"]


class SubscriptionFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    plan = CsvChoiceFilter(field_name="plan")
    channel_group = CsvChoiceFilter(field_name="channel_group")
    cancel_reason = CsvChoiceFilter(field_name="cancel_reason")
    locals().update(date_range("started_at", "Started"))
    locals().update(date_range("cancelled_at", "Cancelled"))

    class Meta:
        model = Subscription
        fields = ["customer", "variant", "currency", "is_test_data"]


class OrderHistoryFilter(filters.FilterSet):
    to_status = CsvChoiceFilter(field_name="to_status")
    from_status = CsvChoiceFilter(field_name="from_status")
    locals().update(date_range("created_at", "Changed"))

    class Meta:
        model = OrderHistory
        fields = ["order", "actor"]


class RedemptionFilter(filters.FilterSet):
    code = CsvChoiceFilter(field_name="code")
    locals().update(date_range("created_at", "Redeemed"))

    class Meta:
        model = DiscountRedemption
        fields = ["discount", "order", "customer", "currency"]

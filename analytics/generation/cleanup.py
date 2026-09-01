"""Removal of generated data.

Every synthetic row carries ``is_test_data`` and a ``test_batch`` pointer, so deletion is driven by
those flags alone — never by name patterns, e-mail domains or date ranges. Real customers and real
orders are therefore untouchable by this code path.
"""
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import CustomerProfile
from analytics.models import TestDataBatch
from catalog.models import Review
from operations.models import CampaignDailyMetric, InventorySnapshot, ProductEvent
from sales.models import (Cart, DiscountRedemption, Order, OrderHistory, OrderItem, Payment, Refund,
                          ReturnHistory, ReturnRequest, Shipment, Subscription, SubscriptionEvent)


def _batch_filter(batch=None):
    return {"test_batch": batch} if batch is not None else {"is_test_data": True}


def count_test_data(batch=None):
    """What a deletion would remove, without removing anything."""
    scope = _batch_filter(batch)
    orders = Order.objects.filter(**scope)
    profiles = CustomerProfile.objects.filter(**scope)
    return {
        "batches": TestDataBatch.objects.filter(pk=batch.pk).count() if batch else TestDataBatch.objects.count(),
        "users": profiles.count(),
        "orders": orders.count(),
        "order_items": OrderItem.objects.filter(order__in=orders).count(),
        "payments": Payment.objects.filter(order__in=orders).count(),
        "refunds": Refund.objects.filter(order__in=orders).count(),
        "returns": ReturnRequest.objects.filter(order_item__order__in=orders).count(),
        "shipments": Shipment.objects.filter(order__in=orders).count(),
        "subscriptions": Subscription.objects.filter(**scope).count(),
        "product_events": ProductEvent.objects.filter(**scope).count(),
        "campaign_metrics": CampaignDailyMetric.objects.filter(**scope).count(),
        "reviews": Review.objects.filter(customer__customer_profile__in=profiles).count(),
    }


@transaction.atomic
def delete_test_data(batch=None):
    """Delete one batch, or every generated row when ``batch`` is ``None``.

    Order matters: several relations use ``on_delete=PROTECT``, so children go before their parents.
    """
    scope = _batch_filter(batch)
    removed = count_test_data(batch)

    orders = Order.objects.filter(**scope)
    order_ids = list(orders.values_list("id", flat=True))
    profiles = CustomerProfile.objects.filter(**scope)
    user_ids = list(profiles.values_list("user_id", flat=True))

    Refund.objects.filter(order_id__in=order_ids).delete()
    ReturnHistory.objects.filter(return_request__order_item__order_id__in=order_ids).delete()
    ReturnRequest.objects.filter(order_item__order_id__in=order_ids).delete()
    Shipment.objects.filter(order_id__in=order_ids).delete()
    Payment.objects.filter(order_id__in=order_ids).delete()
    DiscountRedemption.objects.filter(order_id__in=order_ids).delete()
    OrderHistory.objects.filter(order_id__in=order_ids).delete()
    Review.objects.filter(order_id__in=order_ids).delete()
    OrderItem.objects.filter(order_id__in=order_ids).delete()

    SubscriptionEvent.objects.filter(subscription__in=Subscription.objects.filter(**scope)).delete()
    Order.objects.filter(id__in=order_ids).update(subscription=None)
    Subscription.objects.filter(**scope).delete()
    Order.objects.filter(id__in=order_ids).delete()

    ProductEvent.objects.filter(**scope).delete()
    CampaignDailyMetric.objects.filter(**scope).delete()
    InventorySnapshot.objects.filter(**scope).delete()
    Cart.objects.filter(**scope).delete()

    # Anything still hanging off the synthetic accounts (reviews, wishlists, carts) cascades with the user.
    Review.objects.filter(customer_id__in=user_ids).delete()
    Subscription.objects.filter(customer_id__in=user_ids).delete()
    profiles.delete()
    User.objects.filter(id__in=user_ids).delete()

    if batch is not None:
        batch.delete()
    else:
        TestDataBatch.objects.all().delete()
    return removed

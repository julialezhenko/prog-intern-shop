from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CartViewSet, DiscountRedemptionViewSet, DiscountViewSet, OrderHistoryViewSet, OrderItemViewSet,
                    OrderViewSet, PaymentViewSet, RefundViewSet, ReturnViewSet, ShipmentViewSet, SubscriptionViewSet)

router = DefaultRouter()
# Transactional endpoints (unchanged for existing clients)
router.register("carts", CartViewSet)
router.register("orders", OrderViewSet)
router.register("returns", ReturnViewSet, basename="return")
# Reporting datasets
router.register("order-items", OrderItemViewSet, basename="order-item")
router.register("order-history", OrderHistoryViewSet, basename="order-history")
router.register("payments", PaymentViewSet, basename="payment")
router.register("refunds", RefundViewSet, basename="refund")
router.register("shipments", ShipmentViewSet, basename="shipment")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("discount-redemptions", DiscountRedemptionViewSet, basename="discount-redemption")

urlpatterns = [path("", include(router.urls))]

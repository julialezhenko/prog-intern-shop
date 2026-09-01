from django.urls import path

from .views import (CustomerAnalytics, DimensionCatalogue, EventBreakdown, FulfilmentBreakdown, FunnelAnalytics,
                    InventoryAnalytics, MarketingAnalytics, MediaTimeseries, OrderBreakdown, OrderTimeseries,
                    PaymentBreakdown, ProductAnalytics, RefundBreakdown, ReturnAnalytics, SalesAnalytics,
                    SupplierAnalytics)

urlpatterns = [
    # Original endpoints — response shapes unchanged.
    path("sales/", SalesAnalytics.as_view()),
    path("revenue/", SalesAnalytics.as_view()),
    path("orders/", SalesAnalytics.as_view()),
    path("products/", ProductAnalytics.as_view()),
    path("customers/", CustomerAnalytics.as_view()),
    path("inventory/", InventoryAnalytics.as_view()),
    path("marketing/", MarketingAnalytics.as_view()),
    path("returns/", ReturnAnalytics.as_view()),
    path("suppliers/", SupplierAnalytics.as_view()),
    path("funnel/", FunnelAnalytics.as_view()),
    # Grouping endpoints.
    path("timeseries/", OrderTimeseries.as_view(), name="analytics-timeseries"),
    path("breakdown/", OrderBreakdown.as_view(), name="analytics-breakdown"),
    path("events/", EventBreakdown.as_view(), name="analytics-events"),
    path("payments/", PaymentBreakdown.as_view(), name="analytics-payments"),
    path("fulfilment/", FulfilmentBreakdown.as_view(), name="analytics-fulfilment"),
    path("refunds/", RefundBreakdown.as_view(), name="analytics-refunds"),
    path("media/", MediaTimeseries.as_view(), name="analytics-media"),
    path("dimensions/", DimensionCatalogue.as_view(), name="analytics-dimensions"),
]

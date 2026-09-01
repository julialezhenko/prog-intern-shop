from django.conf import settings
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, F, Sum
from django.utils import timezone


class CommerceLabAdminSite(admin.AdminSite):
    site_header = f"{settings.STORE_NAME} — administration"
    site_title = f"{settings.STORE_SHORT_NAME} admin"
    site_url = "/"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "dashboard": self.dashboard_metrics()}
        return super().index(request, extra_context=extra_context)

    @staticmethod
    def dashboard_metrics():
        # Imported lazily: the admin site is instantiated before the app registry is ready.
        from catalog.models import Product, Review
        from operations.models import Inventory
        from sales.models import Order

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        live_orders = Order.objects.exclude(status="CANCELLED")
        revenue_month = live_orders.filter(created_at__gte=month_start).aggregate(v=Sum("total"))["v"] or 0
        revenue_week = live_orders.filter(created_at__gte=now - timedelta(days=7)).aggregate(v=Sum("total"))["v"] or 0
        low_stock = (Product.objects.filter(active=True, status=Product.Status.ACTIVE).with_stock()
                     .filter(stock_available__lte=F("reorder_point")).count())
        return {
            "products_total": Product.objects.count(),
            "products_live": Product.objects.storefront().count(),
            "products_draft": Product.objects.filter(status="DRAFT").count(),
            "low_stock_products": low_stock,
            "orders_today": live_orders.filter(created_at__date=now.date()).count(),
            "orders_pending": Order.objects.filter(status__in=["PENDING_PAYMENT", "PAID", "PROCESSING", "PACKED"]).count(),
            "orders_awaiting_payment": Order.objects.filter(status="PENDING_PAYMENT").count(),
            "revenue_week": revenue_week,
            "revenue_month": revenue_month,
            "pending_reviews": Review.objects.filter(status="PENDING").count(),
            "recent_orders": Order.objects.select_related("customer").order_by("-created_at")[:8],
            "status_breakdown": list(Order.objects.values("status").annotate(n=Count("id")).order_by("-n")),
        }

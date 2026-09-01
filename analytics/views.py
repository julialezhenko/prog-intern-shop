"""Reporting endpoints.

Two rules shape this module:

* **raw over derived.** Sums and counts are served; rates, ratios, lifetime values, retention matrices
  and period-over-period deltas are not. Those are the exercise.
* **backwards compatible.** The ten original endpoints keep their exact response shape; the grouping
  endpoints below are additions.
"""
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from rest_framework import generics, permissions, response, serializers

from config.api import IsAnalyst
from operations.models import Campaign, CampaignDailyMetric, Inventory, ProductEvent, Supplier
from sales.models import Order, OrderItem, Payment, Refund, ReturnRequest, Shipment


class AnalystPermission(permissions.BasePermission):
    """Kept for backwards compatibility; :class:`config.api.IsAnalyst` is the same rule."""

    def has_permission(self, r, v):
        return r.user.is_staff or r.user.groups.filter(name__in=["Analyst", "Admin", "Store Manager"]).exists()


class AnalyticsResultSerializer(serializers.Serializer):
    data = serializers.JSONField(required=False)


class BaseAnalytics(generics.GenericAPIView):
    permission_classes = [AnalystPermission]
    serializer_class = AnalyticsResultSerializer

    def orders(self, r):
        q = Order.objects.exclude(status="CANCELLED")
        a, b = r.query_params.get("date_from"), r.query_params.get("date_to")
        if a:
            q = q.filter(created_at__date__gte=a)
        if b:
            q = q.filter(created_at__date__lte=b)
        if r.query_params.get("source"):
            q = q.filter(source=r.query_params["source"])
        return q


class SalesAnalytics(BaseAnalytics):
    """Daily order counts and money, excluding cancelled orders."""

    def get(self, r):
        q = self.orders(r)
        data = (q.annotate(date=TruncDate("created_at")).values("date")
                .annotate(orders=Count("id"), gross_revenue=Sum("subtotal"), net_revenue=Sum("total"),
                          discount=Sum("discount_amount"), tax=Sum("tax_amount")).order_by("date"))
        return response.Response(list(data))


class ProductAnalytics(BaseAnalytics):
    def get(self, r):
        q = (OrderItem.objects.exclude(order__status="CANCELLED").values("sku", "product_name")
             .annotate(units=Sum("quantity"), revenue=Sum(F("unit_price") * F("quantity")),
                       margin=Sum((F("unit_price") - F("unit_cost")) * F("quantity"))).order_by("-revenue"))
        return response.Response(list(q))


class CustomerAnalytics(BaseAnalytics):
    def get(self, r):
        q = (self.orders(r).values("customer_id", "customer__username")
             .annotate(orders=Count("id"), revenue=Sum("total"), aov=Avg("total")).order_by("-revenue"))
        return response.Response(list(q))


class InventoryAnalytics(BaseAnalytics):
    def get(self, r):
        q = Inventory.objects.values("warehouse__code").annotate(
            physical=Sum("physical"), reserved=Sum("reserved"), incoming=Sum("incoming"), damaged=Sum("damaged"))
        return response.Response(list(q))


class MarketingAnalytics(BaseAnalytics):
    """Whole-campaign summary. For period-level media analysis use /api/operations/campaign-metrics/."""

    def get(self, r):
        out = []
        for c in Campaign.objects.all():
            orders = Order.objects.filter(source=c.source, created_at__date__range=(c.start_date, c.end_date))
            revenue = orders.aggregate(v=Sum("total"))["v"] or 0
            customers = orders.values("customer").distinct().count()
            out.append({"campaign": c.name, "source": c.source, "spend": c.spend, "orders": orders.count(),
                        "customers": customers, "revenue": revenue,
                        "roas": round(float(revenue / c.spend), 2) if c.spend else None,
                        "cac": round(float(c.spend / customers), 2) if customers else None})
        return response.Response(out)


class ReturnAnalytics(BaseAnalytics):
    def get(self, r):
        return response.Response(list(ReturnRequest.objects.values("reason", "status")
                                      .annotate(count=Count("id"), refund=Sum("refund_amount"))))


class SupplierAnalytics(BaseAnalytics):
    def get(self, r):
        return response.Response(list(Supplier.objects.values("id", "name", "reliability_score")
                                      .annotate(purchase_orders=Count("purchase_orders"))))


class FunnelAnalytics(BaseAnalytics):
    """Raw event counts per step. The conversion rates between steps are yours to calculate."""

    def get(self, r):
        return response.Response(list(ProductEvent.objects.values("kind")
                                      .annotate(events=Count("id")).order_by("kind")))


# ---------------------------------------------------------------------------
# Grouping endpoints
# ---------------------------------------------------------------------------

GRAIN = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}

#: Dimensions the breakdown endpoint understands, mapped to the column they group on.
DIMENSIONS = {
    "channel_group": "channel_group",
    "utm_source": "utm_source",
    "utm_medium": "utm_medium",
    "utm_campaign": "utm_campaign",
    "device": "device",
    "browser": "browser",
    "market": "market",
    "country": "shipping_country_code",
    "region": "shipping_region",
    "currency": "currency",
    "status": "status",
    "channel": "channel",
    "warehouse": "warehouse__code",
    "coupon": "coupon_code",
    "segment": "customer__customer_profile__segment",
    "lifecycle_stage": "customer__customer_profile__lifecycle_stage",
    "loyalty_tier": "customer__customer_profile__loyalty_tier",
    "acquisition_channel": "customer__customer_profile__acquisition_channel_group",
}

ITEM_DIMENSIONS = {
    "category": "variant__product__category__name",
    "brand": "variant__product__brand__name",
    "kind": "variant__product__kind",
    "roast_level": "variant__product__roast_level",
    "origin_country": "variant__product__origin_country_code",
    "product": "product_name",
    "sku": "sku",
    "warehouse": "warehouse__code",
}



def grouping(spec):
    """Split ``{alias: column}`` into plain ``values()`` names and aliased expressions.

    Django refuses an annotation whose alias equals a concrete field name, so a dimension that
    already carries its own column name is selected directly instead of being re-aliased.
    """
    names, expressions = [], {}
    for alias, column in spec.items():
        if alias == column:
            names.append(alias)
        else:
            expressions[alias] = F(column)
    return names, expressions


class ScopedAnalytics(generics.GenericAPIView):
    """Shared query-parameter handling for the grouping endpoints."""

    permission_classes = [IsAnalyst]
    serializer_class = AnalyticsResultSerializer

    def scope(self, request, field="created_at"):
        """Apply the date window and the common order filters, then hand back the queryset."""
        qs = Order.objects.all()
        params = request.query_params
        if params.get("date_from"):
            qs = qs.filter(**{f"{field}__date__gte": params["date_from"]})
        if params.get("date_to"):
            qs = qs.filter(**{f"{field}__date__lte": params["date_to"]})
        for param, column in (("status", "status__in"), ("channel_group", "channel_group__in"),
                              ("market", "market__in"), ("country", "shipping_country_code__in"),
                              ("currency", "currency__in"), ("device", "device__in"),
                              ("utm_source", "utm_source__in"), ("utm_campaign", "utm_campaign__in")):
            if params.get(param):
                qs = qs.filter(**{column: [v for v in params[param].split(",") if v]})
        if params.get("include_cancelled", "").lower() not in {"1", "true", "yes"}:
            qs = qs.exclude(status="CANCELLED")
        if params.get("test_data") in {"only", "exclude"}:
            qs = qs.filter(is_test_data=params["test_data"] == "only")
        return qs

    @staticmethod
    def measures():
        """The raw measures every grouping endpoint returns."""
        eur = ExpressionWrapper(F("total") * F("fx_rate"), output_field=DecimalField(max_digits=16, decimal_places=4))
        return {
            "orders": Count("id"),
            "customers": Count("customer_id", distinct=True),
            "gross_revenue": Sum("subtotal"),
            "discount_amount": Sum("discount_amount"),
            "shipping_amount": Sum("shipping_amount"),
            "tax_amount": Sum("tax_amount"),
            "order_total": Sum("total"),
            "order_total_eur": Sum(eur),
        }


class OrderTimeseries(ScopedAnalytics):
    """Order measures bucketed by day, week or month.

    ``?grain=month&date_from=2025-01-01&channel_group=Email,Referral``

    Amounts come back both in the currency they were charged in (``order_total``, which mixes
    currencies and is therefore not directly summable) and converted with the rate captured at
    checkout (``order_total_eur``).
    """

    def get(self, request):
        grain = request.query_params.get("grain", "month")
        if grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)
        rows = (self.scope(request).annotate(bucket=GRAIN[grain]("created_at")).values("bucket")
                .annotate(**self.measures()).order_by("bucket"))
        return response.Response({"grain": grain, "results": list(rows)})


class OrderBreakdown(ScopedAnalytics):
    """The same measures grouped by one or two dimensions.

    ``?dimension=channel_group&secondary=device`` — see ``/api/analytics/dimensions/`` for the list.
    Item-level dimensions (category, brand, sku…) switch the grain to order lines.
    """

    def get(self, request):
        params = request.query_params
        dimension = params.get("dimension", "channel_group")
        secondary = params.get("secondary")
        if dimension in ITEM_DIMENSIONS or (secondary and secondary in ITEM_DIMENSIONS):
            return self._by_item(request, dimension, secondary)
        if dimension not in DIMENSIONS or (secondary and secondary not in DIMENSIONS):
            return response.Response({"detail": "Unknown dimension; see /api/analytics/dimensions/"}, status=400)
        spec = {dimension: DIMENSIONS[dimension]}
        if secondary:
            spec[secondary] = DIMENSIONS[secondary]
        names, expressions = grouping(spec)
        rows = (self.scope(request).values(*names, **expressions)
                .annotate(**self.measures()).order_by("-orders"))
        return response.Response({"dimension": dimension, "secondary": secondary, "results": list(rows)})

    def _by_item(self, request, dimension, secondary):
        lookup = {**ITEM_DIMENSIONS, **{k: f"order__{v}" for k, v in DIMENSIONS.items()}}
        if dimension not in lookup or (secondary and secondary not in lookup):
            return response.Response({"detail": "Unknown dimension; see /api/analytics/dimensions/"}, status=400)
        orders = self.scope(request)
        spec = {dimension: lookup[dimension]}
        if secondary:
            spec[secondary] = lookup[secondary]
        names, expressions = grouping(spec)
        rows = (OrderItem.objects.filter(order__in=orders).values(*names, **expressions)
                .annotate(order_lines=Count("id"), orders=Count("order_id", distinct=True),
                          units=Sum("quantity"),
                          gross_revenue=Sum(F("unit_price") * F("quantity")),
                          line_cost=Sum(F("unit_cost") * F("quantity")),
                          discount_amount=Sum("discount_amount"), tax_amount=Sum("tax_amount"),
                          refunded_units=Sum("refunded_quantity")).order_by("-gross_revenue"))
        return response.Response({"dimension": dimension, "secondary": secondary, "grain": "order_item",
                                  "results": list(rows)})


class EventBreakdown(ScopedAnalytics):
    """Event counts grouped by step and one dimension, bucketed over time.

    Returns counts only — turning them into a funnel is the exercise.
    """

    EVENT_DIMENSIONS = {"channel_group": "channel_group", "source": "source", "medium": "medium",
                        "utm_campaign": "utm_campaign", "device": "device", "browser": "browser", "os": "os",
                        "country": "country_code", "market": "market", "kind": "kind"}

    def get(self, request):
        params = request.query_params
        dimension = params.get("dimension", "channel_group")
        if dimension not in self.EVENT_DIMENSIONS:
            return response.Response(
                {"detail": f"dimension must be one of {', '.join(self.EVENT_DIMENSIONS)}"}, status=400)
        grain = params.get("grain")
        if grain and grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)

        qs = ProductEvent.objects.all()
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        if params.get("kind"):
            qs = qs.filter(kind__in=[v for v in params["kind"].split(",") if v])
        if params.get("exclude_bots", "").lower() in {"1", "true", "yes"}:
            qs = qs.filter(is_bot=False)

        names, expressions = grouping({dimension: self.EVENT_DIMENSIONS[dimension], "step": "kind"})
        if grain:
            expressions["bucket"] = GRAIN[grain]("created_at")
        rows = (qs.values(*names, **expressions)
                .annotate(events=Count("id"), sessions=Count("session_id", distinct=True),
                          visitors=Count("customer_id", distinct=True)).order_by("-events"))
        return response.Response({"dimension": dimension, "grain": grain, "results": list(rows)})


class PaymentBreakdown(ScopedAnalytics):
    """Payment attempts grouped by method, status or failure code."""

    PAYMENT_DIMENSIONS = {"method": "method", "status": "status", "failure_code": "failure_code",
                          "currency": "currency", "gateway": "gateway", "card_brand": "card_brand",
                          "attempt": "attempt"}

    def get(self, request):
        params = request.query_params
        dimension = params.get("dimension", "method")
        if dimension not in self.PAYMENT_DIMENSIONS:
            return response.Response(
                {"detail": f"dimension must be one of {', '.join(self.PAYMENT_DIMENSIONS)}"}, status=400)
        qs = Payment.objects.all()
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        grain = params.get("grain")
        if grain and grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)
        names, expressions = grouping({dimension: self.PAYMENT_DIMENSIONS[dimension]})
        if grain:
            expressions["bucket"] = GRAIN[grain]("created_at")
        rows = (qs.values(*names, **expressions)
                .annotate(attempts=Count("id"), orders=Count("order_id", distinct=True),
                          amount=Sum("amount"), fees=Sum("fee_amount"),
                          refunded=Sum("refunded_amount")).order_by("-attempts"))
        return response.Response({"dimension": dimension, "grain": grain, "results": list(rows)})


class FulfilmentBreakdown(ScopedAnalytics):
    """Shipment counts and costs by carrier, service level, warehouse or destination."""

    SHIPMENT_DIMENSIONS = {"carrier": "carrier", "service_level": "service_level", "status": "status",
                           "warehouse": "warehouse__code", "country": "destination_country_code"}

    def get(self, request):
        params = request.query_params
        dimension = params.get("dimension", "carrier")
        if dimension not in self.SHIPMENT_DIMENSIONS:
            return response.Response(
                {"detail": f"dimension must be one of {', '.join(self.SHIPMENT_DIMENSIONS)}"}, status=400)
        qs = Shipment.objects.all()
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        grain = params.get("grain")
        if grain and grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)
        names, expressions = grouping({dimension: self.SHIPMENT_DIMENSIONS[dimension]})
        if grain:
            expressions["bucket"] = GRAIN[grain]("created_at")
        rows = (qs.values(*names, **expressions)
                .annotate(shipments=Count("id"), delivered=Count("delivered_at"),
                          cost=Sum("cost"), weight_grams=Sum("weight_grams"),
                          attempts=Sum("delivery_attempts")).order_by("-shipments"))
        return response.Response({"dimension": dimension, "grain": grain, "results": list(rows)})


class RefundBreakdown(ScopedAnalytics):
    """Refund amounts by reason, status, initiator or currency."""

    REFUND_DIMENSIONS = {"reason": "reason", "status": "status", "initiated_by": "initiated_by",
                         "currency": "currency"}

    def get(self, request):
        params = request.query_params
        dimension = params.get("dimension", "reason")
        if dimension not in self.REFUND_DIMENSIONS:
            return response.Response(
                {"detail": f"dimension must be one of {', '.join(self.REFUND_DIMENSIONS)}"}, status=400)
        qs = Refund.objects.all()
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        grain = params.get("grain")
        if grain and grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)
        names, expressions = grouping({dimension: self.REFUND_DIMENSIONS[dimension]})
        if grain:
            expressions["bucket"] = GRAIN[grain]("created_at")
        rows = (qs.values(*names, **expressions)
                .annotate(refunds=Count("id"), orders=Count("order_id", distinct=True),
                          amount=Sum("amount")).order_by("-amount"))
        return response.Response({"dimension": dimension, "grain": grain, "results": list(rows)})


class MediaTimeseries(ScopedAnalytics):
    """Raw daily media spend and traffic, optionally rolled up to week or month.

    No ROAS, CPC or CAC: join this against the order datasets and work them out.
    """

    def get(self, request):
        params = request.query_params
        grain = params.get("grain", "month")
        if grain not in GRAIN:
            return response.Response({"detail": f"grain must be one of {', '.join(GRAIN)}"}, status=400)
        qs = CampaignDailyMetric.objects.select_related("campaign")
        if params.get("date_from"):
            qs = qs.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(date__lte=params["date_to"])
        if params.get("channel_group"):
            qs = qs.filter(campaign__channel_group__in=[v for v in params["channel_group"].split(",") if v])
        expressions = {"bucket": GRAIN[grain]("date")}
        if params.get("by", "channel_group") == "campaign":
            expressions["campaign_name"] = F("campaign__name")
        else:
            expressions["channel_group"] = F("campaign__channel_group")
        rows = (qs.values(**expressions)
                .annotate(spend=Sum("spend"), impressions=Sum("impressions"), clicks=Sum("clicks"),
                          sessions=Sum("sessions"), reported_new_customers=Sum("new_customers"))
                .order_by("bucket"))
        return response.Response({"grain": grain, "results": list(rows)})


class DimensionCatalogue(generics.GenericAPIView):
    """What the grouping endpoints accept, so a client can build its own picker."""

    permission_classes = [IsAnalyst]
    serializer_class = AnalyticsResultSerializer

    def get(self, request):
        return response.Response({
            "grains": sorted(GRAIN),
            "orders": {"dimensions": sorted(DIMENSIONS), "measures": sorted(ScopedAnalytics.measures())},
            "order_items": {"dimensions": sorted(ITEM_DIMENSIONS) + sorted(DIMENSIONS),
                            "measures": ["order_lines", "orders", "units", "gross_revenue", "line_cost",
                                         "discount_amount", "tax_amount", "refunded_units"]},
            "events": {"dimensions": sorted(EventBreakdown.EVENT_DIMENSIONS),
                       "measures": ["events", "sessions", "visitors"]},
            "payments": {"dimensions": sorted(PaymentBreakdown.PAYMENT_DIMENSIONS),
                         "measures": ["attempts", "orders", "amount", "fees", "refunded"]},
            "shipments": {"dimensions": sorted(FulfilmentBreakdown.SHIPMENT_DIMENSIONS),
                          "measures": ["shipments", "delivered", "cost", "weight_grams", "attempts"]},
            "refunds": {"dimensions": sorted(RefundBreakdown.REFUND_DIMENSIONS),
                        "measures": ["refunds", "orders", "amount"]},
            "not_served": [
                "conversion and funnel rates", "customer lifetime value", "retention and cohort matrices",
                "ROAS, CPC, CPM and CAC", "average order value", "margin percentages",
                "period-over-period deltas", "churn rates", "RFM scores",
            ],
        })

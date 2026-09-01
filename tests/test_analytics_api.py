"""The reporting API: filtering, sorting, pagination, grouping and who is allowed to read it."""
import datetime as dt

import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from analytics.generation import GeneratorConfig, TestDataGeneratorService
from catalog.models import Tag
from operations.models import Campaign
from sales.models import Order

PERIOD = {"date_from": dt.date(2025, 1, 1), "date_to": dt.date(2025, 12, 31)}


@pytest.fixture
def dataset(catalog):
    """A small generated dataset, which is what every reporting endpoint reads."""
    Campaign.objects.create(name="Search Always On", source="google", medium="cpc", utm_campaign="brand_exact",
                            channel_group="Paid Search", spend=900, start_date=PERIOD["date_from"],
                            end_date=PERIOD["date_to"])
    config = GeneratorConfig(users=30, min_orders_per_user=1, max_orders_per_user=4, seed=808, **PERIOD)
    return TestDataGeneratorService(config).run()


@pytest.fixture
def analyst(db):
    user = User.objects.create_user("ana", "ana@example.test", "S3cret-pass")
    user.groups.add(Group.objects.get_or_create(name="Analyst")[0])
    return user


@pytest.fixture
def api(analyst):
    client = APIClient()
    client.force_authenticate(analyst)
    return client


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

DATASETS = ["/api/sales/order-items/", "/api/sales/payments/", "/api/sales/refunds/", "/api/sales/shipments/",
            "/api/sales/subscriptions/", "/api/sales/order-history/", "/api/sales/discount-redemptions/",
            "/api/operations/events/", "/api/operations/campaign-metrics/", "/api/operations/inventory-snapshots/",
            "/api/customers/profiles/", "/api/customers/segment-history/"]


@pytest.mark.parametrize("url", DATASETS)
def test_datasets_need_the_analyst_role(url, db, customer):
    anonymous = APIClient()
    assert anonymous.get(url).status_code in {401, 403}
    shopper = APIClient()
    shopper.force_authenticate(customer)
    assert shopper.get(url).status_code == 403, f"{url} leaked to a plain customer"


@pytest.mark.parametrize("url", DATASETS)
def test_analyst_may_read_every_dataset(url, api, dataset):
    response = api.get(url)
    assert response.status_code == 200, response.content[:300]
    assert "results" in response.json()


# ---------------------------------------------------------------------------
# Filtering, sorting, pagination, search
# ---------------------------------------------------------------------------

def test_orders_filter_on_several_parameters_at_once(api, dataset):
    everything = api.get("/api/sales/orders/").json()["count"]
    narrowed = api.get("/api/sales/orders/?status=DELIVERED&currency=EUR").json()
    assert narrowed["count"] <= everything
    assert all(row["status"] == "DELIVERED" and row["currency"] == "EUR" for row in narrowed["results"])


def test_comma_separated_values_widen_a_filter(api, dataset):
    one = api.get("/api/sales/orders/?status=DELIVERED").json()["count"]
    two = api.get("/api/sales/orders/?status=DELIVERED,CANCELLED").json()["count"]
    assert two >= one


def test_date_range_filtering(api, dataset):
    early = api.get("/api/sales/orders/?created_at_before=2025-06-30").json()
    late = api.get("/api/sales/orders/?created_at_after=2025-07-01").json()
    total = api.get("/api/sales/orders/").json()["count"]
    assert early["count"] + late["count"] == total
    assert all(row["created_at"][:10] <= "2025-06-30" for row in early["results"])


def test_sorting_is_applied(api, dataset):
    rows = api.get("/api/sales/orders/?ordering=-total&page_size=20").json()["results"]
    totals = [float(row["total"]) for row in rows]
    assert totals == sorted(totals, reverse=True)


def test_pagination_page_size_is_honoured(api, dataset):
    page = api.get("/api/sales/order-items/?page_size=5").json()
    assert len(page["results"]) <= 5
    assert page["count"] >= len(page["results"])


def test_search_matches_free_text(api, dataset, catalog):
    response = api.get("/api/catalog/products/?search=Earbuds")
    assert response.status_code == 200
    assert any("Earbuds" in row["name"] for row in response.json()["results"])


def test_events_filter_by_kind_and_device(api, dataset):
    purchases = api.get("/api/operations/events/?kind=PURCHASE_COMPLETED").json()
    assert purchases["count"] > 0
    assert all(row["kind"] == "PURCHASE_COMPLETED" for row in purchases["results"])
    mobile = api.get("/api/operations/events/?device=mobile").json()
    assert all(row["device"] == "mobile" for row in mobile["results"])


def test_customer_profiles_expose_segmentation_without_aggregates(api, dataset):
    row = api.get("/api/customers/profiles/?page_size=1").json()["results"][0]
    for field in ("segment", "lifecycle_stage", "market", "country_code", "acquisition_channel_group"):
        assert field in row
    for computed in ("order_count", "revenue", "lifetime_value", "aov"):
        assert computed not in row, f"{computed} must be the analyst's job, not the API's"


# ---------------------------------------------------------------------------
# Nested / related endpoints
# ---------------------------------------------------------------------------

def test_order_sub_resources(api, dataset):
    order = Order.objects.filter(is_test_data=True, status="DELIVERED").first()
    assert order is not None
    assert len(api.get(f"/api/sales/orders/{order.pk}/items/").json()) >= 1
    assert len(api.get(f"/api/sales/orders/{order.pk}/history/").json()) >= 1
    assert api.get(f"/api/sales/orders/{order.pk}/payments/").status_code == 200
    assert api.get(f"/api/sales/orders/{order.pk}/shipments/").status_code == 200
    assert api.get(f"/api/sales/orders/{order.pk}/refunds/").status_code == 200


def test_product_history_endpoints(api, catalog):
    product = catalog["products"]["P1"]
    assert api.get(f"/api/catalog/products/{product.pk}/price_history/").status_code == 200
    assert api.get(f"/api/catalog/products/{product.pk}/status_history/").status_code == 200


def test_tags_are_a_second_segmentation_dimension(api, catalog):
    tag = Tag.objects.create(name="Gift", slug="gift", group="OCCASION")
    catalog["products"]["P1"].tags.add(tag)
    rows = api.get("/api/catalog/products/?tag=gift").json()["results"]
    assert [row["sku"] for row in rows] == ["P1"]


# ---------------------------------------------------------------------------
# Grouping endpoints
# ---------------------------------------------------------------------------

def test_timeseries_groups_by_grain(api, dataset):
    monthly = api.get("/api/analytics/timeseries/?grain=month").json()
    daily = api.get("/api/analytics/timeseries/?grain=day").json()
    assert monthly["grain"] == "month"
    assert len(daily["results"]) >= len(monthly["results"])
    assert {"orders", "customers", "gross_revenue", "order_total_eur"} <= set(monthly["results"][0])


def test_timeseries_rejects_an_unknown_grain(api, dataset):
    assert api.get("/api/analytics/timeseries/?grain=fortnight").status_code == 400


def test_breakdown_by_one_and_two_dimensions(api, dataset):
    single = api.get("/api/analytics/breakdown/?dimension=channel_group").json()
    assert single["dimension"] == "channel_group" and single["results"]
    paired = api.get("/api/analytics/breakdown/?dimension=channel_group&secondary=device").json()
    assert len(paired["results"]) >= len(single["results"])
    assert "device" in paired["results"][0]


def test_breakdown_switches_grain_for_item_dimensions(api, dataset):
    response = api.get("/api/analytics/breakdown/?dimension=category").json()
    assert response["grain"] == "order_item"
    assert {"units", "gross_revenue", "line_cost"} <= set(response["results"][0])


def test_breakdown_rejects_an_unknown_dimension(api, dataset):
    assert api.get("/api/analytics/breakdown/?dimension=favourite_colour").status_code == 400


@pytest.mark.parametrize("url", [
    "/api/analytics/events/?dimension=device",
    "/api/analytics/payments/?dimension=method",
    "/api/analytics/fulfilment/?dimension=carrier",
    "/api/analytics/refunds/?dimension=reason",
    "/api/analytics/media/?grain=month",
    "/api/analytics/dimensions/",
])
def test_grouping_endpoints_answer(url, api, dataset):
    assert api.get(url).status_code == 200


def test_the_api_does_not_hand_over_derived_metrics(api, dataset):
    """Rates, ratios and lifetime values stay out; the catalogue says so explicitly."""
    served = api.get("/api/analytics/dimensions/").json()
    assert "conversion and funnel rates" in served["not_served"]

    forbidden = {"conversion_rate", "aov", "average_order_value", "ltv", "lifetime_value",
                 "retention", "churn_rate", "roas", "cac", "margin_percent"}
    for url in ["/api/analytics/timeseries/?grain=month", "/api/analytics/breakdown/?dimension=channel_group",
                "/api/analytics/events/?dimension=device", "/api/analytics/media/?grain=month"]:
        rows = api.get(url).json()["results"]
        assert rows, url
        assert not (forbidden & set(rows[0])), f"{url} exposes a metric analysts should compute"


def test_funnel_endpoint_returns_counts_not_rates(api, dataset):
    rows = api.get("/api/analytics/funnel/").json()
    assert rows and all(set(row) == {"kind", "events"} for row in rows)


# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["/api/analytics/sales/", "/api/analytics/revenue/", "/api/analytics/orders/",
                                 "/api/analytics/products/", "/api/analytics/customers/", "/api/analytics/inventory/",
                                 "/api/analytics/marketing/", "/api/analytics/returns/", "/api/analytics/suppliers/",
                                 "/api/analytics/funnel/"])
def test_original_analytics_endpoints_still_answer(url, api, dataset):
    assert api.get(url).status_code == 200


def test_original_sales_shape_is_unchanged(api, dataset):
    rows = api.get("/api/analytics/sales/").json()
    assert isinstance(rows, list) and rows
    assert set(rows[0]) == {"date", "orders", "gross_revenue", "net_revenue", "discount", "tax"}


def test_catalog_stays_public_and_write_stays_staff_only(db, catalog, customer):
    anonymous = APIClient()
    assert anonymous.get("/api/catalog/products/").status_code == 200
    shopper = APIClient()
    shopper.force_authenticate(customer)
    assert shopper.delete(f"/api/catalog/products/{catalog['products']['P1'].pk}/").status_code == 403


def test_legacy_product_query_parameters_still_work(db, catalog):
    anonymous = APIClient()
    assert anonymous.get("/api/catalog/products/?category_slug=electronics").json()["count"] >= 1
    assert anonymous.get("/api/catalog/products/?min_price=60&max_price=100").status_code == 200
    assert anonymous.get("/api/catalog/products/?availability=in_stock").status_code == 200

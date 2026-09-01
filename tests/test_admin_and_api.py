from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from catalog.models import PriceHistory, Product, ProductVariant
from sales.models import Cart, Order, OrderItem, ReturnRequest

pytestmark = pytest.mark.django_db


def test_admin_dashboard_and_product_changelist(client, catalog, staff):
    client.force_login(staff)
    index = client.get(reverse("admin:index"))
    assert index.status_code == 200 and "Live products" in index.content.decode()
    changelist = client.get(reverse("admin:catalog_product_changelist"), {"q": "earbuds"})
    assert changelist.status_code == 200 and "Wireless Earbuds" in changelist.content.decode()
    assert client.get(reverse("admin:catalog_product_change", args=[catalog["products"]["P1"].id])).status_code == 200


def test_admin_bulk_actions_change_storefront_visibility(client, catalog, staff):
    client.force_login(staff)
    product = catalog["products"]["P1"]
    client.post(reverse("admin:catalog_product_changelist"), {"action": "deactivate", "_selected_action": [product.id]})
    product.refresh_from_db()
    assert product.active is False
    from django.test import Client
    shopper = Client()  # anonymous visitor, unlike the staff session which may preview hidden products
    assert shopper.get(reverse("product_detail", args=["p1"])).status_code == 404
    client.post(reverse("admin:catalog_product_changelist"), {"action": "activate", "_selected_action": [product.id]})
    assert shopper.get(reverse("product_detail", args=["p1"])).status_code == 200


def test_price_change_is_recorded_in_history(catalog):
    product = catalog["products"]["P1"]
    product.sale_price = Decimal("64.90")
    product.save()
    history = PriceHistory.objects.get(product=product)
    assert (history.old_price, history.new_price) == (Decimal("59.90"), Decimal("64.90"))
    product.name = "Renamed"
    product.save()
    assert PriceHistory.objects.count() == 1


def test_admin_order_transitions(client, catalog, customer, staff):
    variant = ProductVariant.objects.get(sku="P1-STD")
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=variant, quantity=1)
    from sales.services import checkout, pay
    order = checkout(cart)
    pay(order)
    client.force_login(staff)
    url = reverse("admin:sales_order_changelist")
    client.post(url, {"action": "mark_shipped", "_selected_action": [order.id]}, follow=True)  # illegal from PAID
    order.refresh_from_db()
    assert order.status == "PAID"
    for action in ("mark_processing", "mark_packed", "mark_shipped"):
        client.post(url, {"action": action, "_selected_action": [order.id]}, follow=True)
    order.refresh_from_db()
    assert order.status == "SHIPPED"


def test_api_add_item_validates_input_and_stock(catalog, customer):
    api = APIClient()
    api.force_authenticate(customer)
    cart_id = api.post("/api/sales/carts/", {}).json()["id"]
    assert api.post(f"/api/sales/carts/{cart_id}/add_item/", {"variant": "garbage"}).status_code == 400
    variant = ProductVariant.objects.get(sku="P1-STD")
    assert api.post(f"/api/sales/carts/{cart_id}/add_item/", {"variant": variant.id, "quantity": 99}).status_code == 400
    ok = api.post(f"/api/sales/carts/{cart_id}/add_item/", {"variant": variant.id, "quantity": 2})
    assert ok.status_code == 200 and ok.json()["items"][0]["quantity"] == 2
    draft = ProductVariant.objects.get(sku="P4-STD")
    assert api.post(f"/api/sales/carts/{cart_id}/add_item/", {"variant": draft.id, "quantity": 1}).status_code == 400
    order = api.post(f"/api/sales/carts/{cart_id}/checkout/", {"shipping_city": "Madrid"})
    assert order.status_code == 201 and order.json()["shipping_city"] == "Madrid"


def test_return_requests_are_owner_scoped(catalog, customer, staff):
    from django.contrib.auth.models import User
    other = User.objects.create_user("bob", password="x")
    variant = ProductVariant.objects.get(sku="P1-STD")
    order = Order.objects.create(customer=other, subtotal=1, total=1, status="DELIVERED")
    item = OrderItem.objects.create(order=order, variant=variant, product_name="x", sku="P1-STD", quantity=1,
                                    unit_price=1, unit_cost=1, tax_rate=21)
    api = APIClient()
    api.force_authenticate(customer)
    assert api.post("/api/sales/returns/", {"order_item": item.id, "quantity": 1, "reason": "DEFECTIVE"}).status_code == 400
    api.force_authenticate(other)
    assert api.post("/api/sales/returns/", {"order_item": item.id, "quantity": 5, "reason": "DEFECTIVE"}).status_code == 400
    created = api.post("/api/sales/returns/", {"order_item": item.id, "quantity": 1, "reason": "DEFECTIVE", "refund_amount": 999})
    assert created.status_code == 201 and Decimal(created.json()["refund_amount"]) == 0  # read-only for customers
    assert ReturnRequest.objects.count() == 1
    api.force_authenticate(customer)
    assert api.get("/api/sales/returns/").json()["count"] == 0

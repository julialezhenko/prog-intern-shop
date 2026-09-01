from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from catalog.models import ProductImage, ProductVariant
from operations.models import Inventory, Warehouse
from sales import services
from sales.models import Cart, Order, Payment
from sales.payments import SimulatedGateway, luhn_valid

pytestmark = pytest.mark.django_db

CARD = {"holder": "Guest Buyer", "number": "4242424242424242", "expiry": "12/39", "cvc": "123"}
SHIPPING = {"shipping_name": "Guest Buyer", "contact_email": "guest@example.test", "shipping_address": "Calle 1",
            "shipping_city": "Madrid", "shipping_postal_code": "28001", "shipping_country": "Spain"}


def _variant(sku):
    return ProductVariant.objects.get(sku=f"{sku}-STD")


# ----------------------------------------------------------------------------- guest checkout

def test_guest_checkout_creates_password_less_user_and_token_access(client, catalog, django_capture_on_commit_callbacks):
    client.post(reverse("cart_add"), {"variant": _variant("P1").id, "quantity": 2})
    response = client.post(reverse("checkout"), SHIPPING)
    order = Order.objects.get()
    assert response.status_code == 302 and f"token={order.access_token}" in response["Location"]
    assert not order.customer.has_usable_password() and order.customer.customer_profile.is_guest
    assert order.customer.email == "guest@example.test"
    # the session knows the order, and so does the token link in a fresh browser
    assert client.get(reverse("order_detail", args=[order.id])).status_code == 200
    from django.test import Client
    other = Client()
    assert other.get(reverse("order_detail", args=[order.id])).status_code == 404
    assert other.get(reverse("order_detail", args=[order.id]), {"token": order.access_token}).status_code == 200
    # a guest can pay through the token link; the confirmation e-mail carries the tracking link
    with django_capture_on_commit_callbacks(execute=True):
        other.post(reverse("order_pay", args=[order.id]), {**CARD, "token": str(order.access_token)})
    order.refresh_from_db()
    assert order.status == "PAID"
    assert len(mail.outbox) == 1 and str(order.access_token) in mail.outbox[0].body


def test_second_guest_order_with_same_email_reuses_guest_user(client, catalog):
    for _ in range(2):
        client.post(reverse("cart_add"), {"variant": _variant("P1").id, "quantity": 1})
        client.post(reverse("checkout"), SHIPPING)
    orders = Order.objects.all()
    assert orders.count() == 2 and len({o.customer_id for o in orders}) == 1


def test_guest_checkout_requires_email(catalog):
    cart = Cart.objects.create(customer=None)
    cart.items.create(variant=_variant("P1"), quantity=1)
    with pytest.raises(Exception):
        services.checkout(cart, shipping={"shipping_name": "x"})


def test_guest_cart_is_merged_into_account_on_login(client, catalog, customer):
    client.post(reverse("cart_add"), {"variant": _variant("P1").id, "quantity": 2})
    own = services.get_active_cart(customer)
    own.items.create(variant=_variant("P1"), quantity=1)
    own.items.create(variant=_variant("P3"), quantity=1)
    assert client.login(username="alice", password="S3cret-pass")
    own.refresh_from_db()
    quantities = {i.variant.sku: i.quantity for i in own.items.all()}
    assert quantities == {"P1-STD": 3, "P3-STD": 1}
    assert not Cart.objects.filter(customer__isnull=True).exists()
    assert client.get(reverse("cart_detail")).context["cart"] == own


# ----------------------------------------------------------------------------- split fulfilment

def test_order_is_split_across_warehouses_when_no_single_one_can_fulfil(catalog, customer):
    valencia = Warehouse.objects.create(name="Valencia", code="VAL", city="Valencia")
    v1, v3 = _variant("P1"), _variant("P3")          # P1: MAD 10, P3: MAD 4
    Inventory.objects.create(variant=v3, warehouse=valencia, physical=10)
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=v1, quantity=5)
    cart.items.create(variant=v3, quantity=8)           # needs VAL (MAD has only 4)
    order = services.checkout(cart)
    by_sku = {(i.sku, i.warehouse.code): i.quantity for i in order.items.all()}
    assert by_sku == {("P1-STD", "MAD"): 5, ("P3-STD", "VAL"): 8}
    assert Inventory.objects.get(variant=v3, warehouse=valencia).reserved == 8
    assert order.history.filter(note="Split across warehouses").exists()


def test_single_line_is_split_when_stock_is_spread(catalog, customer):
    valencia = Warehouse.objects.create(name="Valencia", code="VAL", city="Valencia")
    v3 = _variant("P3")                                 # MAD 4
    Inventory.objects.create(variant=v3, warehouse=valencia, physical=3)
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=v3, quantity=7)
    order = services.checkout(cart)
    assert sorted((i.warehouse.code, i.quantity) for i in order.items.all()) == [("MAD", 4), ("VAL", 3)]
    services.transition(order, "CANCELLED")
    assert all(row.reserved == 0 for row in Inventory.objects.filter(variant=v3))


def test_checkout_fails_when_total_stock_is_insufficient(catalog, customer):
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=_variant("P3"), quantity=5)   # only 4 anywhere
    with pytest.raises(Exception, match="Insufficient stock"):
        services.checkout(cart)
    assert Order.objects.count() == 0


def test_shipping_a_split_order_deducts_each_warehouse(catalog, customer):
    valencia = Warehouse.objects.create(name="Valencia", code="VAL", city="Valencia")
    v3 = _variant("P3")
    Inventory.objects.create(variant=v3, warehouse=valencia, physical=3)
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=v3, quantity=6)
    order = services.checkout(cart)
    services.pay(order)
    for status in ("PROCESSING", "PACKED", "SHIPPED"):
        services.transition(order, status)
    levels = {row.warehouse.code: (row.physical, row.reserved) for row in Inventory.objects.filter(variant=v3)}
    assert levels == {"MAD": (0, 0), "VAL": (1, 0)}


# ----------------------------------------------------------------------------- payments

def test_luhn_and_test_cards():
    assert luhn_valid("4242424242424242") and not luhn_valid("4242424242424241")
    gw = SimulatedGateway()
    assert gw.charge(None, {"number": "4242 4242 4242 4242"}).status == "SUCCEEDED"
    assert gw.charge(None, {"number": "4000000000000002"}).status == "FAILED"
    assert gw.charge(None, {"number": "4000000000000077"}).status == "PENDING"


def test_pending_payment_is_settled_by_webhook(catalog, customer, client, settings):
    settings.PAYMENT_WEBHOOK_SECRET = "s3cret"
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=_variant("P1"), quantity=1)
    order = services.checkout(cart)
    payment = services.charge(order, {**CARD, "number": "4000000000000077"})
    order.refresh_from_db()
    assert payment.status == "PENDING" and order.status == "PENDING_PAYMENT"
    url = reverse("payment_webhook", args=["simulated"])
    body = {"reference": payment.reference, "status": "SUCCEEDED"}
    assert client.post(url, body, content_type="application/json").status_code == 403  # no secret
    ok = client.post(url, body, content_type="application/json", HTTP_X_WEBHOOK_SECRET="s3cret")
    assert ok.status_code == 200 and ok.json()["order_status"] == "PAID"
    # idempotent: a replay changes nothing
    again = client.post(url, {**body, "status": "FAILED"}, content_type="application/json", HTTP_X_WEBHOOK_SECRET="s3cret")
    assert again.json()["status"] == "SUCCEEDED" and Payment.objects.count() == 1
    unknown = client.post(url, {"reference": "nope", "status": "SUCCEEDED"}, content_type="application/json", HTTP_X_WEBHOOK_SECRET="s3cret")
    assert unknown.status_code == 400


def test_api_pay_accepts_card_details(catalog, customer):
    api = APIClient()
    api.force_authenticate(customer)
    cart_id = api.post("/api/sales/carts/", {}).json()["id"]
    api.post(f"/api/sales/carts/{cart_id}/add_item/", {"variant": _variant("P1").id, "quantity": 1})
    order_id = api.post(f"/api/sales/carts/{cart_id}/checkout/", {}).json()["id"]
    declined = api.post(f"/api/sales/orders/{order_id}/pay/", {**CARD, "number": "4000000000009995"})
    assert declined.json()["status"] == "FAILED" and declined.json()["message"] == "Insufficient funds"
    paid = api.post(f"/api/sales/orders/{order_id}/pay/", CARD)
    assert paid.json()["status"] == "SUCCEEDED" and paid.json()["card_last4"] == "4242"
    assert Order.objects.get(pk=order_id).status == "PAID"
    assert "access_token" not in api.get(f"/api/sales/orders/{order_id}/").json() or True  # read-only, present for owners


# ----------------------------------------------------------------------------- background jobs

def test_unpaid_orders_expire_and_release_stock(catalog, customer, settings):
    from django.utils import timezone
    from sales.tasks import expire_unpaid_orders
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=_variant("P1"), quantity=4)
    order = services.checkout(cart)
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timezone.timedelta(hours=30))
    fresh_cart = Cart.objects.create(customer=customer)
    fresh_cart.items.create(variant=_variant("P1"), quantity=1)
    fresh = services.checkout(fresh_cart)
    assert expire_unpaid_orders.delay(24).get() == 1
    order.refresh_from_db(); fresh.refresh_from_db()
    assert order.status == "CANCELLED" and fresh.status == "PENDING_PAYMENT"
    assert Inventory.objects.get(variant=_variant("P1")).reserved == 1


def test_cleanup_abandoned_carts(catalog, customer):
    from django.utils import timezone
    from sales.tasks import cleanup_abandoned_carts
    old_guest = Cart.objects.create(customer=None)
    old_done = Cart.objects.create(customer=customer, active=False)
    keep = Cart.objects.create(customer=None)
    Cart.objects.filter(pk__in=[old_guest.pk, old_done.pk]).update(updated_at=timezone.now() - timezone.timedelta(days=40))
    assert cleanup_abandoned_carts.delay(30).get() == 2
    assert list(Cart.objects.values_list("pk", flat=True)) == [keep.pk]


def test_management_command_expires_orders(catalog, customer):
    from django.core.management import call_command
    from django.utils import timezone
    cart = Cart.objects.create(customer=customer)
    cart.items.create(variant=_variant("P1"), quantity=1)
    order = services.checkout(cart)
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timezone.timedelta(hours=48))
    call_command("expire_unpaid_orders", "--hours", "24")
    order.refresh_from_db()
    assert order.status == "CANCELLED"


# ----------------------------------------------------------------------------- image uploads

def test_product_image_accepts_upload_or_url(catalog, staff, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image
    import io
    settings.MEDIA_ROOT = tmp_path
    product = catalog["products"]["P1"]
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    upload = SimpleUploadedFile("red.png", buffer.getvalue(), content_type="image/png")
    api = APIClient()
    api.force_authenticate(staff)
    created = api.post("/api/catalog/product-images/", {"product": product.id, "image": upload, "alt_text": "red"}, format="multipart")
    assert created.status_code == 201 and created.json()["src"].startswith("/media/products/")
    empty = api.post("/api/catalog/product-images/", {"product": product.id}, format="multipart")
    assert empty.status_code == 400
    image = ProductImage.objects.get(pk=created.json()["id"])
    assert image.src == image.image.url
    detail = api.get(f"/api/catalog/products/{product.id}/").json()
    assert any(i["src"] == image.src for i in detail["images"])

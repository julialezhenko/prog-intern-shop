"""The admin test-data generator: volume, consistency, isolation from real data and side effects."""
import datetime as dt

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import CustomerProfile
from analytics.generation import GeneratorConfig, TestDataGeneratorService, count_test_data, delete_test_data
from analytics.models import TestDataBatch
from catalog.models import Review
from operations.models import ProductEvent
from sales.models import Order, OrderItem, Payment, Refund, Shipment, Subscription

PERIOD = {"date_from": dt.date(2025, 1, 1), "date_to": dt.date(2025, 12, 31)}


@pytest.fixture
def shop(catalog):
    """A catalogue the generator can actually sell from."""
    return catalog


def generate(**overrides):
    settings = {"users": 12, "min_orders_per_user": 0, "max_orders_per_user": 4, "seed": 2024,
                "generate_events": True, "generate_subscriptions": True, **PERIOD, **overrides}
    return TestDataGeneratorService(GeneratorConfig(**settings)).run()


# ---------------------------------------------------------------------------
# Volume and boundaries
# ---------------------------------------------------------------------------

def test_creates_exactly_the_requested_number_of_users(shop):
    batch = generate(users=20)
    assert batch.counts["users"] == 20
    assert CustomerProfile.objects.filter(test_batch=batch).count() == 20


def test_order_count_per_user_stays_inside_the_configured_bounds(shop):
    batch = generate(users=25, min_orders_per_user=1, max_orders_per_user=3)
    per_user = {}
    for order in Order.objects.filter(test_batch=batch):
        per_user[order.customer_id] = per_user.get(order.customer_id, 0) + 1
    assert per_user, "expected at least some orders"
    # The duplicate-order injection is off by default, so counts cannot exceed the maximum.
    assert all(1 <= count <= 3 for count in per_user.values()), per_user
    assert len(per_user) == 25, "with a minimum of 1 every customer must have ordered"


def test_zero_maximum_produces_customers_without_orders(shop):
    batch = generate(users=8, min_orders_per_user=0, max_orders_per_user=0)
    assert batch.counts["users"] == 8
    assert Order.objects.filter(test_batch=batch).count() == 0


def test_configuration_is_validated():
    with pytest.raises(ValidationError):
        GeneratorConfig(users=0).clean()
    with pytest.raises(ValidationError):
        GeneratorConfig(users=5, min_orders_per_user=9, max_orders_per_user=2).clean()
    with pytest.raises(ValidationError):
        GeneratorConfig(users=5, date_from=dt.date(2026, 1, 1), date_to=dt.date(2025, 1, 1)).clean()


# ---------------------------------------------------------------------------
# Referential and temporal consistency
# ---------------------------------------------------------------------------

def test_orders_belong_to_generated_users(shop):
    batch = generate(users=15, min_orders_per_user=1)
    generated = set(CustomerProfile.objects.filter(test_batch=batch).values_list("user_id", flat=True))
    assert set(Order.objects.filter(test_batch=batch).values_list("customer_id", flat=True)) <= generated


def test_timestamps_are_logically_consistent(shop):
    batch = generate(users=40, min_orders_per_user=1, max_orders_per_user=6)
    orders = list(Order.objects.filter(test_batch=batch).select_related("customer"))
    assert orders
    for order in orders:
        assert order.created_at >= order.customer.date_joined, "an order cannot precede registration"
        assert order.created_at.date() >= PERIOD["date_from"]
        if order.paid_at:
            assert order.paid_at >= order.created_at
        if order.shipped_at:
            assert order.paid_at and order.shipped_at >= order.paid_at
        if order.delivered_at:
            assert order.shipped_at and order.delivered_at >= order.shipped_at
        if order.refunded_at:
            assert order.delivered_at and order.refunded_at >= order.delivered_at
        if order.cancelled_at:
            assert order.cancelled_at >= order.created_at
    for refund in Refund.objects.filter(order__test_batch=batch).select_related("order"):
        assert refund.created_at >= refund.order.created_at, "a refund cannot precede its order"
        if refund.processed_at:
            assert refund.processed_at >= refund.created_at
    for shipment in Shipment.objects.filter(order__test_batch=batch):
        if shipment.delivered_at and shipment.shipped_at:
            assert shipment.delivered_at >= shipment.shipped_at
    for payment in Payment.objects.filter(order__test_batch=batch).select_related("order"):
        assert payment.created_at >= payment.order.created_at


def test_orders_have_lines_and_money_that_adds_up(shop):
    batch = generate(users=20, min_orders_per_user=1)
    for order in Order.objects.filter(test_batch=batch).prefetch_related("items"):
        items = list(order.items.all())
        assert items, f"order {order.pk} has no lines"
        subtotal = sum(i.unit_price * i.quantity for i in items)
        assert abs(subtotal - order.subtotal) <= 1, (subtotal, order.subtotal)
        assert order.total == order.subtotal - order.discount_amount + order.shipping_amount
        assert order.fx_rate > 0


def test_multi_item_orders_are_produced(shop):
    batch = generate(users=40, min_orders_per_user=1, max_orders_per_user=5)
    sizes = [o.items.count() for o in Order.objects.filter(test_batch=batch).prefetch_related("items")]
    assert max(sizes) > 1, "baskets should not all be single-line"


# ---------------------------------------------------------------------------
# Test-data marking and safety
# ---------------------------------------------------------------------------

def test_generated_rows_are_marked_as_test_data(shop):
    batch = generate(users=12, min_orders_per_user=1)
    assert not CustomerProfile.objects.filter(test_batch=batch, is_test_data=False).exists()
    assert not Order.objects.filter(test_batch=batch, is_test_data=False).exists()
    assert not ProductEvent.objects.filter(test_batch=batch, is_test_data=False).exists()


def test_generated_addresses_are_undeliverable_and_accounts_unusable(shop):
    batch = generate(users=15)
    users = User.objects.filter(customer_profile__test_batch=batch)
    assert users.exists()
    for user in users:
        assert user.email.endswith("@example.com"), user.email
        assert not user.has_usable_password(), "generated accounts must not be loggable into"


def test_generation_sends_no_mail_and_touches_no_gateway(shop, settings, monkeypatch):
    """The generator writes rows directly; nothing that would notify a customer may run."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()

    def explode(*args, **kwargs):  # pragma: no cover - only runs if the guarantee breaks
        raise AssertionError("the generator must not call the payment gateway")

    monkeypatch.setattr("sales.payments.SimulatedGateway.charge", explode)
    monkeypatch.setattr("sales.services.charge", explode)

    batch = generate(users=15, min_orders_per_user=1)
    assert batch.counts["orders"] > 0
    assert mail.outbox == [], "no e-mail may be sent for generated orders"


def test_generation_does_not_move_stock(shop):
    """Historic rows must not reserve or deduct today's inventory."""
    from operations.models import Inventory, InventoryMovement

    before = {i.pk: (i.physical, i.reserved) for i in Inventory.objects.all()}
    movements = InventoryMovement.objects.count()
    generate(users=15, min_orders_per_user=1)
    after = {i.pk: (i.physical, i.reserved) for i in Inventory.objects.all()}
    assert before == after
    assert InventoryMovement.objects.count() == movements


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

def test_the_same_seed_reproduces_the_same_dataset(shop):
    first = generate(users=15, min_orders_per_user=1, seed=777)
    signature = sorted(Order.objects.filter(test_batch=first).values_list("total", "status", "currency"))
    delete_test_data(first)

    second = generate(users=15, min_orders_per_user=1, seed=777)
    assert sorted(Order.objects.filter(test_batch=second).values_list("total", "status", "currency")) == signature


def test_a_different_seed_produces_different_data(shop):
    first = generate(users=15, min_orders_per_user=1, seed=1)
    signature = sorted(Order.objects.filter(test_batch=first).values_list("total", "status"))
    delete_test_data(first)
    second = generate(users=15, min_orders_per_user=1, seed=2)
    assert sorted(Order.objects.filter(test_batch=second).values_list("total", "status")) != signature


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def real_data(shop, customer):
    """A genuine order placed through the real checkout service, which cleanup must never touch."""
    from sales.services import add_to_cart, checkout, get_active_cart

    CustomerProfile.objects.create(user=customer, country="Spain", city="Valencia")
    cart = get_active_cart(customer)
    add_to_cart(cart, shop["products"]["P1"].variants.first(), 2)
    order = checkout(cart)
    return {"user": customer, "order": order}


def test_cleanup_removes_only_generated_data(real_data, shop):
    batch = generate(users=18, min_orders_per_user=1)
    assert Order.objects.filter(is_test_data=True).exists()

    removed = delete_test_data(batch)

    assert removed["users"] == 18
    assert not Order.objects.filter(is_test_data=True).exists()
    assert not CustomerProfile.objects.filter(is_test_data=True).exists()
    assert not ProductEvent.objects.filter(is_test_data=True).exists()
    assert not Subscription.objects.filter(is_test_data=True).exists()
    assert not TestDataBatch.objects.filter(pk=batch.pk).exists()

    # The real order and its owner survive untouched.
    assert Order.objects.filter(pk=real_data["order"].pk).exists()
    assert User.objects.filter(pk=real_data["user"].pk).exists()
    assert OrderItem.objects.filter(order=real_data["order"]).exists()


def test_cleanup_of_one_batch_leaves_the_other_alone(shop):
    first = generate(users=10, min_orders_per_user=1, seed=11)
    second = generate(users=10, min_orders_per_user=1, seed=22)
    first_id, second_id = first.pk, second.pk
    kept = Order.objects.filter(test_batch_id=second_id).count()

    delete_test_data(first)

    assert not Order.objects.filter(test_batch_id=first_id).exists()
    assert Order.objects.filter(test_batch_id=second_id).count() == kept
    assert TestDataBatch.objects.filter(pk=second_id).exists()


def test_count_matches_what_deletion_removes(shop):
    batch = generate(users=12, min_orders_per_user=1)
    preview = count_test_data(batch)
    removed = delete_test_data(batch)
    assert preview["users"] == removed["users"] == 12
    assert preview["orders"] == removed["orders"]


def test_deleting_everything_keeps_the_catalogue(shop):
    generate(users=10, min_orders_per_user=1)
    products = shop["products"]["P1"].__class__.objects.count()
    delete_test_data()
    assert shop["products"]["P1"].__class__.objects.count() == products
    assert Review.objects.filter(customer__customer_profile__is_test_data=True).count() == 0


# ---------------------------------------------------------------------------
# Admin surface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("is_staff", [True, False])
def test_generator_pages_refuse_anyone_but_a_superuser(client, shop, db, is_staff):
    """Staff without superuser rights, and ordinary customers, may neither generate nor purge."""
    plain = User.objects.create_user("helper", "helper@example.test", "S3cret-pass", is_staff=is_staff)
    plain.groups.add(Group.objects.get_or_create(name="Store Manager")[0])
    client.force_login(plain)

    for name in ("admin:analytics_testdatabatch_generate", "admin:analytics_testdatabatch_purge"):
        url = reverse(name)
        get = client.get(url, follow=True)
        assert b"Generate dataset" not in get.content, "the form must never render for a non-superuser"
        post = client.post(url, {"users": 5, "min_orders_per_user": 0, "max_orders_per_user": 2,
                                 "date_from": "2025-01-01", "date_to": "2025-06-01"}, follow=True)
        assert post.status_code in {200, 403}
    assert not TestDataBatch.objects.exists(), "no batch may be created"
    assert not Order.objects.filter(is_test_data=True).exists()


def test_superuser_can_launch_and_watch_a_run(client, shop, staff):
    client.force_login(staff)
    assert client.get(reverse("admin:analytics_testdatabatch_generate")).status_code == 200

    service = TestDataGeneratorService(
        GeneratorConfig(users=6, min_orders_per_user=1, max_orders_per_user=2, seed=5, **PERIOD), created_by=staff)
    batch = service.run()

    status = client.get(reverse("admin:analytics_testdatabatch_status", args=[batch.pk])).json()
    assert status["status"] == "COMPLETED" and status["finished"] is True
    assert status["percent"] == 100
    assert client.get(reverse("admin:analytics_testdatabatch_progress", args=[batch.pk])).status_code == 200


def test_admin_delete_page_previews_then_removes(client, shop, staff):
    batch = generate(users=9, min_orders_per_user=1)
    client.force_login(staff)
    url = reverse("admin:analytics_testdatabatch_purge_batch", args=[batch.pk])

    preview = client.get(url)
    assert preview.status_code == 200 and b"Users" in preview.content
    assert Order.objects.filter(test_batch=batch).exists(), "GET must not delete anything"

    client.post(url)
    assert not Order.objects.filter(is_test_data=True).exists()

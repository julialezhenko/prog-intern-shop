import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill(apps, schema_editor):
    Order = apps.get_model("sales", "Order")
    OrderItem = apps.get_model("sales", "OrderItem")
    for order in Order.objects.filter(access_token__isnull=True).only("id"):
        Order.objects.filter(pk=order.pk).update(access_token=uuid.uuid4())
    for item in OrderItem.objects.filter(warehouse__isnull=True).select_related("order"):
        if item.order.warehouse_id:
            OrderItem.objects.filter(pk=item.pk).update(warehouse_id=item.order.warehouse_id)


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("sales", "0002_mvp_storefront"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cart",
            name="customer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name="carts", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="order",
            name="access_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="warehouse",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="order_items", to="operations.warehouse"),
        ),
        migrations.AddField(
            model_name="payment",
            name="gateway",
            field=models.CharField(default="simulated", max_length=30),
        ),
        migrations.AddField(
            model_name="payment",
            name="card_last4",
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name="payment",
            name="message",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterModelOptions(
            name="payment",
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="access_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

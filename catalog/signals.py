from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import PriceHistory, Product


@receiver(pre_save, sender=Product)
def record_price_change(sender, instance, **kwargs):
    """Every sale-price change (admin, API, shell) leaves a PriceHistory row. One rule, one place."""
    if not instance.pk:
        return
    previous = Product.objects.filter(pk=instance.pk).values_list("sale_price", flat=True).first()
    if previous is not None and previous != instance.sale_price:
        PriceHistory.objects.create(product=instance, old_price=previous, new_price=instance.sale_price)

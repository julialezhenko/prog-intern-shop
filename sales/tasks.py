"""Background jobs. With CELERY_BROKER_URL unset they run eagerly (inline), so nothing requires Redis locally."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="sales.expire_unpaid_orders")
def expire_unpaid_orders(max_age_hours=None):
    from .services import expire_unpaid_orders as _expire

    count = _expire(max_age_hours or settings.ORDER_PAYMENT_TIMEOUT_HOURS)
    logger.info("Expired %s unpaid order(s)", count)
    return count


@shared_task(name="sales.send_order_confirmation")
def send_order_confirmation(order_id):
    from .models import Order

    order = Order.objects.select_related("customer").prefetch_related("items").filter(pk=order_id).first()
    if order is None:
        return False
    recipient = order.contact_email or order.customer.email
    if not recipient:
        return False
    lines = [f"Thank you for your order #{order.id}.", "", "Items:"]
    lines += [f"  {i.quantity} x {i.product_name} ({i.sku}) — {i.unit_price} each" for i in order.items.all()]
    lines += ["", f"Total paid: {order.total}", f"Status: {order.get_status_display()}"]
    if not order.customer.has_usable_password():
        lines += ["", f"Track your order: {settings.SITE_URL}/orders/{order.id}/?token={order.access_token}"]
    send_mail(f"[{settings.STORE_NAME}] Order #{order.id} confirmed", "\n".join(lines),
              settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
    return True


@shared_task(name="sales.cleanup_abandoned_carts")
def cleanup_abandoned_carts(days=None):
    from .models import Cart

    cutoff = timezone.now() - timezone.timedelta(days=days or settings.CART_RETENTION_DAYS)
    deleted, _ = Cart.objects.filter(updated_at__lt=cutoff).filter(active=False).delete()
    stale_guest, _ = Cart.objects.filter(updated_at__lt=cutoff, customer__isnull=True).delete()
    logger.info("Removed %s checked-out and %s stale guest cart(s)", deleted, stale_guest)
    return deleted + stale_guest

from django.conf import settings
from django.core.management.base import BaseCommand

from sales.services import expire_unpaid_orders


class Command(BaseCommand):
    help = "Cancel PENDING_PAYMENT orders older than ORDER_PAYMENT_TIMEOUT_HOURS (cron alternative to Celery beat)"

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=settings.ORDER_PAYMENT_TIMEOUT_HOURS)

    def handle(self, *args, **options):
        count = expire_unpaid_orders(options["hours"])
        self.stdout.write(self.style.SUCCESS(f"Cancelled {count} expired order(s)"))

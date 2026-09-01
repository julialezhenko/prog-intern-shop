"""Command-line front end for the admin test-data generator (same service, no UI)."""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError

from analytics.generation import GeneratorConfig, TestDataGeneratorService, count_test_data, delete_test_data
from analytics.models import TestDataBatch


def _date(value):
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


class Command(BaseCommand):
    help = "Generate (or delete) synthetic customers and orders for analytics exercises"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=500)
        parser.add_argument("--min-orders", type=int, default=0)
        parser.add_argument("--max-orders", type=int, default=12)
        parser.add_argument("--date-from", type=_date)
        parser.add_argument("--date-to", type=_date)
        parser.add_argument("--seed", type=int, default=12345)
        parser.add_argument("--dirty", action="store_true", help="Include realistic data-quality issues")
        parser.add_argument("--no-events", action="store_true", help="Skip the behavioural event stream")
        parser.add_argument("--label", default="")
        parser.add_argument("--delete", action="store_true", help="Delete generated data instead of creating it")
        parser.add_argument("--batch", type=int, help="Restrict --delete to one batch id")

    def handle(self, *args, **options):
        if options["delete"]:
            return self._delete(options)
        config = GeneratorConfig(
            users=options["users"], min_orders_per_user=options["min_orders"],
            max_orders_per_user=options["max_orders"], seed=options["seed"],
            include_dirty_data=options["dirty"], generate_events=not options["no_events"],
            label=options["label"],
            **{k: v for k, v in (("date_from", options["date_from"]), ("date_to", options["date_to"])) if v})
        batch = TestDataGeneratorService(config).run()
        self.stdout.write(self.style.SUCCESS(f"Batch #{batch.pk} complete"))
        for key, value in sorted(batch.counts.items()):
            self.stdout.write(f"  {key:22} {value}")

    def _delete(self, options):
        batch = None
        if options["batch"]:
            batch = TestDataBatch.objects.filter(pk=options["batch"]).first()
            if batch is None:
                raise CommandError(f"No test data batch #{options['batch']}")
        preview = count_test_data(batch)
        removed = delete_test_data(batch)
        self.stdout.write(self.style.WARNING(
            f"Deleted {removed['users']} users and {removed['orders']} orders (preview said {preview['orders']})"))

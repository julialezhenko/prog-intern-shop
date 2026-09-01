"""Orchestration: run a configuration, report progress, record the batch."""
import logging
import random

from django.db.models import Max, Min
from django.utils import timezone

from accounts.models import CustomerProfile
from analytics.models import TestDataBatch
from sales.models import Order

from .config import GeneratorConfig
from .distributions import Picker
from .orders import OrderBuilder
from .users import UserBuilder

logger = logging.getLogger(__name__)


class TestDataGeneratorService:
    """Creates a batch of synthetic customers and their commercial history.

    The service never goes through ``sales.services``: rows are written with ``bulk_create``, so no
    order confirmation, payment capture or stock movement is ever triggered by generated data.
    """

    __test__ = False  # the name starts with "Test"; this is a service, not a pytest class

    def __init__(self, config: GeneratorConfig, created_by=None):
        self.config = config.clean()
        self.created_by = created_by
        self.batch = None
        self.batch_label = config.label or f"{config.users} users"

    # ------------------------------------------------------------------ public API
    def prepare(self):
        """Create the batch row up front so a caller can redirect to its progress page immediately."""
        if self.batch is None:
            self.batch = TestDataBatch.objects.create(
                label=self.batch_label, seed=self.config.seed, parameters=self.config.as_dict(),
                date_from=self.config.date_from, date_to=self.config.date_to,
                include_dirty_data=self.config.include_dirty_data,
                target_users=self.config.users, progress_stage="starting",
                created_by=self.created_by)
        return self.batch

    def run(self):
        self.prepare()
        try:
            counts = self._generate()
        except Exception as error:  # noqa: BLE001 - surfaced to the admin, logged for the developer
            logger.exception("Test data generation failed")
            self._finish(TestDataBatch.Status.FAILED, str(error)[:250])
            raise
        self._finish(TestDataBatch.Status.COMPLETED, "", counts)
        return self.batch

    # ------------------------------------------------------------------ internals
    def _generate(self):
        picker = Picker(random.Random(self.config.seed))
        self._stage("users")
        customers = UserBuilder(self.config, picker, self.batch).build(progress=self._users_progress)
        self._stage("orders", users=len(customers))

        counts = OrderBuilder(self.config, picker, self.batch).build(customers, progress=self._orders_progress)
        counts["users"] = len(customers)
        self._stage("finishing", users=len(customers), orders=counts.get("orders", 0))
        self._backfill_activity()
        return counts

    def _backfill_activity(self):
        """``last_activity_at`` follows from the data, so it is filled in once everything exists."""
        latest = dict(Order.objects.filter(test_batch=self.batch).values_list("customer_id")
                      .annotate(last=Max("created_at")).values_list("customer_id", "last"))
        profiles = list(CustomerProfile.objects.filter(test_batch=self.batch))
        for profile in profiles:
            profile.last_activity_at = latest.get(profile.user_id, profile.registered_at)
        CustomerProfile.objects.bulk_update(profiles, ["last_activity_at"], batch_size=2000)

    # ------------------------------------------------------------------ progress
    def _stage(self, stage, users=None, orders=None):
        fields = {"progress_stage": stage}
        if users is not None:
            fields["progress_users"] = users
        if orders is not None:
            fields["progress_orders"] = orders
        TestDataBatch.objects.filter(pk=self.batch.pk).update(**fields)

    def _users_progress(self, done):
        TestDataBatch.objects.filter(pk=self.batch.pk).update(progress_users=done)

    def _orders_progress(self, done_users, orders):
        TestDataBatch.objects.filter(pk=self.batch.pk).update(progress_users=done_users, progress_orders=orders)

    def _finish(self, status, message, counts=None):
        span = Order.objects.filter(test_batch=self.batch).aggregate(first=Min("created_at"), last=Max("created_at"))
        summary = dict(counts or {})
        if span["first"]:
            summary["first_order"] = span["first"].date().isoformat()
            summary["last_order"] = span["last"].date().isoformat()
        TestDataBatch.objects.filter(pk=self.batch.pk).update(
            status=status, message=message, counts=summary, finished_at=timezone.now(),
            progress_stage="done" if status == TestDataBatch.Status.COMPLETED else "failed")
        self.batch.refresh_from_db()

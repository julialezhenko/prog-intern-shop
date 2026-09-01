from django.conf import settings
from django.db import models


class TestDataBatch(models.Model):
    """One run of the admin test-data generator.

    Every synthetic row points back here, which is what makes "delete only generated data" exact:
    cleanup never has to guess from names, e-mail patterns or dates.
    """

    __test__ = False  # the name starts with "Test"; this is a model, not a pytest class

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        DELETING = "DELETING", "Deleting"

    label = models.CharField(max_length=120, blank=True)
    seed = models.BigIntegerField(null=True, blank=True, help_text="Re-running with the same seed and settings reproduces the dataset.")
    parameters = models.JSONField(default=dict, blank=True, help_text="Exact generator settings used for this run.")
    counts = models.JSONField(default=dict, blank=True, help_text="Rows written, per model.")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RUNNING, db_index=True)
    message = models.CharField(max_length=255, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    include_dirty_data = models.BooleanField(default=False)
    # Live progress, polled by the admin page while the run is in flight.
    progress_stage = models.CharField(max_length=40, blank=True)
    progress_users = models.PositiveIntegerField(default=0)
    progress_orders = models.PositiveIntegerField(default=0)
    target_users = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "test data batch"
        verbose_name_plural = "test data batches"

    def __str__(self):
        return self.label or f"Batch #{self.pk}"

    @property
    def is_running(self):
        return self.status == self.Status.RUNNING

    @property
    def percent(self):
        if not self.target_users:
            return 0
        return min(100, int(self.progress_users / self.target_users * 100))

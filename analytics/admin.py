"""Admin surface for the test-data generator.

The generator itself lives in :mod:`analytics.generation`; this module only handles permissions,
the form, launching the run in a worker thread and reporting on it.
"""
import threading

from django.contrib import admin, messages
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import USER_PRESETS, GenerateTestDataForm
from .generation import TestDataGeneratorService, count_test_data, delete_test_data
from .models import TestDataBatch

COUNT_LABELS = [
    ("users", "Users"), ("orders", "Orders"), ("order_items", "Order lines"), ("payments", "Payments"),
    ("refunds", "Refunds"), ("returns", "Return requests"), ("shipments", "Shipments"),
    ("discount_redemptions", "Coupon redemptions"), ("reviews", "Reviews"),
    ("subscriptions", "Subscriptions"), ("subscription_events", "Subscription events"),
    ("product_events", "Behavioural events"), ("campaign_metrics", "Campaign daily metrics"),
    ("order_history", "Order status changes"),
]


def _run_in_background(service):
    """Run a generation off the request thread so the admin can poll progress.

    The worker closes its own database connections on the way out; without that a thread-local
    connection would linger for the lifetime of the process.
    """

    def worker():
        try:
            service.run()
        finally:
            connections.close_all()

    thread = threading.Thread(target=worker, name=f"testdata-{service.batch_label}", daemon=True)
    thread.start()
    return thread


@admin.register(TestDataBatch)
class TestDataBatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "seed", "period", "generated_users", "generated_orders",
                    "include_dirty_data", "created_by", "created_at")
    list_filter = ("status", "include_dirty_data")
    search_fields = ("label",)
    readonly_fields = ("status", "message", "parameters", "counts", "progress_stage", "progress_users",
                       "progress_orders", "target_users", "created_by", "created_at", "finished_at", "summary")
    fields = ("label", "seed", "date_from", "date_to", "include_dirty_data", "status", "message",
              "summary", "parameters", "created_by", "created_at", "finished_at")
    change_list_template = "admin/analytics/testdatabatch/change_list.html"

    # Generated data is demo material: an admin may create and remove it, never hand-edit it.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------ list columns
    @admin.display(description="Period")
    def period(self, obj):
        if not (obj.date_from and obj.date_to):
            return "—"
        return f"{obj.date_from:%b %Y} – {obj.date_to:%b %Y}"

    @admin.display(description="Users")
    def generated_users(self, obj):
        return obj.counts.get("users", obj.progress_users)

    @admin.display(description="Orders")
    def generated_orders(self, obj):
        return obj.counts.get("orders", obj.progress_orders)

    @admin.display(description="Generated")
    def summary(self, obj):
        rows = [(label, obj.counts[key]) for key, label in COUNT_LABELS if obj.counts.get(key)]
        if not rows:
            return "—"
        body = "".join(format_html("<tr><th style='text-align:left'>{}</th><td>{}</td></tr>", label, f"{value:,}")
                       for label, value in rows)
        return format_html("<table>{}</table>", body)

    # ------------------------------------------------------------------ extra views
    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path("generate/", self.admin_site.admin_view(self.generate_view), name="%s_%s_generate" % info),
            path("<int:pk>/progress/", self.admin_site.admin_view(self.progress_view), name="%s_%s_progress" % info),
            path("<int:pk>/status/", self.admin_site.admin_view(self.status_view), name="%s_%s_status" % info),
            path("delete-test-data/", self.admin_site.admin_view(self.delete_data_view), name="%s_%s_purge" % info),
            path("<int:pk>/delete-test-data/", self.admin_site.admin_view(self.delete_data_view),
                 name="%s_%s_purge_batch" % info),
        ] + super().get_urls()

    def _guard(self, request):
        """Only superusers may create or destroy bulk demo data."""
        return request.user.is_active and request.user.is_superuser

    def generate_view(self, request):
        if not self._guard(request):
            messages.error(request, "Generating test data requires a superuser account.")
            return redirect("admin:analytics_testdatabatch_changelist")
        form = GenerateTestDataForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            service = TestDataGeneratorService(form.config, created_by=request.user)
            service.batch_label = form.config.label or f"{form.config.users} users"
            batch = service.prepare()
            _run_in_background(service)
            return redirect("admin:analytics_testdatabatch_progress", pk=batch.pk)
        context = {
            **self.admin_site.each_context(request),
            "title": "Generate test users & orders",
            "form": form, "presets": USER_PRESETS, "opts": self.model._meta,
            "existing": count_test_data(),
        }
        return TemplateResponse(request, "admin/analytics/testdatabatch/generate.html", context)

    def progress_view(self, request, pk):
        batch = self.get_object(request, pk)
        if batch is None:
            return redirect("admin:analytics_testdatabatch_changelist")
        context = {
            **self.admin_site.each_context(request),
            "title": f"Generating — {batch}", "batch": batch, "opts": self.model._meta,
            "labels": COUNT_LABELS,
            "status_url": reverse("admin:analytics_testdatabatch_status", args=[batch.pk]),
        }
        return TemplateResponse(request, "admin/analytics/testdatabatch/progress.html", context)

    def status_view(self, request, pk):
        """Polled by the progress page; returns the live counters as JSON."""
        batch = self.get_object(request, pk)
        if batch is None:
            return JsonResponse({"error": "not found"}, status=404)
        return JsonResponse({
            "status": batch.status, "stage": batch.progress_stage, "message": batch.message,
            "users": batch.progress_users, "orders": batch.progress_orders,
            "target_users": batch.target_users, "percent": batch.percent,
            "finished": not batch.is_running,
            "counts": [{"label": label, "value": batch.counts[key]}
                       for key, label in COUNT_LABELS if batch.counts.get(key)],
        })

    def delete_data_view(self, request, pk=None):
        if not self._guard(request):
            messages.error(request, "Deleting test data requires a superuser account.")
            return redirect("admin:analytics_testdatabatch_changelist")
        batch = self.get_object(request, pk) if pk else None
        if pk and batch is None:
            return redirect("admin:analytics_testdatabatch_changelist")
        counts = count_test_data(batch)
        if request.method == "POST":
            removed = delete_test_data(batch)
            messages.success(request, f"Deleted {removed['users']:,} generated users, {removed['orders']:,} orders "
                                      f"and {removed['product_events']:,} events. Real data was not touched.")
            return redirect("admin:analytics_testdatabatch_changelist")
        context = {
            **self.admin_site.each_context(request),
            "title": "Delete generated test data", "batch": batch, "opts": self.model._meta,
            "counts": [(label, counts[key]) for key, label in COUNT_LABELS if counts.get(key)],
            "total": sum(counts.values()),
        }
        return render(request, "admin/analytics/testdatabatch/confirm_delete.html", context)

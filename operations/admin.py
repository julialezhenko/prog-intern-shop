from django.contrib import admin

from .models import (Campaign, CampaignDailyMetric, Inventory, InventoryMovement, InventorySnapshot,
                     ProductEvent, PurchaseOrder, PurchaseOrderItem, Supplier, SupplierProduct, Transfer,
                     Warehouse)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "variant", "physical", "reserved", "available", "incoming", "damaged")
    list_filter = ("warehouse",)
    search_fields = ("variant__sku", "variant__product__name")
    autocomplete_fields = ("variant",)
    list_select_related = ("warehouse", "variant__product")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "country", "active")
    list_filter = ("active", "country")
    search_fields = ("code", "name", "city")


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "inventory", "kind", "quantity", "reference_type", "reference_id")
    list_filter = ("kind", "inventory__warehouse")
    search_fields = ("reference_id", "inventory__variant__sku")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in InventoryMovement._meta.fields]

    def has_add_permission(self, request):
        return False


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    autocomplete_fields = ("variant",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "warehouse", "status", "expected_delivery", "created_at")
    list_filter = ("status", "warehouse", "supplier")
    inlines = [PurchaseOrderItemInline]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "default_lead_days", "reliability_score", "active")
    list_filter = ("country", "active")
    search_fields = ("name",)


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ("supplier", "variant", "supplier_sku", "purchase_price", "lead_days", "minimum_order_quantity")
    search_fields = ("supplier_sku", "variant__sku")
    autocomplete_fields = ("variant",)


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "destination", "variant", "quantity", "status", "created_at")
    list_filter = ("status", "source", "destination")
    autocomplete_fields = ("variant",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "medium", "start_date", "end_date", "spend", "active")
    list_filter = ("source", "medium", "active")
    search_fields = ("name", "utm_campaign")


@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "customer", "product", "source", "device")
    list_filter = ("kind", "source")
    search_fields = ("session_id", "customer__username", "product__name")
    date_hierarchy = "created_at"
    raw_id_fields = ("customer", "product", "campaign")


@admin.register(CampaignDailyMetric)
class CampaignDailyMetricAdmin(admin.ModelAdmin):
    list_display = ("date", "campaign", "spend", "currency", "impressions", "clicks", "sessions", "new_customers")
    list_filter = ("campaign", "currency", "is_test_data")
    date_hierarchy = "date"


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "warehouse", "variant", "physical", "reserved", "incoming", "damaged", "unit_cost")
    list_filter = ("warehouse", "snapshot_date", "is_test_data")
    search_fields = ("variant__sku",)
    date_hierarchy = "snapshot_date"
    raw_id_fields = ("variant",)

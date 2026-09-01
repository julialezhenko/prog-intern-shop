from django.db.models import F
from rest_framework import permissions, response, viewsets

from config.api import DatasetPagination, IsAnalyst

from .filters import (CampaignFilter, CampaignMetricFilter, InventoryFilter, InventorySnapshotFilter, MovementFilter,
                      ProductEventFilter, PurchaseOrderFilter, TransferFilter)
from .models import (Campaign, CampaignDailyMetric, Inventory, InventoryMovement, InventorySnapshot, ProductEvent,
                     PurchaseOrder, Supplier, SupplierProduct, Transfer, Warehouse)
from .serializers import (CampaignMetricSerializer, CampaignSerializer, InventorySerializer,
                          InventorySnapshotSerializer, MovementSerializer, POSerializer, ProductEventSerializer,
                          ReorderSerializer, SupplierProductSerializer, SupplierSerializer, TransferSerializer,
                          WarehouseSerializer)


class StaffWrite(permissions.BasePermission):
    def has_permission(self, r, v): return r.method in permissions.SAFE_METHODS or r.user.is_staff


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all(); serializer_class = WarehouseSerializer; permission_classes = [StaffWrite]
    filterset_fields = ["active", "country_code", "market", "city"]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["code", "name", "opened_on"]


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inventory.objects.select_related("variant__product", "warehouse").order_by("id")
    serializer_class = InventorySerializer
    filterset_class = InventoryFilter
    pagination_class = DatasetPagination
    ordering_fields = ["physical", "reserved", "incoming", "damaged"]


class MovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryMovement.objects.select_related("inventory__warehouse", "inventory__variant").order_by("-created_at")
    serializer_class = MovementSerializer
    filterset_class = MovementFilter
    pagination_class = DatasetPagination
    ordering_fields = ["created_at", "quantity"]


class InventorySnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """Weekly stock levels, so stock value and cover can be tracked over time."""
    queryset = InventorySnapshot.objects.select_related("warehouse", "variant__product").order_by("-snapshot_date")
    serializer_class = InventorySnapshotSerializer
    filterset_class = InventorySnapshotFilter
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    ordering_fields = ["snapshot_date", "physical", "reserved"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all(); serializer_class = SupplierSerializer; permission_classes = [StaffWrite]
    filterset_fields = ["active", "country", "country_code", "currency"]
    search_fields = ["name", "contact_name"]
    ordering_fields = ["name", "reliability_score", "default_lead_days"]


class SupplierProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierProduct.objects.select_related("supplier", "variant__product").order_by("id")
    serializer_class = SupplierProductSerializer
    pagination_class = DatasetPagination
    filterset_fields = ["supplier", "variant", "is_preferred", "currency"]
    ordering_fields = ["purchase_price", "lead_days"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier", "warehouse").prefetch_related("items")
    serializer_class = POSerializer; permission_classes = [StaffWrite]
    filterset_class = PurchaseOrderFilter
    pagination_class = DatasetPagination
    ordering_fields = ["created_at", "expected_delivery", "received_at"]
    search_fields = ["reference", "supplier__name"]


class TransferViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transfer.objects.select_related("source", "destination", "variant").order_by("-created_at", "-id")
    serializer_class = TransferSerializer
    filterset_class = TransferFilter
    pagination_class = DatasetPagination
    ordering_fields = ["created_at", "quantity"]


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all(); serializer_class = CampaignSerializer; permission_classes = [StaffWrite]
    filterset_class = CampaignFilter
    ordering_fields = ["start_date", "end_date", "spend", "name"]
    search_fields = ["name", "utm_campaign", "source"]


class CampaignMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """Daily spend, impressions and clicks per campaign — the raw media table."""
    queryset = CampaignDailyMetric.objects.select_related("campaign").order_by("-date")
    serializer_class = CampaignMetricSerializer
    filterset_class = CampaignMetricFilter
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    ordering_fields = ["date", "spend", "clicks", "impressions", "sessions"]


class ProductEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Raw behavioural events. Filter and aggregate them yourself — no funnel rates are served here."""
    queryset = ProductEvent.objects.select_related("product", "variant", "campaign").order_by("-created_at", "-id")
    serializer_class = ProductEventSerializer
    filterset_class = ProductEventFilter
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    ordering_fields = ["created_at", "kind", "value"]
    search_fields = ["session_id", "search_term", "landing_page"]


class ReorderViewSet(viewsets.ViewSet):
    serializer_class = ReorderSerializer

    def list(self, request):
        rows = Inventory.objects.filter(
            physical__lte=F("variant__product__reorder_point") + F("reserved")).select_related("variant__product", "warehouse")
        return response.Response([{"variant": r.variant.sku, "warehouse": r.warehouse.code, "available": r.available,
                                   "recommended": r.variant.product.preferred_reorder_quantity} for r in rows])

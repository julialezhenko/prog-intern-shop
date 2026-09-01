from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CampaignMetricViewSet, CampaignViewSet, InventorySnapshotViewSet, InventoryViewSet,
                    MovementViewSet, ProductEventViewSet, PurchaseOrderViewSet, ReorderViewSet,
                    SupplierProductViewSet, SupplierViewSet, TransferViewSet, WarehouseViewSet)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet)
router.register("inventory", InventoryViewSet)
router.register("movements", MovementViewSet)
router.register("suppliers", SupplierViewSet)
router.register("purchase-orders", PurchaseOrderViewSet)
router.register("campaigns", CampaignViewSet)
router.register("reorder", ReorderViewSet, basename="reorder")
# Reporting datasets
router.register("events", ProductEventViewSet, basename="event")
router.register("campaign-metrics", CampaignMetricViewSet, basename="campaign-metric")
router.register("inventory-snapshots", InventorySnapshotViewSet, basename="inventory-snapshot")
router.register("supplier-products", SupplierProductViewSet, basename="supplier-product")
router.register("transfers", TransferViewSet, basename="transfer")

urlpatterns = [path("", include(router.urls))]

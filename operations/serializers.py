from rest_framework import serializers

from .models import (Campaign, CampaignDailyMetric, Inventory, InventoryMovement, InventorySnapshot, ProductEvent,
                     PurchaseOrder, PurchaseOrderItem, Supplier, SupplierProduct, Transfer, Warehouse)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta: model = Warehouse; fields = "__all__"


class InventorySerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True); sku = serializers.CharField(source="variant.sku", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    class Meta: model = Inventory; fields = "__all__"


class MovementSerializer(serializers.ModelSerializer):
    class Meta: model = InventoryMovement; fields = "__all__"


class InventorySnapshotSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    class Meta: model = InventorySnapshot; fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta: model = Supplier; fields = "__all__"


class SupplierProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    class Meta: model = SupplierProduct; fields = "__all__"


class POItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    class Meta: model = PurchaseOrderItem; fields = "__all__"


class POSerializer(serializers.ModelSerializer):
    items = POItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    class Meta: model = PurchaseOrder; fields = "__all__"


class TransferSerializer(serializers.ModelSerializer):
    class Meta: model = Transfer; fields = "__all__"


class CampaignSerializer(serializers.ModelSerializer):
    class Meta: model = Campaign; fields = "__all__"


class CampaignMetricSerializer(serializers.ModelSerializer):
    """Raw daily media figures. CTR, CPC, CPM, ROAS and CAC are intentionally not included."""
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    channel_group = serializers.CharField(source="campaign.channel_group", read_only=True)
    source = serializers.CharField(source="campaign.source", read_only=True)
    class Meta: model = CampaignDailyMetric; fields = "__all__"


class ProductEventSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    category_id = serializers.IntegerField(source="product.category_id", read_only=True, default=None)
    sku = serializers.CharField(source="variant.sku", read_only=True, default=None)
    class Meta: model = ProductEvent; fields = "__all__"


class ReorderSerializer(serializers.Serializer):
    variant = serializers.CharField(); warehouse = serializers.CharField(); available = serializers.IntegerField(); recommended = serializers.IntegerField()

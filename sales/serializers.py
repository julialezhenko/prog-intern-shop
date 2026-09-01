from rest_framework import serializers

from catalog.models import ProductVariant

from .models import (Cart, CartItem, Discount, DiscountRedemption, Order, OrderHistory, OrderItem,
                     Payment, Refund, ReturnRequest, Shipment, Subscription, SubscriptionEvent)
from .services import SHIPPING_FIELDS


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    unit_price = serializers.DecimalField(source="variant.effective_price", max_digits=12, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "cart", "variant", "sku", "product_name", "quantity", "unit_price", "line_total"]
        read_only_fields = ["cart"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount_code = serializers.CharField(source="discount.code", read_only=True, default=None)

    class Meta:
        model = Cart
        fields = ["id", "customer", "active", "discount", "discount_code", "items", "subtotal", "created_at", "updated_at"]
        read_only_fields = ["customer", "active", "discount"]


class AddItemSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.select_related("product"))
    quantity = serializers.IntegerField(min_value=1, default=1)


class RemoveItemSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())


class DiscountCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    """Optional shipping snapshot; every field is optional so existing API clients keep working."""
    shipping_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    shipping_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    shipping_country = serializers.CharField(max_length=80, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    customer_note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class OrderItemSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True, default=None)

    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_username = serializers.CharField(source="customer.username", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True, default=None)
    item_count = serializers.IntegerField(read_only=True, default=None,
                                          help_text="Number of order lines; only present on list endpoints.")

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["customer", "status", "warehouse", "subtotal", "discount_amount", "tax_amount", "total",
                            "fraud_score", "source", "access_token", *SHIPPING_FIELDS]


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderHistory
        fields = "__all__"


class ShipmentSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True, default=None)

    class Meta:
        model = Shipment
        fields = "__all__"


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"


class SubscriptionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionEvent
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    customer_username = serializers.CharField(source="customer.username", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["is_test_data", "test_batch"]


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = "__all__"


class DiscountRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountRedemption
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["gateway", "card_last4", "message"]


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class PaySerializer(serializers.Serializer):
    """Either pass card details (processed by the configured gateway) or, for simulations, a forced outcome."""
    success = serializers.BooleanField(required=False)
    number = serializers.CharField(required=False, allow_blank=True)
    holder = serializers.CharField(required=False, allow_blank=True)
    expiry = serializers.CharField(required=False, allow_blank=True)
    cvc = serializers.CharField(required=False, allow_blank=True)


class WebhookSerializer(serializers.Serializer):
    reference = serializers.CharField()
    status = serializers.ChoiceField(choices=["SUCCEEDED", "FAILED"])
    message = serializers.CharField(required=False, allow_blank=True, default="")


class ReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequest
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None and not request.user.is_staff:
            for name in ("status", "refund_amount", "restock", "damaged"):
                fields[name].read_only = True
        return fields

    def validate(self, attrs):
        request = self.context["request"]
        item = attrs.get("order_item") or getattr(self.instance, "order_item", None)
        if item is not None:
            if not request.user.is_staff and item.order.customer_id != request.user.id:
                raise serializers.ValidationError({"order_item": "You can only return items from your own orders."})
            quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
            if quantity is not None and quantity > item.quantity:
                raise serializers.ValidationError({"quantity": f"You ordered only {item.quantity} unit(s)."})
            if self.instance is None and item.order.status not in {"DELIVERED", "RETURNED"}:
                raise serializers.ValidationError({"order_item": "Returns can be requested only for delivered orders."})
        return attrs

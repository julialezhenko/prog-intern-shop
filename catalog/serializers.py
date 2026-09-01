from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (Brand, Category, PriceHistory, Product, ProductImage, ProductStatusHistory,
                     ProductVariant, Review, Tag, Wishlist)


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "product_count"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "group", "description", "product_count"]


class VariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "name", "attributes", "price", "effective_price", "available_quantity", "active"]


class ProductImageSerializer(serializers.ModelSerializer):
    src = serializers.CharField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image", "url", "src", "alt_text", "primary", "position"]

    def validate(self, attrs):
        image = attrs.get("image", getattr(self.instance, "image", None))
        url = attrs.get("url", getattr(self.instance, "url", ""))
        if not image and not url:
            raise serializers.ValidationError("Provide an uploaded image or an image URL.")
        return attrs


class ProductSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    tag_slugs = serializers.SlugRelatedField(source="tags", slug_field="slug", many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    @extend_schema_field(OpenApiTypes.URI)
    def get_primary_image_url(self, obj):
        image = obj.primary_image
        return image.src if image else None


class ReviewSerializer(serializers.ModelSerializer):
    customer = serializers.HiddenField(default=serializers.CurrentUserDefault())
    customer_name = serializers.CharField(source="customer.username", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "customer", "customer_name", "product", "order", "title", "rating", "comment", "status",
                  "channel", "language", "country_code", "helpful_votes", "verified_purchase",
                  "moderated_at", "responded_at", "created_at"]
        read_only_fields = ["verified_purchase", "status", "created_at", "moderated_at", "responded_at",
                            "helpful_votes"]


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = "__all__"


class ProductStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductStatusHistory
        fields = "__all__"


class WishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ["id", "products"]

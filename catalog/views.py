from django.db.models import Count, F, Q
from rest_framework import decorators, permissions, response, viewsets

from config.api import DatasetPagination

from .filters import ProductFilter, ProductStatusHistoryFilter, ReviewFilter
from .models import Brand, Category, PriceHistory, Product, ProductImage, ProductStatusHistory, Review, Tag, Wishlist
from .serializers import (BrandSerializer, CategorySerializer, PriceHistorySerializer, ProductImageSerializer,
                          ProductSerializer, ProductStatusHistorySerializer, ReviewSerializer, TagSerializer,
                          WishlistSerializer)
from .storefront_views import storefront  # noqa: F401  (kept for backwards compatibility)


class StaffWritePermission(permissions.BasePermission):
    """Anyone may read the catalog; only staff may change it."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or bool(request.user and request.user.is_staff)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [StaffWritePermission]
    filterset_class = ProductFilter
    pagination_class = DatasetPagination
    search_fields = ["name", "sku", "description", "tasting_notes", "origin", "producer", "variants__sku"]
    ordering_fields = ["sale_price", "purchase_cost", "name", "created_at", "launched_at"]
    lookup_field = "pk"

    @decorators.action(detail=True, methods=["get"], serializer_class=PriceHistorySerializer)
    def price_history(self, request, pk=None):
        """Every recorded sale-price change for this product."""
        return response.Response(PriceHistorySerializer(self.get_object().price_history.all(), many=True).data)

    @decorators.action(detail=True, methods=["get"], serializer_class=ProductStatusHistorySerializer)
    def status_history(self, request, pk=None):
        """When the product moved between draft, active and discontinued."""
        return response.Response(ProductStatusHistorySerializer(self.get_object().status_history.all(), many=True).data)

    def get_queryset(self):
        qs = (Product.objects.select_related("brand", "category")
              .prefetch_related("variants", "images", "tags").order_by("id"))
        user = self.request.user
        if not (user and user.is_staff):
            qs = qs.storefront()  # drafts and discontinued products are a staff-only concern
        # min_price / max_price / category_slug are declared on ProductFilter; availability needs a join.
        params = self.request.query_params
        if params.get("availability") in {"1", "true", "in_stock"}:
            qs = qs.filter(variants__inventory__physical__gt=F("variants__inventory__reserved")).distinct()
        return qs


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related("product")
    serializer_class = ProductImageSerializer
    permission_classes = [StaffWritePermission]
    filterset_fields = ["product", "primary"]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(
        product_count=Count("products", filter=Q(products__active=True, products__status="ACTIVE")))
    serializer_class = CategorySerializer
    permission_classes = [StaffWritePermission]
    search_fields = ["name"]


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [StaffWritePermission]
    search_fields = ["name"]


class TagViewSet(viewsets.ModelViewSet):
    """Merchandising labels — a segmentation dimension that overlaps categories instead of replacing them."""

    queryset = Tag.objects.annotate(
        product_count=Count("products", filter=Q(products__active=True, products__status="ACTIVE"))).order_by("group", "name")
    serializer_class = TagSerializer
    permission_classes = [StaffWritePermission]
    filterset_fields = ["group"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "group", "product_count"]


class ProductStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue lifecycle changes, so 'what was on sale in March' is answerable."""

    queryset = ProductStatusHistory.objects.select_related("product").order_by("-changed_at", "-id")
    serializer_class = ProductStatusHistorySerializer
    permission_classes = [StaffWritePermission]
    pagination_class = DatasetPagination
    filterset_class = ProductStatusHistoryFilter
    ordering_fields = ["changed_at"]


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Price changes over time — needed to explain revenue moves that volume alone does not."""

    queryset = PriceHistory.objects.select_related("product").order_by("-changed_at", "-id")
    serializer_class = PriceHistorySerializer
    permission_classes = [StaffWritePermission]
    pagination_class = DatasetPagination
    filterset_fields = ["product"]
    ordering_fields = ["changed_at", "new_price"]


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_class = ReviewFilter
    pagination_class = DatasetPagination
    ordering_fields = ["created_at", "rating", "helpful_votes"]
    search_fields = ["title", "comment", "product__name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        qs = Review.objects.select_related("product", "customer")
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(status="APPROVED") | Q(customer=self.request.user))


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Wishlist.objects.none()
        return Wishlist.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

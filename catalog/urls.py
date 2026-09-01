from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (BrandViewSet, CategoryViewSet, PriceHistoryViewSet, ProductImageViewSet,
                    ProductStatusHistoryViewSet, ProductViewSet, ReviewViewSet, TagViewSet, WishlistViewSet)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("categories", CategoryViewSet)
router.register("brands", BrandViewSet)
router.register("tags", TagViewSet)
router.register("reviews", ReviewViewSet, basename="review")
router.register("wishlist", WishlistViewSet, basename="wishlist")
router.register("price-history", PriceHistoryViewSet, basename="price-history")
router.register("product-status-history", ProductStatusHistoryViewSet, basename="product-status-history")

urlpatterns = [path("", include(router.urls))]

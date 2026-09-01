from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import CustomerProfileViewSet, CustomerSegmentHistoryViewSet, NewsletterSubscriberViewSet

router = DefaultRouter()
router.register("profiles", CustomerProfileViewSet, basename="customer-profile")
router.register("segment-history", CustomerSegmentHistoryViewSet, basename="customer-segment-history")
router.register("newsletter-subscribers", NewsletterSubscriberViewSet, basename="newsletter-subscriber")

urlpatterns = [path("", include(router.urls))]

"""Customer dimension endpoints. Read-only, analyst role, never exposed to the storefront."""
from django_filters import rest_framework as filters
from rest_framework import decorators, response, viewsets

from config.api import CsvChoiceFilter, DatasetPagination, IsAnalyst, date_range

from .models import CustomerProfile, CustomerSegmentHistory, NewsletterSubscriber
from .serializers import (CustomerProfileSerializer, CustomerSegmentHistorySerializer,
                          NewsletterSubscriberSerializer)


class CustomerProfileFilter(filters.FilterSet):
    segment = CsvChoiceFilter(field_name="segment")
    lifecycle_stage = CsvChoiceFilter(field_name="lifecycle_stage")
    loyalty_tier = CsvChoiceFilter(field_name="loyalty_tier")
    country_code = CsvChoiceFilter(field_name="country_code")
    market = CsvChoiceFilter(field_name="market")
    acquisition_source = CsvChoiceFilter(field_name="acquisition_source")
    acquisition_channel_group = CsvChoiceFilter(field_name="acquisition_channel_group")
    acquisition_campaign = CsvChoiceFilter(field_name="acquisition_campaign")
    signup_device = CsvChoiceFilter(field_name="signup_device")
    has_segment = filters.BooleanFilter(field_name="segment", lookup_expr="exact", exclude=True,
                                        method="filter_has_segment", label="Only rows where a segment is filled in")
    locals().update(date_range("registered_at", "Registered"))
    locals().update(date_range("first_seen_at", "First seen"))
    locals().update(date_range("last_activity_at", "Last active"))

    class Meta:
        model = CustomerProfile
        fields = ["is_guest", "is_test_data", "marketing_opt_in", "preferred_language", "default_currency"]

    def filter_has_segment(self, queryset, name, value):
        return queryset.exclude(segment="") if value else queryset.filter(segment="")


class CustomerProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerProfile.objects.select_related("user").order_by("-registered_at", "-id")
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    filterset_class = CustomerProfileFilter
    ordering_fields = ["registered_at", "first_seen_at", "last_activity_at", "birth_year"]
    search_fields = ["user__username", "user__email", "city", "company_name"]

    @decorators.action(detail=True, methods=["get"], serializer_class=CustomerSegmentHistorySerializer)
    def history(self, request, pk=None):
        """CRM attribute changes for one customer."""
        rows = self.get_object().segment_history.all()
        return response.Response(CustomerSegmentHistorySerializer(rows, many=True).data)


class CustomerSegmentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerSegmentHistory.objects.select_related("profile__user").order_by("-changed_at", "-id")
    serializer_class = CustomerSegmentHistorySerializer
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    filterset_fields = ["field", "old_value", "new_value", "profile"]
    ordering_fields = ["changed_at"]


class NewsletterSubscriberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsletterSubscriber.objects.order_by("-created_at")
    serializer_class = NewsletterSubscriberSerializer
    permission_classes = [IsAnalyst]
    pagination_class = DatasetPagination
    filterset_fields = ["active", "source", "medium", "campaign", "country_code"]
    ordering_fields = ["created_at", "confirmed_at"]
    search_fields = ["email"]

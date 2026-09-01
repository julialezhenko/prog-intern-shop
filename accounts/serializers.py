from rest_framework import serializers

from .models import CustomerProfile, CustomerSegmentHistory, NewsletterSubscriber


class CustomerProfileSerializer(serializers.ModelSerializer):
    """The customer dimension: geography, acquisition and segmentation, ready to join onto orders.

    Deliberately free of aggregates — order counts, revenue, recency and lifetime value are for the
    reader to compute from the order datasets.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta:
        model = CustomerProfile
        fields = "__all__"


class CustomerSegmentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegmentHistory
        fields = "__all__"


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = "__all__"

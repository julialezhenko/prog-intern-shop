"""Filter sets for the catalogue datasets."""
from django_filters import rest_framework as filters

from config.api import CsvChoiceFilter, CsvNumberFilter, date_range

from .models import Product, ProductStatusHistory, Review


class ProductFilter(filters.FilterSet):
    category = CsvNumberFilter(field_name="category_id")
    category_slug = CsvChoiceFilter(field_name="category__slug")
    brand = CsvNumberFilter(field_name="brand_id")
    kind = CsvChoiceFilter(field_name="kind")
    status = CsvChoiceFilter(field_name="status")
    roast_level = CsvChoiceFilter(field_name="roast_level")
    process = CsvChoiceFilter(field_name="process")
    origin_country_code = CsvChoiceFilter(field_name="origin_country_code")
    tag = CsvChoiceFilter(field_name="tags__slug", label="One or more tag slugs, comma separated")
    min_price = filters.NumberFilter(field_name="sale_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="sale_price", lookup_expr="lte")
    locals().update(date_range("created_at", "Created"))

    class Meta:
        model = Product
        fields = ["active", "featured", "is_limited", "is_seasonal"]


class ReviewFilter(filters.FilterSet):
    status = CsvChoiceFilter(field_name="status")
    rating = CsvNumberFilter(field_name="rating")
    channel = CsvChoiceFilter(field_name="channel")
    country_code = CsvChoiceFilter(field_name="country_code")
    category = CsvNumberFilter(field_name="product__category_id")
    min_rating = filters.NumberFilter(field_name="rating", lookup_expr="gte")
    max_rating = filters.NumberFilter(field_name="rating", lookup_expr="lte")
    answered = filters.BooleanFilter(field_name="responded_at", lookup_expr="isnull", exclude=True)
    locals().update(date_range("created_at", "Written"))

    class Meta:
        model = Review
        fields = ["product", "verified_purchase", "order"]


class ProductStatusHistoryFilter(filters.FilterSet):
    to_status = CsvChoiceFilter(field_name="to_status")
    locals().update(date_range("changed_at", "Changed"))

    class Meta:
        model = ProductStatusHistory
        fields = ["product"]

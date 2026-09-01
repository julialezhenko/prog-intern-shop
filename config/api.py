"""Cross-app API building blocks: pagination, roles and filter helpers.

Kept in ``config`` because catalog, sales, operations, accounts and analytics all need the same
conventions — one place to change how every dataset endpoint paginates and who may read it.
"""
from django_filters import rest_framework as filters
from rest_framework import pagination, permissions


class DatasetPagination(pagination.PageNumberPagination):
    """Page-number pagination that lets an analyst pull larger slices for an extract.

    ``?page_size=`` is honoured up to 2 000 rows; without it the shop-wide default applies.
    """

    page_size_query_param = "page_size"
    max_page_size = 2000


class IsAnalyst(permissions.BasePermission):
    """Staff, or a member of one of the reporting groups."""

    message = "An analyst, manager or staff account is required to read this dataset."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_staff or user.groups.filter(
            name__in=["Analyst", "Admin", "Store Manager", "Marketing Manager"]).exists()


class StaffWriteOnly(permissions.BasePermission):
    """Anybody authenticated may read; only staff may change."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or bool(request.user and request.user.is_staff)


class CsvChoiceFilter(filters.BaseInFilter, filters.CharFilter):
    """``?status=PAID,SHIPPED`` — comma separated values on one query parameter."""


class CsvNumberFilter(filters.BaseInFilter, filters.NumberFilter):
    """``?category=1,4,9``."""


def date_range(field, label=None):
    """The pair of bounds every fact table exposes for one of its timestamps."""
    label = label or field.replace("_", " ")
    return {
        f"{field}_after": filters.IsoDateTimeFilter(field_name=field, lookup_expr="gte",
                                                    label=f"{label} on or after (ISO date/datetime)"),
        f"{field}_before": filters.IsoDateTimeFilter(field_name=field, lookup_expr="lte",
                                                     label=f"{label} on or before (ISO date/datetime)"),
    }


def day_range(field, label=None):
    """Same idea for plain ``DateField`` columns."""
    label = label or field.replace("_", " ")
    return {
        f"{field}_after": filters.DateFilter(field_name=field, lookup_expr="gte", label=f"{label} on or after"),
        f"{field}_before": filters.DateFilter(field_name=field, lookup_expr="lte", label=f"{label} on or before"),
    }


def with_filters(base, *extra_dicts, **extra):
    """Compose a FilterSet class body from ``date_range``/``day_range`` fragments."""
    attrs = {}
    for fragment in extra_dicts:
        attrs.update(fragment)
    attrs.update(extra)
    return type(base.__name__, (base,), attrs)

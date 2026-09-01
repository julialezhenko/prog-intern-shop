from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import AuditLog, CustomerProfile, CustomerSegmentHistory, NewsletterSubscriber


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    extra = 0


class UserAdmin(DjangoUserAdmin):
    inlines = [CustomerProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country_code", "market", "city", "segment", "lifecycle_stage", "loyalty_tier",
                    "acquisition_channel_group", "acquisition_source", "marketing_opt_in", "is_test_data",
                    "registered_at")
    list_filter = ("segment", "lifecycle_stage", "loyalty_tier", "market", "country_code",
                   "acquisition_channel_group", "acquisition_source", "marketing_opt_in", "is_guest", "is_test_data")
    search_fields = ("user__username", "user__email", "city", "company_name")
    raw_id_fields = ("user",)
    date_hierarchy = "registered_at"


@admin.register(CustomerSegmentHistory)
class CustomerSegmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("changed_at", "profile", "field", "old_value", "new_value", "reason")
    list_filter = ("field", "new_value")
    search_fields = ("profile__user__username",)
    date_hierarchy = "changed_at"
    raw_id_fields = ("profile",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity", "entity_id")
    list_filter = ("action", "entity")
    search_fields = ("entity_id", "actor__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "medium", "campaign", "country_code", "active", "confirmed_at", "created_at")
    list_filter = ("active", "source", "medium", "country_code")
    search_fields = ("email",)
    actions = ["unsubscribe"]

    @admin.action(description="Unsubscribe selected addresses")
    def unsubscribe(self, request, queryset):
        self.message_user(request, f"{queryset.update(active=False)} address(es) unsubscribed.")

from django.contrib.admin.apps import AdminConfig


class CommerceLabAdminConfig(AdminConfig):
    default_site = "config.admin.CommerceLabAdminSite"

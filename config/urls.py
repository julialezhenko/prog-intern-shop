from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("rest_framework.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/catalog/", include("catalog.urls")),
    path("api/customers/", include("accounts.api_urls")),
    path("api/sales/", include("sales.urls")),
    path("api/operations/", include("operations.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("sales.storefront_urls")),
    path("", include("catalog.storefront_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

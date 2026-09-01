from django.contrib.sitemaps.views import sitemap
from django.urls import path

from . import storefront_views as views
from .sitemaps import SITEMAPS

urlpatterns = [
    path("", views.storefront, name="storefront"),
    path("catalog/", views.product_list, name="product_list"),
    path("catalog/category/<slug:category_slug>/", views.product_list, name="category_detail"),
    path("catalog/<slug:slug>/", views.product_detail, name="product_detail"),
    path("catalog/<slug:slug>/review/", views.review_create, name="review_create"),
    path("newsletter/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("about/", views.about, name="about"),
    path("shipping-returns/", views.shipping_returns, name="shipping_returns"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", views.robots_txt, name="robots"),
]

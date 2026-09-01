from django.contrib.sitemaps import Sitemap
from django.db.models import Count, Q
from django.urls import reverse

from .models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.storefront().order_by("id")

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return (Category.objects.annotate(n=Count("products", filter=Q(products__active=True, products__status="ACTIVE")))
                .filter(n__gt=0).order_by("id"))


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ["storefront", "product_list", "about", "shipping_returns"]

    def location(self, item):
        return reverse(item)


SITEMAPS = {"products": ProductSitemap, "categories": CategorySitemap, "pages": StaticSitemap}

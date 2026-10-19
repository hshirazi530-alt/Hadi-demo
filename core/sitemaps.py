from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from core.models import Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https" if not settings.DEBUG else "http"
    domain = settings.SITE_DOMAIN

    def items(self):
        return Product.objects.filter(
            product_status="published",
            status=True,
        ).order_by("pid")

    def location(self, item):
        return reverse("core:product-detail", args=[item.pid])

    def lastmod(self, item):
        return item.updated or item.date


class StorePagesSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https" if not settings.DEBUG else "http"
    domain = settings.SITE_DOMAIN

    def items(self):
        return (
            "core:index",
            "core:product-list",
            "core:category-list",
            "core:about_us",
            "core:contact",
            "core:purchase_guide",
            "core:privacy_policy",
            "core:terms_of_service",
        )

    def location(self, item):
        return reverse(item)

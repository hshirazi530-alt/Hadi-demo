from decimal import Decimal
import re
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from core.catalog_inquiry import catalog_items, catalog_by_id, featured_items
from core.models import Product


class InquiryCatalogTests(TestCase):
    def setUp(self):
        self.sample = Product.objects.create(
            title="کالای نمایشی (نمونه)", product_status="published", status=True,
            in_stock=True, featured=True, price=Decimal("800000"), image="sample.jpg",
        )

    def homepage_product_section(self, response):
        html = response.content.decode("utf-8")
        found = re.search(r'<section\b[^>]*\bid="products"[^>]*>.*?</section>', html, re.S)
        self.assertIsNotNone(found)
        return found.group(0)

    def test_dataset_is_minimal_and_images_are_registered(self):
        rows = catalog_items()
        self.assertEqual(len(rows), 689)
        self.assertEqual(len({row["id"] for row in rows}), 689)
        self.assertTrue({8460, 15839, 15857, 15849}.issubset({row["id"] for row in rows if row["image"]}))
        from pathlib import Path
        from django.conf import settings
        for row in rows:
            if row["image"]:
                self.assertTrue((Path(settings.BASE_DIR) / "static" / row["image"]).is_file(), row["title"])
        self.assertFalse(any(set(row) & {"price", "stock", "in_stock", "sale_price", "description", "url", "gallery"} for row in rows))
        self.assertEqual(catalog_by_id()[8460]["title"], "مخلوط‌کن مدل TF-67")
        self.assertEqual(catalog_by_id()[15839]["title"], "اپیلیدی DSP 70019U")
        self.assertEqual([row["id"] for row in featured_items(2)], [15839, 8460])

    def test_homepage_sample_is_not_shown_in_target_section(self):
        before = Product.objects.count()
        response = self.client.get(reverse("core:index"))
        section = self.homepage_product_section(response)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.sample.title, section)
        self.assertEqual(section.count('class="swiper-slide hm-product-card beauty-product-card hm-inquiry-card"'), 12)
        self.assertNotIn("product-cart-btn", section)
        self.assertIn("قیمت و موجودی در انتظار تأیید", section)
        self.assertEqual(Product.objects.count(), before)
        self.assertTrue(Product.objects.filter(pk=self.sample.pk).exists())

    def test_existing_published_real_product_remains_buyable_and_unchanged(self):
        actual = Product.objects.create(
            title="کالای واقعی تست", product_status="published", status=True,
            in_stock=True, featured=True, price=Decimal("1234567"), image="actual.jpg",
        )
        with patch('core.photo_visibility.has_product_photo', return_value=True):
            response = self.client.get(reverse("core:index"))
        section = self.homepage_product_section(response)
        self.assertIn(actual.title, section)
        self.assertIn('data-product-price="1234567"', section)
        self.assertIn("product-cart-btn", section)
        self.assertNotIn(self.sample.title, section)
        self.assertEqual(section.count('class="swiper-slide hm-product-card beauty-product-card hm-inquiry-card"'), 11)
        actual.refresh_from_db()
        self.assertEqual(actual.price, Decimal("1234567"))
        self.assertTrue(actual.in_stock)
        self.assertEqual(actual.product_status, "published")

    def test_list_is_read_only_noindexed_paginated_and_searchable(self):
        response = self.client.get(reverse("core:catalog-inquiry-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(response, '<meta name="robots" content="noindex,nofollow">', html=True)
        self.assertEqual(response.context["total_count"], sum(bool(row["image"]) for row in catalog_items()))
        self.assertEqual(len(response.context["items"]), 24)
        self.assertContains(response, "قیمت، موجودی، اصالت و مشخصات این کالاها تأیید نشده")
        self.assertNotContains(response, "product-cart-btn")
        second = self.client.get(reverse("core:catalog-inquiry-list"), {"page": "2"})
        self.assertEqual(second.context["page_obj"].number, 2)
        result = self.client.get(reverse("core:catalog-inquiry-list"), {"q": "70019U"})
        self.assertEqual(result.context["total_count"], 1)
        self.assertContains(result, "اپیلیدی DSP 70019U")
        self.assertEqual(self.client.post(reverse("core:catalog-inquiry-list")).status_code, 405)

    def test_detail_is_inquiry_only_and_not_an_existing_product_cart(self):
        url = reverse("core:catalog-inquiry-detail", args=[15839])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(response, "تعداد عملکرد در حال بررسی است")
        main = re.search(r'<main class="hm-review-shell".*?</main>', response.content.decode("utf-8"), re.S).group(0)
        self.assertNotIn("product-cart-btn", main)
        self.assertNotIn("data-product-id", main)
        self.assertNotIn("تومان", main)
        self.assertNotIn("افزودن به سبد", main)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(reverse("core:catalog-inquiry-detail", args=[99999999])).status_code, 404)

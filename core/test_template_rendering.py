from django.test import TestCase
from django.urls import reverse


class StorefrontTemplateRenderingTests(TestCase):
    """Smoke tests for the public storefront templates and URL wiring."""

    def test_homepage_renders(self):
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هژیر مارکت")

    def test_category_directory_renders(self):
        response = self.client.get(reverse("core:category-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دسته‌بندی")

    def test_product_list_renders(self):
        response = self.client.get(reverse("core:product-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "محصول")

    def test_static_template_assets_are_referenced(self):
        response = self.client.get(reverse("core:index"))
        self.assertNotContains(response, "We're waiting to hear from you")
        self.assertNotContains(response, "I'm here for you")

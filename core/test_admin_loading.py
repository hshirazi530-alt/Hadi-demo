from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminLoadingTemplateTests(TestCase):
    def test_admin_page_renders_branded_loader_and_admin_assets(self):
        admin_user = get_user_model().objects.create_user(
            username="admin-loading-test",
            email="admin-loading-test@example.com",
            password="test-password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="hjm-admin-loader"')
        self.assertContains(response, "assets/imgs/theme/hejrmarket-logo.png")
        self.assertContains(response, "در حال بارگذاری پنل مدیریت")
        self.assertContains(response, "/static/css/admin-rtl.css")
        self.assertContains(response, "/static/js/admin-loading.js")

    def test_storefront_does_not_render_admin_loader(self):
        response = self.client.get(reverse("core:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="hjm-admin-loader"')

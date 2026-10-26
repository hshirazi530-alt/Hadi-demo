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
        self.assertContains(response, "larkon-admin")
        self.assertContains(response, 'class="main-sidebar')
        self.assertContains(response, 'id="hjm-admin-loader"')
        self.assertContains(response, "assets/imgs/theme/hejrmarket-logo-192.png")
        self.assertContains(response, "در حال بارگذاری پنل مدیریت")
        self.assertContains(response, "/static/css/admin-rtl.css")
        self.assertEqual(response.content.count(b"/static/css/admin-rtl.css"), 1)
        self.assertContains(response, "/static/js/admin-loading.js")

    def test_admin_login_loads_shared_persian_assets(self):
        response = self.client.get(reverse("admin:login"))

        # The public login screen renders through Jazzmin's own shell, which only
        # pulls the single JAZZMIN_SETTINGS["custom_css"] file (the luxury light
        # theme). The full RTL stack is injected by templates/admin/base_site.html
        # for authenticated pages, so it is asserted on the index response above.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hazhirmarket")
        self.assertContains(response, '<html lang="fa-ir" dir="rtl">')
        self.assertContains(response, "/static/css/admin-luxury-light.css")
        self.assertEqual(response.content.count(b"/static/css/admin-luxury-light.css"), 1)
        self.assertContains(response, "/static/js/admin-loading.js")
        self.assertNotContains(response, "fonts.googleapis.com")

    def test_storefront_does_not_render_admin_loader(self):
        response = self.client.get(reverse("core:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="hjm-admin-loader"')

from pathlib import Path

from django.conf import settings
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

        # Jazzmin loads a single custom CSS file on login. It imports the
        # original luxury theme and adds the RTL redesign without losing it.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hazhirmarket")
        self.assertContains(response, '<html lang="fa-ir" dir="rtl">')
        self.assertContains(response, "/static/css/admin-jazzmin-rtl.css", count=1)
        self.assertContains(response, 'placeholder="ایمیل"')
        self.assertContains(response, 'placeholder="گذرواژه"')
        self.assertNotContains(response, 'placeholder="Email"')
        jazzmin_css = (Path(settings.BASE_DIR) / 'static/css/admin-jazzmin-rtl.css').read_text(encoding='utf8')
        self.assertIn('@import url("admin-luxury-light.css")', jazzmin_css)
        self.assertContains(response, "/static/js/admin-loading.js")
        self.assertNotContains(response, "fonts.googleapis.com")

    def test_admin_login_still_authenticates_with_email_and_password(self):
        admin = get_user_model().objects.create_user(
            username="login-check", email="login-check@example.com", password="test-password",
            is_staff=True, is_superuser=True,
        )
        response = self.client.post(reverse("admin:login"), {
            "username": admin.email, "password": "test-password", "next": reverse("admin:index"),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), admin.pk)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_admin_login_shows_error_for_wrong_credentials(self):
        response = self.client.post(reverse("admin:login"), {
            "username": "not-a-user@example.com", "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "callout-danger")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_storefront_does_not_render_admin_loader(self):
        response = self.client.get(reverse("core:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="hjm-admin-loader"')

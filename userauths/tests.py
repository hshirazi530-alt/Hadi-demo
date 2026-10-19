from django.test import TestCase
from django.urls import reverse

from userauths.models import User


class AuthenticationRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cart-customer",
            email="cart-customer@example.com",
            password="safe-test-password",
        )

    def test_login_returns_to_the_cart_after_authentication(self):
        response = self.client.post(
            f"{reverse('userauths:sign-in')}?next={reverse('core:cart')}",
            {
                "email": self.user.email,
                "password": "safe-test-password",
                "next": reverse("core:cart"),
            },
        )

        self.assertRedirects(response, reverse("core:cart"))

    def test_login_rejects_external_next_redirect(self):
        response = self.client.post(
            reverse("userauths:sign-in"),
            {
                "email": self.user.email,
                "password": "safe-test-password",
                "next": "https://example.invalid/",
            },
        )

        self.assertRedirects(response, reverse("core:index"))

    def test_authenticated_user_is_returned_to_safe_next_destination(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("userauths:sign-in"),
            {"next": reverse("core:cart")},
        )

        self.assertRedirects(response, reverse("core:cart"))

    def test_registration_preserves_the_cart_destination(self):
        cart_path = reverse("core:cart")
        registration_page = self.client.get(
            reverse("userauths:sign-up"),
            {"next": cart_path},
        )
        self.assertContains(registration_page, f'name="next" value="{cart_path}"')

        response = self.client.post(
            f"{reverse('userauths:sign-up')}?next={cart_path}",
            {
                "username": "new-cart-customer",
                "email": "new-cart-customer@example.com",
                "password1": "Cart-Test-Password-2026!",
                "password2": "Cart-Test-Password-2026!",
                "next": cart_path,
            },
        )

        self.assertRedirects(response, cart_path)

from django.test import TestCase
from django.urls import reverse

class StoreEmailTests(TestCase):
    def test_contact_email_is_clickable_on_public_pages(self):
        for name in ('core:index', 'core:contact', 'core:about_us'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'href="mailto:markethazhir@gmail.com"')
                self.assertNotContains(response, 'info@hejrmarket.com')

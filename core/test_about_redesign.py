from django.test import TestCase
from django.urls import reverse

class AboutRedesignTests(TestCase):
    def test_page_renders_and_uses_webp(self):
        response = self.client.get(reverse('core:about_us'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'about-hazhir-task8.webp')
        self.assertContains(response, 'about-hazhir-task8.css')
        self.assertContains(response, 'آنچه ما ارائه می‌دهیم')
        self.assertContains(response, 'هژیر مارکت')
        self.assertContains(response, '<bdi dir="ltr">+۱۲</bdi><span>هزار</span>')
        self.assertContains(response, 'Hazhirmarket')
        self.assertNotContains(response, 'Hazhirmarkett')
        self.assertContains(response, '<bdi dir="ltr">٪۹۸</bdi>')

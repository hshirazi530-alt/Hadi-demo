import re
from pathlib import Path
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

@override_settings(GOFTINO_WIDGET_ID='')
class ChatPreviewTests(TestCase):
    def test_contact_widget_is_local_and_has_safe_links(self):
        response=self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code,200)
        html=response.content.decode();section=html.split('<div class="hm-helper"',1)[1].split('<!-- End mobile header -->',1)[0]
        self.assertIn('mailto:markethazhir@gmail.com',section)
        self.assertIn('data-helper-mobile',section)
        self.assertIn('required maxlength="9"',section)
        self.assertIn('hm-chat-mobile-error',section)
        self.assertIn('pattern="[0-9]{9}"',section)
        self.assertIn('<bdi dir="ltr">+989</bdi>',section)
        self.assertIn('گفت‌وگوی زنده و ارسال پیام در آن فعال نیست',section)
        self.assertNotIn('href="tel:',section)
        self.assertIn('instagram.com/hazhir_markett',section)
        self.assertIn('t.me/hazhir_markett',section)
        self.assertIn('wa.me/989186555100',section)
    def test_digit_normalization_and_limit(self):
        source=(Path(settings.BASE_DIR)/'static/js/stages-8-14.js').read_text()
        self.assertIn("replace(/[^0-9]/g, '').slice(0, 9)",source)
        self.assertIn('data-helper-mobile',source)

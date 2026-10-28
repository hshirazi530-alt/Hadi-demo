from pathlib import Path
import re

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class StageFivePreloaderTests(TestCase):
    def test_style_is_loaded_after_store_style_without_replacing_the_logo(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        store = re.search(r'/static/css/store\.css(?:\?v=\d+)?', html)
        stage = '/static/css/preloader-stage5.css?v=1'
        self.assertIsNotNone(store)
        self.assertEqual(html.count(stage), 1)
        self.assertLess(store.start(), html.index(stage))
        self.assertIn('id="hm-preloader"', html)
        self.assertIn('role="status" aria-live="polite"', html)
        self.assertIn('/static/assets/imgs/theme/hejrmarket-loading-gold.png', html)
        self.assertIn('<noscript><style>#hm-preloader{display:none !important;}</style></noscript>', html)

    def test_style_is_scoped_and_keeps_the_failure_and_accessibility_fallbacks(self):
        path = finders.find('css/preloader-stage5.css')
        self.assertTrue(path)
        css = Path(path).read_text(encoding='utf-8')
        self.assertIn('.store-css #hm-preloader', css)
        self.assertIn('#fff8dc', css.lower())
        self.assertIn('#f5f5dc', css.lower())
        self.assertIn('#d4af37', css.lower())
        self.assertIn('#ffd700', css.lower())
        self.assertIn('animation: hm-stage5-dismiss 720ms ease 3.6s forwards;', css)
        self.assertIn('@keyframes hm-stage5-dismiss', css)
        self.assertIn('pointer-events: none;', css)
        self.assertIn('@media (max-height: 360px)', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (forced-colors: active)', css)
        self.assertNotIn('url(http', css.lower())

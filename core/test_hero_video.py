from pathlib import Path
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

class HeroVideoTests(TestCase):
    def test_slide_is_in_hero_and_has_user_controls(self):
        response=self.client.get(reverse('core:index'))
        self.assertContains(response,'data-hero-video-slide')
        self.assertContains(response,'data-swiper-autoplay="11000"')
        self.assertContains(response,'data-hero-video muted playsinline loop')
        self.assertContains(response,'data-video-sound')
        self.assertContains(response,'data-video-play')
        self.assertContains(response,'hero-feature.mp4')
        self.assertContains(response,'hero-feature-poster.webp')
        self.assertContains(response,'hero-video-slide.js')
        self.assertTrue((Path(settings.BASE_DIR)/'static/assets/video/hero-feature.mp4').exists())

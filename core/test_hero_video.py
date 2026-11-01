from pathlib import Path
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from core.models import HeroBanner

class HeroVideoTests(TestCase):
    def test_slide_is_in_hero_and_has_user_controls(self):
        response=self.client.get(reverse('core:index'))
        self.assertContains(response,'data-hero-video-slide')
        self.assertContains(response,'data-swiper-autoplay="11000"')
        self.assertContains(response,'data-hero-video muted playsinline loop')
        self.assertNotContains(response,'data-video-sound')
        self.assertContains(response,'data-video-play')
        self.assertContains(response,'آراستگی،')
        self.assertContains(response,'در هر لحظه')
        slide = response.content.decode('utf-8').split('data-hero-video-slide', 1)[1].split('</article>', 1)[0]
        self.assertIn('href="/products/"', slide)
        self.assertIn('href="/category/"', slide)
        self.assertContains(response,'hero-feature-1.mp4')
        self.assertContains(response,'hero-feature-1-poster.webp')
        self.assertContains(response,'hero-video-slide.js')
        self.assertTrue((Path(settings.BASE_DIR)/'static/assets/video/hero-feature-1.mp4').exists())

    def test_video_is_first_slide(self):
        response = self.client.get(reverse('core:index'))
        html = response.content.decode('utf-8')
        slides = html.split('<div class="swiper-wrapper hm-hero__slides">', 1)[1]
        self.assertIn('data-hero-video-slide', slides.split('</article>', 1)[0])

    def test_only_selected_banner_image_is_replaced_and_actions_preserved(self):
        HeroBanner.objects.create(title='ابزارهای مراقبت شخصی مردانه', image='storefront/banners/barber-hero.jpg', button_label='دیدن محصولات', button_url='/products/')
        HeroBanner.objects.create(title='بنر دیگر', image='storefront/banners/other.jpg', button_label='لینک دیگر', button_url='/category/')
        html = self.client.get(reverse('core:index')).content.decode('utf-8')
        selected = html.split('home-appliances-slide-2.webp', 1)[1].split('</article>', 1)[0]
        self.assertIn('خانه‌ای زیباتر', selected)
        self.assertIn('زندگی آسان‌تر', selected)
        self.assertIn('لوازم خانه و آشپزخانه', selected)
        self.assertIn('دیدن محصولات', selected)
        self.assertIn('href="/products/"', selected)
        self.assertIn('همهٔ دسته‌بندی‌ها', selected)
        self.assertIn('/media/storefront/banners/other.jpg', html)
        self.assertNotIn('/media/storefront/banners/barber-hero.jpg', html)

    def test_two_new_slides_are_independent_and_have_links(self):
        html = self.client.get(reverse('core:index')).content.decode('utf-8')
        self.assertEqual(html.count('data-hero-video-slide'), 2)
        self.assertIn('care-slide-3.webp', html)
        self.assertIn('hero-feature-4.mp4', html)
        self.assertIn('hm-hero-video__original-text-mask', html)
        for marker in ('data-hero-care-slide', 'data-hero-barber-slide'):
            slide = html.split(marker, 1)[1].split('</article>', 1)[0]
            self.assertIn('href="/products/"', slide)
            self.assertIn('href="/category/"', slide)
        self.assertTrue((Path(settings.BASE_DIR) / 'static/assets/video/hero-feature-4.mp4').is_file())

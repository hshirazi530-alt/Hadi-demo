from django.test import override_settings as legacy_photo_policy
from pathlib import Path

from PIL import Image
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from core.models import Category, DigitalBanner, HeroBanner, Product
from core.navigation import invalidate_nav_cache
from core.storefront import HOME_CATEGORIES


# Legacy rendering checks exercise the explicitly supported fallback mode.
@legacy_photo_policy(HIDE_PRODUCTS_WITHOUT_PHOTO=False)
class HeroShowcaseTests(TestCase):
    def setUp(self):
        # A data migration may pre-create a digital category in test databases.
        Category.objects.all().delete()
        invalidate_nav_cache()
        self.addCleanup(invalidate_nav_cache)

    @staticmethod
    def hero_html(response):
        html = response.content.decode("utf-8")
        return html.split('<div class="swiper-wrapper hm-hero__slides">', 1)[1].split(
            '<nav class="hm-hero__controls"', 1
        )[0]

    def test_original_active_banner_slides_remain_first_and_untouched(self):
        digital = DigitalBanner.objects.create(
            title="بنر دیجیتال قبلی", button_label="دکمهٔ دیجیتال", button_url="/products/", sort_order=2
        )
        first = HeroBanner.objects.create(
            title="بنر قدیمی اول", button_label="دکمهٔ اول", button_url="/search/?q=one", sort_order=1
        )
        second = HeroBanner.objects.create(title="بنر قدیمی دوم", sort_order=2)
        HeroBanner.objects.create(title="نباید دیده شود", is_active=False)

        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 200)
        html = self.hero_html(response)
        expected = ["بنر دیجیتال قبلی", "بنر قدیمی اول", "بنر قدیمی دوم", 'data-hero-showcase="personal"', 'data-hero-showcase="digital"']
        offsets = [html.index(item) for item in expected]
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(html.count('<article class="swiper-slide hm-hero__slide'), 6)
        self.assertNotIn("نباید دیده شود", html)
        self.assertIn('href="/search/?q=one">دکمهٔ اول</a>', html)
        digital.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((digital.title, digital.button_url, digital.sort_order), ("بنر دیجیتال قبلی", "/products/", 2))
        self.assertEqual((first.title, first.button_url, first.sort_order), ("بنر قدیمی اول", "/search/?q=one", 1))
        self.assertEqual(second.title, "بنر قدیمی دوم")

    def test_existing_fallback_slides_are_preserved_before_both_new_slides(self):
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 200)
        html = self.hero_html(response)
        self.assertEqual(html.count('<article class="swiper-slide hm-hero__slide'), len(HOME_CATEGORIES) + 3)
        for category in HOME_CATEGORIES:
            self.assertIn(category["hero_title"], html)
            self.assertLess(html.index(category["hero_title"]), html.index('data-hero-showcase="personal"'))
        self.assertEqual(html.count('data-hero-showcase="personal"'), 1)
        self.assertEqual(html.count('data-hero-showcase="digital"'), 1)

    def test_links_use_actual_header_category_ids_and_reach_correct_products(self):
        personal = Category.objects.create(title="لوازم شخصی")
        digital = Category.objects.create(title="قطعات و لوازم دیجیتال")
        Product.objects.create(title="محصول شخصی آزمایشی", category=personal, product_status="published", status=True)
        Product.objects.create(title="محصول دیجیتال آزمایشی", category=digital, product_status="published", status=True)
        invalidate_nav_cache()

        response = self.client.get(reverse("core:index"))
        html = self.hero_html(response)
        for key, category, product in (
            ("personal", personal, "محصول شخصی آزمایشی"),
            ("digital", digital, "محصول دیجیتال آزمایشی"),
        ):
            with self.subTest(slide=key):
                url = reverse("core:category-product-list", args=[category.cid])
                slide = html.split(f'data-hero-showcase="{key}"', 1)[1].split("</article>", 1)[0]
                self.assertIn(f'href="{url}"', slide)
                destination = self.client.get(url)
                self.assertEqual(destination.status_code, 200)
                self.assertContains(destination, product)
                self.assertEqual(destination.context["category"].pk, category.pk)

    def test_missing_category_falls_back_to_a_working_directory_link(self):
        personal = Category.objects.create(title="لوازم شخصی")
        invalidate_nav_cache()
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.context["hero_personal_category_url"], reverse("core:category-product-list", args=[personal.cid]))
        self.assertEqual(response.context["hero_digital_category_url"], reverse("core:category-list"))
        self.assertEqual(self.client.get(response.context["hero_digital_category_url"]).status_code, 200)
        # Do not invalidate the header cache: the slide still must not link
        # to a deleted category while that independent cache is warm.
        personal.delete()
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.context["hero_personal_category_url"], reverse("core:category-list"))

    def test_showcase_images_have_descriptive_alt_and_correct_dimensions(self):
        response = self.client.get(reverse("core:index"))
        html = self.hero_html(response)
        for name, alt, width, height in (
            ("hero-feature-personal-v2.webp", "مجموعه ماشین‌های اصلاح، محصولات مراقبت شخصی و عطر", 2400, 1187),
            ("hero-feature-digital-v2.webp", "لپ‌تاپ، تبلت، کنسول بازی، تلفن همراه و هدفون", 1568, 672),
        ):
            with self.subTest(image=name):
                asset = finders.find(f"assets/imgs/beauty/hero/{name}")
                self.assertTrue(asset)
                self.assertTrue(Path(asset).is_file())
                with Image.open(asset) as image:
                    self.assertEqual(image.format, "WEBP")
                    self.assertEqual(image.size, (width, height))
                self.assertIn(f'/{name}" alt="{alt}" width="{width}" height="{height}" loading="lazy"', html)
        self.assertNotIn('/hero-feature-digital.jpg"', html)
        self.assertNotIn('/hero-feature-personal.jpg"', html)
        self.assertIn('اصلاح دقیق،<br><span>آراستگی بی‌نقص</span>', html)

    def test_all_hero_images_fill_slides_without_a_scrim(self):
        css = Path(finders.find("css/store.css")).read_text(encoding="utf-8")
        self.assertIn(
            ".store-css .hm-hero .hm-hero__slide .hm-hero__media {\n"
            "  inset: 0;\n}",
            css,
        )
        self.assertIn("  object-fit: cover;", css)
        self.assertIn(
            ".store-css .hm-hero .hm-hero__slide .hm-hero__media::after {\n"
            "  content: none;\n}",
            css,
        )
        response = self.client.get(reverse("core:index"))
        self.assertEqual(self.hero_html(response).count('class="hm-hero__copy"'), 2)

    def test_all_slides_share_transparent_bottom_right_copy(self):
        css = Path(finders.find("css/store.css")).read_text(encoding="utf-8")
        selector = ".store-css .hm-hero .hm-hero__slide "
        content = css.split(selector + ".hm-hero__content {", 1)[1].split("}", 1)[0]
        copy = css.split(selector + ".hm-hero__copy {", 1)[1].split("}", 1)[0]
        self.assertIn("position: absolute;", content)
        self.assertIn("inset: 0;", content)
        self.assertIn("align-items: flex-start;", content)
        self.assertIn("overflow-y: auto;", content)
        self.assertIn("margin-block-start: auto;", css)
        self.assertIn("background: transparent;", copy)
        self.assertIn("border: 0;", copy)
        self.assertIn("box-shadow: none;", copy)
        self.assertIn("backdrop-filter: none;", copy)
        self.assertIn("direction: rtl;", content)
        self.assertIn("text-align: right;", content)

    def test_long_admin_banner_copy_is_not_truncated(self):
        title = "ماشین اصلاح حرفه‌ای " * 7
        description = "مراقبت و آراستگی روزانه با انتخاب شخصی شما. " * 16
        HeroBanner.objects.create(title=title, description=description, button_label="مشاهده محصولات")
        response = self.client.get(reverse("core:index"))
        self.assertContains(response, title)
        self.assertContains(response, description)

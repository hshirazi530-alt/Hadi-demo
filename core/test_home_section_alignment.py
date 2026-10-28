from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from core.models import Product
from core.storefront import HOME_CATEGORIES


class HomeSectionAlignmentTests(TestCase):
    def test_categories_and_empty_products_keep_their_content(self):
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        categories = html.split('<section class="beauty-section beauty-categories"', 1)[1].split('</section>', 1)[0]
        products = html.split('<section class="beauty-section featured-products"', 1)[1].split('</section>', 1)[0]
        self.assertIn('id="categories-title"', categories)
        self.assertEqual(categories.count('class="category-card category-card--'), len(HOME_CATEGORIES))
        self.assertIn('id="products-title"', products)
        self.assertIn('class="swiper-slide hm-product-card beauty-product-card hm-inquiry-card"', products)
        self.assertIn('قیمت و موجودی در انتظار تأیید', products)
        self.assertNotIn('data-product-price=', products)
        self.assertIn('/static/css/store.css?v=100', html)

    def test_product_slider_and_category_links_still_render(self):
        Product.objects.create(
            title="محصول آزمایشی", image="", product_status="published", status=True
        )
        response = self.client.get(reverse("core:index"))
        self.assertContains(response, 'data-product-slider')
        self.assertContains(response, 'محصول آزمایشی')
        self.assertContains(response, reverse("core:search") + '?q=')

    def test_css_uses_the_same_gutter_and_responsive_grid_inset(self):
        stylesheet = finders.find("css/store.css")
        self.assertTrue(stylesheet)
        css = Path(stylesheet).read_text(encoding="utf-8")
        marker = '/* Task 4: align the home category grid with the latest-products slider. */'
        self.assertEqual(css.count(marker), 1)
        block = css.split(marker, 1)[1]
        self.assertIn('.home-page > .beauty-categories,', block)
        self.assertIn('.home-page > .featured-products {', block)
        self.assertIn('padding-inline: clamp(16px, 4vw, 64px);', block)
        self.assertIn('width: min(1200px, 100%);', block)
        self.assertIn('gap: 18px;', block)
        self.assertIn('padding-inline: 2px;', block)
        refinement = '/* Task 4 refinement: align every homepage section with the product slider.'
        self.assertEqual(css.count(refinement), 1)
        aligned = css.split(refinement, 1)[1]
        self.assertIn('section:not(.beauty-slider):not(.beauty-categories):not(.featured-products):not(.hm-amazing)', aligned)
        self.assertIn('width: calc(100% - clamp(32px, 8vw, 128px));', aligned)
        self.assertIn('.featured-products > .beauty-section__heading {', aligned)
        self.assertIn('width: 100%;', aligned)
        self.assertIn('.hm-promo-strip > .hm-promo-strip__grid {', aligned)
        self.assertIn('.bundle-section .bundle-grid {', aligned)

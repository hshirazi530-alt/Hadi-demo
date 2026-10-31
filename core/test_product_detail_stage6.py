from django.test import override_settings as legacy_photo_policy
from decimal import Decimal
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from core.models import Category, Product, ProductImages


# Legacy rendering checks exercise the explicitly supported fallback mode.
@legacy_photo_policy(HIDE_PRODUCTS_WITHOUT_PHOTO=False)
class ProductDetailStageSixTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='دسته آزمایشی')
        self.product = Product.objects.create(
            title='محصول آزمایشی جزئیات', category=self.category, image='',
            product_status='published', status=True, in_stock=True,
            price=Decimal('1000'), sale_price=Decimal('800'), is_sale=True,
            has_warranty=True, warranty_6_price=Decimal('50'),
            authenticity_high_copy=True,
        )
        self.url = reverse('core:product-detail', args=[self.product.pid])

    def test_missing_image_is_safe_and_discount_is_correct(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'product-detail-stage6.css?v=1')
        self.assertContains(response, 'product-image-pending.webp')
        self.assertContains(response, '20٪ تخفیف')
        self.assertNotContains(response, '25٪ تخفیف')
        self.assertContains(response, 'data-product-image="/static/assets/imgs/theme/product-image-pending.webp"')
        self.assertContains(response, 'data-warranty-option')
        self.assertContains(response, 'data-authenticity-wrap')
        self.assertContains(response, 'data-product-tabs')
        self.assertContains(response, 'product-cart-btn')

    def test_empty_gallery_entry_does_not_break_product_page(self):
        ProductImages.objects.create(product=self.product, images='')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-gallery-thumb')

    def test_related_products_only_show_published_active_records(self):
        Product.objects.create(title='مرتبط منتشرشده', category=self.category, image='', product_status='published', status=True)
        Product.objects.create(title='مرتبط پیش‌نویس محرمانه', category=self.category, image='', product_status='draft', status=True)
        Product.objects.create(title='مرتبط غیرفعال محرمانه', category=self.category, image='', product_status='published', status=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مرتبط منتشرشده')
        self.assertNotContains(response, 'مرتبط پیش‌نویس محرمانه')
        self.assertNotContains(response, 'مرتبط غیرفعال محرمانه')

    def test_invalid_or_higher_sale_has_no_discount_percentage(self):
        self.product.sale_price = Decimal('1200')
        self.product.save(update_fields=['sale_price'])
        response = self.client.get(self.url)
        self.assertNotContains(response, '٪ تخفیف')
        self.product.sale_price = Decimal('1')
        self.product.save(update_fields=['sale_price'])
        response = self.client.get(self.url)
        self.assertContains(response, '99٪ تخفیف')
        self.assertNotContains(response, '100٪ تخفیف')

    def test_css_and_placeholder_are_local(self):
        stylesheet = Path(finders.find('css/product-detail-stage6.css'))
        self.assertTrue(stylesheet.is_file())
        css = stylesheet.read_text(encoding='utf-8')
        self.assertIn('.hm-product-detail-page', css)
        self.assertIn('.hm-product-tabs__panel[hidden]', css)
        self.assertIn('prefers-reduced-motion', css)
        self.assertNotIn('url(http', css.lower())
        self.assertTrue(Path(finders.find('assets/imgs/theme/product-image-pending.svg')).is_file())

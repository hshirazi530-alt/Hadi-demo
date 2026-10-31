from django.test import override_settings as legacy_photo_policy
from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import CartOrder, Category, FAQ, Product, SubCategory, Vendor
from core.admin import ProductAdminForm
from core.navigation import invalidate_nav_cache
from core.phone import normalize_iranian_mobile
from core.views import _cart_item
from useradmin.forms import AddProductForm
from userauths.models import ContactUs


class IranianMobileTests(TestCase):
    def test_accepted_forms_are_stored_in_legacy_domestic_format(self):
        for number in ('121234567', '۱۲۱۲۳۴۵۶۷', '١٢١٢٣٤٥٦٧', '09121234567',
                       '+989121234567', '989121234567', '00989121234567', '0912 123 4567'):
            with self.subTest(number=number):
                self.assertEqual(normalize_iranian_mobile(number), '09121234567')

    def test_incomplete_foreign_and_malformed_numbers_are_rejected(self):
        for number in ('', '12345678', '1234567890', '0912123456', '+98912123456',
                       '+4917612345678', '+989121234567x2', 'hello09121234567',
                       '++989121234567', '0912/123/4567'):
            with self.subTest(number=number), self.assertRaises(ValidationError):
                normalize_iranian_mobile(number)

    def test_contact_endpoint_validates_and_stores_suffix(self):
        url = reverse('core:ajax-contact-form')
        data = {'full_name': 'مشتری', 'phone': '۱۲۱۲۳۴۵۶۷', 'message': 'درخواست مشاوره'}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(ContactUs.objects.get().phone, '09121234567')
        for bad in ('', '12123456', '0912123456', 'foo123456789'):
            response = self.client.post(url, {**data, 'phone': bad})
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(ContactUs.objects.count(), 1)

    def test_checkout_rejects_invalid_phone_then_accepts_suffix(self):
        user = get_user_model().objects.create_user(username='customer', email='c@example.org', password='demo-pass')
        self.client.force_login(user)
        product = Product.objects.create(title='محصول تست', image='', price=Decimal('10000'),
                                         product_status='published', status=True, in_stock=True)
        session = self.client.session
        session['cart_data_obj'] = {str(product.id): _cart_item(product, 1, 0, 0)}
        session.save()
        payload = {'full_name': 'مشتری', 'email': 'c@example.org', 'mobile': '12123456',
                   'address': 'نشانی تست', 'city': 'بانه', 'state': 'کردستان', 'country': 'ایران'}
        self.client.post(reverse('core:save_checkout_info'), payload)
        self.assertEqual(CartOrder.objects.count(), 0)
        response = self.client.post(reverse('core:save_checkout_info'), {**payload, 'mobile': '121234567'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CartOrder.objects.get().phone, '09121234567')


# Legacy rendering checks exercise the explicitly supported fallback mode.
@legacy_photo_policy(HIDE_PRODUCTS_WITHOUT_PHOTO=False)
class FinalStageRenderingTests(TestCase):
    def setUp(self):
        invalidate_nav_cache()
        self.addCleanup(invalidate_nav_cache)
        self.category = Category.objects.create(title='لوازم شخصی')
        self.child = SubCategory.objects.create(category=self.category, title='زیرمجموعه فعال تست', is_active=True)
        self.hidden_child = SubCategory.objects.create(category=self.category, title='زیرمجموعه غیرفعال تست', is_active=False)
        self.product = Product.objects.create(title='کالای اصالت تست', category=self.category, image='',
                                              price=Decimal('10000'), product_status='published',
                                              status=True, in_stock=True)

    def test_home_banner_faq_social_and_mobile_navigation(self):
        FAQ.objects.create(question='سؤال تست بایگانی', answer='پاسخ تست', is_active=True)
        response = self.client.get(reverse('core:index'))
        html = response.content.decode()
        self.assertIn('id="hm-collection-banner"', html)
        self.assertNotIn('class="beauty-section faq-section"', html)
        self.assertEqual(FAQ.objects.count(), 1)
        header = html.split('<header class="header-area', 1)[1].split('</header>', 1)[0]
        footer = html.split('<footer', 1)[1].split('</footer>', 1)[0]
        self.assertIn('class="hm-header-social"', header)
        self.assertIn('https://t.me/hazhir_markett', header)
        self.assertIn('https://instagram.com/hazhir_markett', header)
        self.assertIn('https://wa.me/989186555100', header)
        self.assertNotIn('hm-footer__social-row', footer)
        mobile = html.split('aria-label="منوی موبایل"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('زیرمجموعه فعال تست', mobile)
        self.assertNotIn('زیرمجموعه غیرفعال تست', mobile)
        self.assertIn('hm-mobile-cat-icon', mobile)
        self.assertIn('<button type="button" class="burger-icon burger-icon-white"', html)
        self.assertIn('data-iran-mobile-suffix', html)
        self.assertIn('data-shopping-assistant', html)

    def test_missing_photos_use_neutral_placeholder_in_catalog(self):
        self.product.is_sale = True
        self.product.sale_price = Decimal('5000')
        self.product.save(update_fields=['is_sale', 'sale_price'])
        pages = [
            (reverse('core:index'), {}),
            (reverse('core:product-list'), {}),
            (reverse('core:search'), {'q': self.product.title}),
            (reverse('core:category-product-list', args=[self.category.cid]), {}),
        ]
        for url, query in pages:
            with self.subTest(url=url):
                response = self.client.get(url, query)
                self.assertContains(response, self.product.title)
                # Homepage retains the SVG fallback; the other pages use WebP.
                expected = 'product-image-pending.svg' if url == reverse('core:index') else 'product-image-pending.webp'
                self.assertContains(response, expected)
                if url != reverse('core:index'):
                    self.assertNotContains(response, 'assets/imgs/beauty/barber-shop.jpg')
                else:
                    self.assertNotContains(response, 'assets/imgs/beauty/hero/hair-model.webp')

    def test_authenticity_never_claimed_without_single_explicit_selection(self):
        detail = reverse('core:product-detail', args=[self.product.pid])
        self.assertNotContains(self.client.get(detail), 'data-authenticity-wrap')
        self.product.authenticity_high_copy = True
        self.product.save(update_fields=['authenticity_high_copy'])
        response = self.client.get(detail)
        self.assertContains(response, 'data-authenticity-wrap')
        self.assertContains(response, 'های‌کپی')
        self.product.authenticity_original = True
        self.product.save(update_fields=['authenticity_original'])
        self.assertNotContains(self.client.get(detail), 'data-authenticity-wrap')
        self.product.refresh_from_db()
        self.assertTrue(self.product.authenticity_original)
        self.assertTrue(self.product.authenticity_high_copy)

    def test_custom_admin_selects_one_state_and_legacy_requests_preserve_it(self):
        data = {'title': self.product.title, 'price': '10000', 'sale_price': '0',
                'product_status': 'published', 'status': 'on', 'in_stock': 'on',
                'category': str(self.category.pk), 'authenticity_stage9_present': '1',
                'authenticity_level': 'high_copy'}
        form = AddProductForm(data, instance=self.product)
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertTrue(product.authenticity_high_copy)
        self.assertFalse(product.authenticity_original)
        data.pop('authenticity_stage9_present')
        data.pop('authenticity_level')
        legacy = AddProductForm(data, instance=product)
        self.assertTrue(legacy.is_valid(), legacy.errors)
        legacy.save()
        product.refresh_from_db()
        self.assertTrue(product.authenticity_high_copy)
        invalid = AddProductForm({**data, 'authenticity_stage9_present': '1', 'authenticity_level': 'invented'}, instance=product)
        self.assertFalse(invalid.is_valid())

    def test_django_admin_rejects_contradictory_authenticity(self):
        user = get_user_model().objects.create_user(username='admin', email='admin@example.org', password='demo-pass')
        vendor = Vendor.objects.create(title='فروشنده تست', user=user)
        self.product.user, self.product.vendor, self.product.image = user, vendor, 'product.jpg'
        self.product.save(update_fields=['user', 'vendor', 'image'])
        data = {'title': self.product.title, 'price': '10000', 'sale_price': '0',
                'product_status': 'published', 'status': 'on', 'in_stock': 'on',
                'pid': self.product.pid, 'user': str(user.pk), 'vendor': str(vendor.pk),
                'category': str(self.category.pk), 'sku': self.product.sku,
                'authenticity_original': 'on', 'authenticity_copy': 'on'}
        buf = BytesIO()
        Image.new('RGB', (24, 24), 'white').save(buf, format='PNG')
        image = SimpleUploadedFile('sample.png', buf.getvalue(), content_type='image/png')
        form = ProductAdminForm(data=data, files={'image': image}, instance=self.product)
        self.assertFalse(form.is_valid())
        self.assertIn('فقط یکی از وضعیت', str(form.non_field_errors()))

    @override_settings(GOFTINO_WIDGET_ID='AbC123')
    def test_goftino_is_opt_in_and_uses_validated_public_id(self):
        response = self.client.get(reverse('core:index'))
        self.assertContains(response, 'data-goftino-id="AbC123"')
        self.assertContains(response, 'goftino-loader.js')
        self.assertNotContains(response, 'data-shopping-assistant')

    @override_settings(GOFTINO_WIDGET_ID='bad\"><script>alert(1)</script>')
    def test_invalid_goftino_id_never_injects_script(self):
        response = self.client.get(reverse('core:index'))
        self.assertNotContains(response, 'goftino-loader.js')
        self.assertContains(response, 'data-shopping-assistant')

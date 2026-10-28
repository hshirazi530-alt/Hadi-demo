from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.admin import ProductAdminForm
from core.models import CartOrder, CartOrderProducts, Category, Product, Vendor


class WarrantyStageSevenTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='دسته گارانتی آزمایشی')
        self.product = Product.objects.create(
            title='کالای گارانتی آزمایشی', category=self.category, image='',
            price=Decimal('1000000'), sale_price=Decimal('800000'), is_sale=True,
            product_status='published', status=True, in_stock=True,
            has_warranty=True, warranty_6_price=Decimal('120000'),
            warranty_12_price=Decimal('200000'), warranty_24_price=Decimal('0'),
        )
        self.add_url = reverse('core:add-to-cart')
        self.cart_url = reverse('core:cart')
        self.checkout_url = reverse('core:save_checkout_info')
        self.customer = get_user_model().objects.create_user(username='warranty-customer', password='test-only')
        self.form = {'full_name':'مشتری آزمایشی','email':'test@example.org','mobile':'09186555100',
                     'address':'نشانی آزمایشی','city':'بانه','state':'کردستان','country':'ایران'}

    def add(self, months=0, qty=1, **extra):
        return self.client.post(self.add_url, {'id':self.product.id, 'qty':qty, 'warranty_months':months, **extra})

    def test_detail_options_and_no_warranty_when_disabled(self):
        url = reverse('core:product-detail', args=[self.product.pid])
        response = self.client.get(url)
        self.assertContains(response, 'value="6" data-warranty-option')
        self.assertContains(response, 'value="12" data-warranty-option')
        self.assertNotContains(response, 'value="24" data-warranty-option')
        self.assertContains(response, 'بدون هزینهٔ اضافه')
        self.assertContains(response, 'هزینهٔ انتخابی به قیمت هر عدد اضافه می‌شود')
        self.assertContains(response, 'aria-live="polite" aria-atomic="true"')
        self.product.has_warranty = False
        self.product.save(update_fields=['has_warranty'])
        response = self.client.get(url)
        self.assertNotContains(response, 'data-warranty-option')

    def test_database_price_and_per_unit_warranty_not_client_price(self):
        response = self.add(6, 2, price='1', warranty_price='1', expected_base_price='800000', expected_warranty_price='120000')
        self.assertEqual(response.status_code, 200)
        row = self.client.session['cart_data_obj'][f'{self.product.id}-w6']
        self.assertEqual(row['price'], '920000')
        self.assertEqual(row['base_price'], '800000')
        self.assertEqual(row['warranty_price'], '120000')
        self.assertEqual(row['qty'], 2)
        cart = self.client.get(self.cart_url)
        self.assertContains(cart, '1,840,000')
        self.assertContains(cart, 'گارانتی 6 ماه')
        self.assertContains(cart, 'برای هر عدد')

    def test_different_warranty_choices_are_separate_rows(self):
        self.assertEqual(self.add(0, 1).status_code, 200)
        self.assertEqual(self.add(6, 2).status_code, 200)
        self.assertEqual(self.add(12, 1).status_code, 200)
        self.assertEqual(self.add(6, 1).status_code, 200)
        cart = self.client.session['cart_data_obj']
        self.assertEqual(set(cart), {str(self.product.id), f'{self.product.id}-w6', f'{self.product.id}-w12'})
        self.assertEqual(cart[f'{self.product.id}-w6']['qty'], 3)
        response = self.client.post(reverse('core:update-cart'), {'id':f'{self.product.id}-w6','qty':4})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['cart_data_obj'][f'{self.product.id}-w6']['price'], '920000')
        self.assertEqual(self.client.session['cart_data_obj'][f'{self.product.id}-w6']['qty'], 4)
        response = self.client.post(reverse('core:delete-from-cart'), {'id':f'{self.product.id}-w12'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['cart_data_obj']), 2)

    def test_legacy_cart_warranty_is_not_overwritten_by_no_warranty(self):
        session = self.client.session
        session['cart_data_obj'] = {str(self.product.id): {'qty':2, 'warranty_months':6,
                                  'base_price':'800000', 'warranty_price':'120000'}}
        session.save()
        self.assertEqual(self.add(0).status_code, 200)
        cart = self.client.session['cart_data_obj']
        self.assertEqual(cart[str(self.product.id)]['warranty_months'], 6)
        self.assertEqual(cart[str(self.product.id)]['qty'], 2)
        self.assertEqual(cart[f'{self.product.id}-w0']['warranty_months'], 0)
        self.client.force_login(self.customer)
        self.client.post(self.checkout_url, self.form)
        order = CartOrder.objects.get(user=self.customer)
        self.assertEqual(order.price, Decimal('2640000'))
        self.assertEqual(set(CartOrderProducts.objects.filter(order=order).values_list('warranty_months', flat=True)), {0,6})

    def test_invalid_and_disabled_warranties_are_rejected(self):
        for value in ('24', '3', '-1', '6.0', 'nan'):
            with self.subTest(value=value):
                self.assertEqual(self.add(value).status_code, 409)
        self.assertEqual(self.client.session.get('cart_data_obj', {}), {})
        self.product.has_warranty = False
        self.product.save(update_fields=['has_warranty'])
        self.assertEqual(self.add(6).status_code, 409)
        self.assertEqual(self.add(0).status_code, 200)

    def test_stale_page_price_is_rejected(self):
        self.assertEqual(self.add(6, expected_base_price='800000', expected_warranty_price='1').status_code, 409)
        self.assertEqual(self.add(6, expected_base_price='1', expected_warranty_price='120000').status_code, 409)
        self.assertEqual(self.client.session.get('cart_data_obj', {}), {})

    def test_checkout_records_selected_warranty_and_preserves_snapshot(self):
        self.add(6, 2)
        self.client.force_login(self.customer)
        response = self.client.post(self.checkout_url, self.form)
        order = CartOrder.objects.get(user=self.customer)
        self.assertRedirects(response, reverse('core:checkout', args=[order.oid]))
        self.assertEqual(order.price, Decimal('1840000'))
        item = CartOrderProducts.objects.get(order=order)
        self.assertEqual((item.qty, item.price, item.total, item.warranty_months, item.warranty_price),
                         (2, Decimal('920000'), Decimal('1840000'), 6, Decimal('120000')))
        self.product.warranty_6_price = 500000
        self.product.save(update_fields=['warranty_6_price'])
        item.refresh_from_db()
        self.assertEqual(item.warranty_price, Decimal('120000'))
        checkout = self.client.get(reverse('core:checkout', args=[order.oid]))
        self.assertContains(checkout, 'گارانتی 6 ماه')
        self.assertContains(checkout, '120,000 تومان برای هر عدد')
        detail = self.client.get(reverse('core:order-detail', args=[order.id]))
        self.assertContains(detail, 'گارانتی 6 ماه')

    def test_changed_price_requires_cart_review_before_order(self):
        self.add(6, 2)
        self.client.force_login(self.customer)
        self.product.warranty_6_price = 150000
        self.product.save(update_fields=['warranty_6_price'])
        response = self.client.post(self.checkout_url, self.form)
        self.assertRedirects(response, self.cart_url, fetch_redirect_response=False)
        self.assertFalse(CartOrder.objects.filter(user=self.customer).exists())
        cart = self.client.get(self.cart_url)
        self.assertContains(cart, '1,900,000')
        self.assertContains(cart, 'قیمت کالا یا گارانتی تغییر کرده')
        response = self.client.post(self.checkout_url, self.form)
        order = CartOrder.objects.get(user=self.customer)
        self.assertEqual(order.price, Decimal('1900000'))
        self.assertRedirects(response, reverse('core:checkout', args=[order.oid]))

    def test_removed_option_keeps_row_and_blocks_checkout(self):
        self.add(6, 2)
        self.client.force_login(self.customer)
        self.product.warranty_6_price = 0
        self.product.save(update_fields=['warranty_6_price'])
        cart = self.client.get(self.cart_url)
        self.assertTrue(cart.context['has_warranty_issues'])
        self.assertContains(cart, 'گارانتی انتخاب‌شده دیگر در دسترس نیست')
        self.assertContains(cart, 'نیازمند بازبینی')
        self.assertNotContains(cart, 'جمع نمایشی: 1,600,000 تومان')
        self.assertEqual(self.client.post(reverse('core:update-cart'), {'id':f'{self.product.id}-w6','qty':3}).status_code, 409)
        self.assertRedirects(self.client.post(self.checkout_url, self.form), self.cart_url)
        self.assertFalse(CartOrder.objects.filter(user=self.customer).exists())
        self.assertEqual(self.client.post(reverse('core:delete-from-cart'), {'id':f'{self.product.id}-w6'}).status_code, 200)
        self.assertEqual(self.client.session['cart_data_obj'], {})

    def test_malformed_cart_option_does_not_silently_become_no_warranty(self):
        session = self.client.session
        session['cart_data_obj'] = {str(self.product.id): {'qty':1, 'warranty_months':'garbage'}}
        session.save()
        self.client.force_login(self.customer)
        cart = self.client.get(self.cart_url)
        self.assertTrue(cart.context['has_warranty_issues'])
        self.assertTrue(self.client.session['cart_data_obj'][str(self.product.id)]['warranty_unavailable'])
        self.assertTrue(self.client.get(self.cart_url).context['has_warranty_issues'])
        response = self.client.post(self.checkout_url, self.form)
        self.assertRedirects(response, self.cart_url, fetch_redirect_response=False)
        self.assertFalse(CartOrder.objects.filter(user=self.customer).exists())

    def test_cart_snapshot_tampering_cannot_set_price_or_warranty(self):
        self.add(6, 1)
        session = self.client.session
        row = session['cart_data_obj'][f'{self.product.id}-w6']
        row['price'] = '1'; row['warranty_price'] = '1'
        session.save()
        cart = self.client.get(self.cart_url)
        self.assertContains(cart, '920,000')
        self.assertEqual(self.client.session['cart_data_obj'][f'{self.product.id}-w6']['warranty_price'], '120000')

    def test_large_amount_fits_order_fields(self):
        self.product.is_sale=False; self.product.price=Decimal('2000000000')
        self.product.save(update_fields=['is_sale','price'])
        self.add(6, 2)
        self.client.force_login(self.customer)
        self.client.post(self.checkout_url, self.form)
        self.assertEqual(CartOrder.objects.get(user=self.customer).price, Decimal('4000240000'))

    def test_no_warranty_selection_still_works(self):
        self.add(0, 1)
        self.client.force_login(self.customer)
        self.client.post(self.checkout_url, self.form)
        item=CartOrderProducts.objects.get(order__user=self.customer)
        self.assertEqual(item.warranty_months, 0)
        self.assertEqual(item.warranty_price, 0)
        self.assertEqual(item.price, Decimal('800000'))

    def test_custom_admin_screen_saves_settings_and_legacy_edit_preserves_them(self):
        admin = get_user_model().objects.create_superuser(username='warranty-admin', email='a@example.org', password='test-only')
        self.client.force_login(admin)
        url = reverse('useradmin:dashboard-edit-products', args=[self.product.pid])
        response = self.client.get(url)
        self.assertContains(response, 'گارانتی اختیاری')
        self.assertContains(response, 'name="warranty_stage7_present"')
        data = {'title':self.product.title, 'description':'توضیحات', 'price':'1000000',
                'sale_price':'800000', 'is_sale':'on', 'stock_count':'10',
                'category':str(self.category.id), 'product_status':'published', 'status':'on', 'in_stock':'on',
                'warranty_stage7_present':'1', 'has_warranty':'on',
                'warranty_6_price':'75000', 'warranty_12_price':'160000', 'warranty_24_price':''}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
        self.product.refresh_from_db()
        self.assertTrue(self.product.has_warranty)
        self.assertEqual((self.product.warranty_6_price, self.product.warranty_12_price, self.product.warranty_24_price), (75000,160000,0))
        for key in ('warranty_stage7_present','has_warranty','warranty_6_price','warranty_12_price','warranty_24_price'):
            data.pop(key)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.product.refresh_from_db()
        self.assertTrue(self.product.has_warranty)
        self.assertEqual(self.product.warranty_6_price, 75000)
        data.update({'warranty_stage7_present':'1','has_warranty':'on','warranty_6_price':'-1'})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'هزینهٔ گارانتی نمی‌تواند منفی باشد')
        self.product.refresh_from_db()
        self.assertEqual(self.product.warranty_6_price, 75000)

    def test_admin_form_validation_and_empty_values(self):
        # Existing instance avoids the separate new-product gallery requirements.
        vendor = Vendor.objects.create(title='فروشندهٔ آزمایشی', user=self.customer)
        self.product.user = self.customer
        self.product.vendor = vendor
        self.product.image = 'product.jpg'
        self.product.save(update_fields=['user', 'vendor', 'image'])
        common = {'title':self.product.title, 'price':'1000000', 'sale_price':'800000',
                  'product_status':'published', 'status':'on', 'in_stock':'on',
                  'pid':self.product.pid, 'user':str(self.customer.id), 'vendor':str(vendor.id),
                  'category':str(self.category.id), 'sku':self.product.sku,
                  'has_warranty':'on', 'warranty_6_price':'50000', 'warranty_12_price':'',
                  'warranty_24_price':''}
        def bound_form(data):
            buffer = BytesIO()
            Image.new('RGB', (24, 24), 'white').save(buffer, format='PNG')
            upload = SimpleUploadedFile('sample.png', buffer.getvalue(), content_type='image/png')
            return ProductAdminForm(data=data, files={'image': upload}, instance=self.product)
        form = bound_form(common)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['warranty_12_price'], Decimal('0'))
        form = bound_form({**common,'warranty_6_price':'-1'})
        self.assertFalse(form.is_valid())
        self.assertIn('warranty_6_price', form.errors)
        form = bound_form({**common,'warranty_6_price':''})
        self.assertFalse(form.is_valid())
        self.assertIn('has_warranty', form.errors)

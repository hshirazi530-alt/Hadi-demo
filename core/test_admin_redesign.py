from decimal import Decimal
from io import BytesIO
import re
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from core.admin import ProductAdminForm
from core.models import CartOrder, Category, Product, SubCategory, Vendor
from useradmin.forms import AddProductForm


class RedesignTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='test-admin', email='test-admin@example.org', password='testPass$123456', is_staff=True, is_superuser=True)
        self.category = Category.objects.create(title='سلامت')
        self.product = Product.objects.create(user=self.admin, category=self.category, title='محصول آزمایشی', price=Decimal('10000'), product_status='published', status=True, in_stock=True, image='product.jpg')
        self.client.force_login(self.admin)

    def test_custom_panel_three_selected_states_and_clear(self):
        data = {'title':self.product.title, 'price':'10000', 'sale_price':'0', 'product_status':'published', 'status':'on', 'in_stock':'on', 'category':str(self.category.pk), 'authenticity_stage9_present':'1'}
        for chosen in ('original','high_copy','copy',''):
            form=AddProductForm({**data,'authenticity_level':chosen},instance=self.product)
            self.assertTrue(form.is_valid(),form.errors)
            form.save(); self.product.refresh_from_db()
            self.assertEqual([self.product.authenticity_original,self.product.authenticity_high_copy,self.product.authenticity_copy],[chosen=='original',chosen=='high_copy',chosen=='copy'])
            html=self.client.get(reverse('core:product-detail',args=[self.product.pid])).content.decode()
            panel=html.split('data-spec-authenticity',1)[1].split('</section>',1)[0]
            self.assertEqual(panel.count('type="radio"'),3)
            self.assertEqual(len(re.findall(r'\bchecked\b',panel)),int(bool(chosen)))
            if chosen:self.assertRegex(panel,rf'value="{chosen}"\s+checked')
            else:self.assertIn('ثبت یا تأیید نشده',panel)

    def test_conflicting_legacy_values_never_claim_authenticity(self):
        self.product.authenticity_original=True;self.product.authenticity_copy=True;self.product.save()
        html=self.client.get(reverse('core:product-detail',args=[self.product.pid])).content.decode()
        panel=html.split('data-spec-authenticity',1)[1].split('</section>',1)[0]
        self.assertNotIn(' checked',panel)
        self.assertNotIn('data-authenticity-wrap',html)

    def test_conflicting_legacy_state_requires_explicit_choice_before_edit(self):
        self.product.authenticity_original = True
        self.product.authenticity_copy = True
        self.product.save()
        data = {'title':self.product.title, 'price':'10000', 'sale_price':'0', 'product_status':'published', 'status':'on', 'in_stock':'on', 'category':str(self.category.pk), 'authenticity_stage9_present':'1'}
        form = AddProductForm(data, instance=self.product)
        self.assertFalse(form.is_valid())
        self.assertIn('authenticity_level', form.errors)
        self.product.refresh_from_db()
        self.assertTrue(self.product.authenticity_original and self.product.authenticity_copy)
        form = AddProductForm({**data, 'authenticity_level':''}, instance=self.product)
        self.assertTrue(form.is_valid(), form.errors)
        form.save(); self.product.refresh_from_db()
        self.assertFalse(self.product.authenticity_original or self.product.authenticity_copy)

    def test_manager_form_and_django_admin_offer_one_choice(self):
        url=reverse('useradmin:dashboard-edit-products',args=[self.product.pid])
        response=self.client.get(url)
        self.assertContains(response,'name="authenticity_level"',count=4)
        self.assertContains(response,'authenticity_stage9_present')
        admin_response=self.client.get(reverse('admin:core_product_change',args=[self.product.pk]))
        self.assertEqual(admin_response.status_code,200)
        self.assertContains(admin_response,'name="authenticity_level"',count=4)
        self.assertNotContains(admin_response,'name="authenticity_original"')
        self.assertNotContains(admin_response,'name="authenticity_high_copy"')
        self.assertNotContains(admin_response,'name="authenticity_copy"')

    def test_django_admin_form_saves_only_one_and_can_clear(self):
        vendor=Vendor.objects.create(title='فروشنده',user=self.admin)
        self.product.vendor=vendor;self.product.save()
        data={'title':self.product.title,'price':'10000','sale_price':'0','product_status':'published','status':'on','in_stock':'on','pid':self.product.pid,'user':str(self.admin.pk),'vendor':str(vendor.pk),'category':str(self.category.pk),'sku':self.product.sku}
        for chosen in ('copy','high_copy','original',''):
            buf=BytesIO();Image.new('RGB',(24,24),'white').save(buf,format='PNG')
            image=SimpleUploadedFile('test.png',buf.getvalue(),content_type='image/png')
            form=ProductAdminForm(data={**data,'authenticity_level':chosen},files={'image':image},instance=self.product)
            self.assertTrue(form.is_valid(),form.errors);form.save();self.product.refresh_from_db()
            self.assertEqual([self.product.authenticity_original,self.product.authenticity_high_copy,self.product.authenticity_copy],[chosen=='original',chosen=='high_copy',chosen=='copy'])

    def test_authenticity_save_through_manager_http_with_csrf(self):
        self.product.authenticity_copy = True
        self.product.save()
        url = reverse('useradmin:dashboard-edit-products', args=[self.product.pid])
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.admin)
        self.assertEqual(secured.get(url).status_code, 200)
        token = secured.cookies['csrftoken'].value
        data = {'title': self.product.title, 'price': '10000', 'sale_price': '0',
                'product_status': 'published', 'status': 'on', 'in_stock': 'on',
                'category': str(self.category.pk), 'authenticity_stage9_present': '1',
                'authenticity_level': 'high_copy'}
        self.assertEqual(secured.post(url, data).status_code, 403)
        response = secured.post(url, data, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302, response.content.decode()[:1500])
        self.product.refresh_from_db()
        self.assertEqual((self.product.authenticity_original, self.product.authenticity_high_copy,
                          self.product.authenticity_copy), (False, True, False))
        page = self.client.get(reverse('core:product-detail', args=[self.product.pid]))
        panel = page.content.decode().split('data-spec-authenticity', 1)[1].split('</section>', 1)[0]
        self.assertRegex(panel, r'value="high_copy"\s+checked')

    def test_edit_pending_price_draft_can_save_authenticity_without_publishing(self):
        self.product.price = 0
        self.product.price_pending_confirmation = True
        self.product.product_status = 'draft'
        self.product.save()
        url = reverse('useradmin:dashboard-edit-products', args=[self.product.pid])
        self.assertContains(self.client.get(url), 'name="price_pending_confirmation"')
        data = {'title': self.product.title, 'price': '0', 'sale_price': '0',
                'product_status': 'draft', 'status': 'on', 'in_stock': 'on',
                'category': str(self.category.pk), 'price_pending_confirmation': 'on',
                'authenticity_stage9_present': '1', 'authenticity_level': 'original'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertTrue(self.product.price_pending_confirmation and self.product.authenticity_original)
        self.assertEqual(self.product.product_status, 'draft')
        response = self.client.post(url, {**data, 'product_status': 'published'})
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.product_status, 'draft')

    def test_authenticity_save_through_django_admin_http(self):
        vendor = Vendor.objects.create(title='فروشنده آزمون', user=self.admin)
        self.product.vendor = vendor
        self.product.authenticity_original = True
        self.product.save()
        url = reverse('admin:core_product_change', args=[self.product.pk])
        data = {'pid': self.product.pid, 'sku': self.product.sku, 'user': str(self.admin.pk),
                'category': str(self.category.pk), 'vendor': str(vendor.pk),
                'title': self.product.title, 'price': '10000', 'sale_price': '0',
                'product_status': 'published', 'status': 'on', 'in_stock': 'on',
                'authenticity_level': 'copy', 'p_images-TOTAL_FORMS': '1',
                'p_images-INITIAL_FORMS': '0', 'p_images-MIN_NUM_FORMS': '0',
                'p_images-MAX_NUM_FORMS': '20', '_save': 'ذخیره'}
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.admin)
        self.assertEqual(secured.get(url).status_code, 200)
        token = secured.cookies['csrftoken'].value
        self.assertEqual(secured.post(url, data).status_code, 403)
        response = secured.post(url, data, HTTP_X_CSRFTOKEN=token)
        if response.status_code != 302:
            form = response.context['adminform'].form
            self.fail(f'Admin form did not save: {form.errors}; inlines: '
                      f'{[inline.formset.errors for inline in response.context["inline_admin_formsets"]]}')
        self.product.refresh_from_db()
        self.assertEqual((self.product.authenticity_original, self.product.authenticity_high_copy,
                          self.product.authenticity_copy), (False, False, True))

    def test_orders_are_real_and_status_update_requires_valid_post_and_csrf(self):
        order=CartOrder.objects.create(user=self.admin,full_name='مشتری آزمون',price=50000,paid_status=True,product_status='processing')
        page=self.client.get(reverse('useradmin:orders'),{'q':'مشتری آزمون'})
        self.assertContains(page,'مشتری آزمون');self.assertContains(page,'پرداخت‌شده');self.assertNotContains(page,'$')
        url=reverse('useradmin:change_order_status',args=[order.oid])
        secured=Client(enforce_csrf_checks=True);secured.force_login(self.admin)
        self.assertEqual(secured.post(url,{'status':'shipped'}).status_code,403)
        self.assertEqual(self.client.get(url).status_code,405)
        self.client.post(url,{'status':'invalid'});order.refresh_from_db();self.assertEqual(order.product_status,'processing')
        self.client.post(url,{'status':'shipped'});order.refresh_from_db();self.assertEqual(order.product_status,'shipped')

    def test_admin_catalog_lists_with_missing_images_and_category_sort(self):
        self.category.image = ''
        self.category.save()
        SubCategory.objects.create(category=self.category, title='زیرمجموعه آزمون', image='')
        Vendor.objects.create(title='فروشنده آزمون', image='', user=self.admin)
        for name in ('core_category_changelist', 'core_subcategory_changelist', 'core_vendor_changelist'):
            with self.subTest(page=name):
                page = self.client.get(reverse('admin:' + name))
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, '—')
        category_page = self.client.get(reverse('admin:core_category_changelist'), {'o':'4'})
        self.assertEqual(category_page.status_code, 200)
        self.assertContains(category_page, 'سلامت')

    def test_navigation_exposes_existing_real_admin_modules(self):
        menu = self.client.get(reverse('useradmin:dashboard'))
        names = ('core_product_changelist', 'core_subcategory_changelist',
                 'core_cartorderproducts_changelist', 'core_paymentattempt_changelist',
                 'core_address_changelist', 'core_wishlist_model_changelist',
                 'core_herobanner_changelist', 'core_banner_changelist',
                 'core_digitalbanner_changelist', 'core_amazingofferssettings_changelist',
                 'core_productbundle_changelist', 'core_storetrustfeature_changelist',
                 'core_faq_changelist', 'core_vendor_changelist')
        for name in names:
            with self.subTest(page=name):
                url = reverse('admin:' + name)
                self.assertContains(menu, f'href="{url}"')
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_pages_render_persian_and_auto_login_is_removed(self):
        for name in ('dashboard','dashboard-products','dashboard-add-products','orders','reviews','shop_page','settings','change_password'):
            with self.subTest(page=name):
                response=self.client.get(reverse('useradmin:'+name))
                self.assertEqual(response.status_code,200);self.assertContains(response,'lang="fa" dir="rtl"');self.assertContains(response,'admin-rtl-modern.css')
        self.assertEqual(self.client.get('/auto-login/').status_code,404)
        self.assertContains(self.client.get(reverse('useradmin:change_password')),'type="password"',count=3)

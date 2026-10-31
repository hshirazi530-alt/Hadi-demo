from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import Product

@override_settings(HIDE_PRODUCTS_WITHOUT_PHOTO=False)
class AuthenticityPositionTests(TestCase):
    def test_unknown_authenticity_is_above_cart_and_not_falsely_checked(self):
        p=Product.objects.create(title='کالای تست',product_status='published',status=True,image='')
        response=self.client.get(reverse('core:product-detail',args=[p.pid]));html=response.content.decode()
        self.assertEqual(response.status_code,200)
        self.assertEqual(html.count('data-spec-authenticity'),1)
        self.assertLess(html.index('data-spec-authenticity'),html.index('store-product-info__actions'))
        self.assertContains(response,'وضعیت اصالت برای این کالا ثبت یا تأیید نشده است')
        self.assertNotContains(response,'class="hm-spec-auth__choice is-selected"')
    def test_recorded_authenticity_still_displays(self):
        p=Product.objects.create(title='کالای تست',product_status='published',status=True,image='',authenticity_high_copy=True)
        response=self.client.get(reverse('core:product-detail',args=[p.pid]))
        self.assertContains(response,'data-authenticity-wrap')
        self.assertContains(response,'value="high_copy" checked')

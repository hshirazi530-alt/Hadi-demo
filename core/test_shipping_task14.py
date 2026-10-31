from django.test import TestCase
from django.urls import reverse
from core.models import Product

class ShippingInfoTests(TestCase):
    def test_guide_has_conditional_tracking_and_no_promised_eta(self):
        response=self.client.get(reverse('core:purchase_guide'))
        self.assertContains(response,'id="shipping-info"')
        self.assertContains(response,'https://tracking.post.ir/')
        self.assertContains(response,'اگر سفارش از طریق پست ارسال شد')
        self.assertNotContains(response,'زمان تحویل معمولاً ۲ تا ۵ روز کاری است')
    def test_cart_distinguishes_goods_total_and_shipping(self):
        product=Product.objects.create(title='کالای آزمون',price=800000,product_status='published',status=True,in_stock=True)
        session=self.client.session
        session['cart_data_obj']={str(product.id):{'title':product.title,'qty':'1','price':'800000','image':product.image.url,'pid':product.pid}}
        session.save()
        response=self.client.get(reverse('core:cart'))
        self.assertContains(response,'هزینهٔ ارسال')
        self.assertContains(response,'هنوز محاسبه نشده')
        self.assertContains(response,'جمع کالاها شامل هزینهٔ ارسال نیست')
        self.assertContains(response,reverse('core:purchase_guide')+'#shipping-info')

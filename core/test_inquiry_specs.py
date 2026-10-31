from django.test import TestCase
from django.urls import reverse
from core.catalog_inquiry import catalog_specifications

class InquiryDetailsTests(TestCase):
    def test_product_details_and_known_source(self):
        r=self.client.get(reverse('core:catalog-inquiry-detail',args=[14475]))
        self.assertContains(r,'مشاهده همه ویژگی‌ها')
        self.assertContains(r,'۱۴۰۰ میلی‌آمپرساعت')
        self.assertContains(r,'مشاهدهٔ منبع مشخصات')
        self.assertContains(r,'خرید از این صفحه غیرفعال است')
        self.assertContains(r,'data-inquiry-zoom-button')
        self.assertContains(r,'catalog-inquiry-zoom.js')
        html = r.content.decode()
        self.assertLess(html.index('data-inquiry-zoom>'), html.index('hm-review-detail__info'))
        self.assertNotContains(r,'product-cart-btn')
    def test_unverified_not_invented(self):
        r=self.client.get(reverse('core:catalog-inquiry-detail',args=[8460]))
        self.assertContains(r,'مشخصات فنی این کالا هنوز بررسی و تکمیل نشده است')
        self.assertNotContains(r,'مشاهدهٔ منبع مشخصات')
        self.assertNotContains(r,'مشاهده همه ویژگی‌ها')
        self.assertContains(r,'data-inquiry-zoom-button')
    def test_data_has_provenance(self):
        records=catalog_specifications();self.assertEqual(len(records),10)
        self.assertTrue(all(v['source'].startswith(('http://','https://')) and v['rows'] for v in records.values()))

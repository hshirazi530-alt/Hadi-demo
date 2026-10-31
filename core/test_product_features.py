from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from core.models import Product
from core.product_specifications import specification_rows

class ProductSpecificationParsingTests(SimpleTestCase):
    def test_lists_and_colons(self):
        self.assertEqual(specification_rows('<ul><li>رنگ: مشکی</li><li>ساختار: مات</li><li>ضد آب</li></ul>'), [
            {'label':'رنگ','value':'مشکی'}, {'label':'ساختار','value':'مات'}, {'label':'ویژگی','value':'ضد آب'}])
    def test_ckeditor_table(self):
        html='<figure class="table"><table><tbody><tr><td>وزن</td><td>۳۵ گرم</td></tr><tr><td>جنس</td><td>مات</td></tr></tbody></table></figure>'
        self.assertEqual(specification_rows(html), [{'label':'وزن','value':'۳۵ گرم'}, {'label':'جنس','value':'مات'}])
    def test_plain_text_and_ignored_script(self):
        self.assertEqual(specification_rows('رنگ: آبی\nنوع: کاور')[0], {'label':'رنگ','value':'آبی'})
        self.assertEqual(specification_rows('<script>bad</script><p>رنگ: سبز</p>'), [{'label':'رنگ','value':'سبز'}])

@override_settings(HIDE_PRODUCTS_WITHOUT_PHOTO=False)
class ProductFeatureViewTests(TestCase):
    def test_features_on_product_and_anchor(self):
        p=Product.objects.create(title='کاور آزمایشی',product_status='published',status=True,specifications='<ul><li>نوع: کاور</li><li>وزن: ۳۵ گرم</li><li>رنگ: مشکی</li></ul>')
        response=self.client.get(reverse('core:product-detail',args=[p.pid]))
        self.assertContains(response,'مشاهده همه ویژگی‌ها')
        self.assertContains(response,'data-tabs-goto="panel-specs"')
        self.assertContains(response,'<dt>رنگ</dt><dd>مشکی</dd>',html=True)
        self.assertContains(response,'نمایش متن اصلی مشخصات')
        self.assertEqual(len(response.context['specification_rows']),3)
    def test_no_fake_features_when_empty(self):
        p=Product.objects.create(title='کالای بی مشخصات',product_status='published',status=True,specifications='')
        response=self.client.get(reverse('core:product-detail',args=[p.pid]))
        self.assertNotContains(response,'مشاهده همه ویژگی‌ها')
        self.assertContains(response,'برای این کالا هنوز مشخصات فنی ثبت نشده است.')

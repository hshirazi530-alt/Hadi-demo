from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse
from core.catalog_inquiry import catalog_items, featured_items
from core.models import Category, Product
from core.photo_visibility import has_product_photo

class PhotoVisibilityTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.settings=override_settings(MEDIA_ROOT=self.temp.name);self.settings.enable();self.addCleanup(self.settings.disable)
        self.cat=Category.objects.create(title='سشوار')
        self.empty=Product.objects.create(title='سشوار بدون عکس',category=self.cat,product_status='published',status=True,image='')
        self.missing=Product.objects.create(title='سشوار فایل گمشده',category=self.cat,product_status='published',status=True,image='missing.jpg')
        self.default=Product.objects.create(title='سشوار پیش فرض',category=self.cat,product_status='published',status=True,image='product.jpg')
        default_storage.save('photo.jpg',ContentFile(b'image exists'))
        self.picture=Product.objects.create(title='سشوار با عکس',category=self.cat,product_status='published',status=True,image='photo.jpg')
    def test_public_list_search_and_direct(self):
        for url in [reverse('core:product-list'),reverse('core:search'),reverse('core:category-product-list',args=[self.cat.cid]),reverse('core:index')]:
            r=self.client.get(url);self.assertContains(r,self.picture.title);self.assertNotContains(r,self.empty.title);self.assertNotContains(r,self.missing.title);self.assertNotContains(r,self.default.title)
        self.assertEqual(self.client.get(reverse('core:product-detail',args=[self.empty.pid])).status_code,404)
        self.assertEqual(self.client.get(reverse('core:product-detail',args=[self.picture.pid])).status_code,200)
        self.assertEqual(Product.objects.count(),4)
    def test_visibility_restored_when_photo_is_added(self):
        self.assertFalse(has_product_photo(self.empty));self.empty.image='photo.jpg';self.empty.save();self.assertTrue(has_product_photo(self.empty))
        self.assertEqual(self.client.get(reverse('core:product-detail',args=[self.empty.pid])).status_code,200)
    def test_hide_can_be_turned_off(self):
        with override_settings(HIDE_PRODUCTS_WITHOUT_PHOTO=False):
            self.assertEqual(self.client.get(reverse('core:product-detail',args=[self.empty.pid])).status_code,200)
    def test_inquiry_omits_imageless_everywhere(self):
        rows=catalog_items();missing=next(x for x in rows if not x['image']);visible=[x for x in rows if x['image'] and (Path(__file__).resolve().parent.parent/'static'/x['image']).is_file()]
        response=self.client.get(reverse('core:catalog-inquiry-list'))
        self.assertEqual(response.context['total_count'],len(visible));self.assertTrue(all(x['image'] for x in response.context['items']))
        self.assertTrue(all(x['image'] for x in featured_items()))
        self.assertEqual(self.client.get(reverse('core:catalog-inquiry-detail',args=[missing['id']])).status_code,404)
        r=self.client.get(reverse('core:catalog-inquiry-list'),{'q':str(missing['id'])});self.assertEqual(r.context['total_count'],0)

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from core.models import Product
from django.contrib.auth import get_user_model

class ProductWebPTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='test@example.com', username='test', password='test')
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.temp.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def jpeg(self, color='red'):
        data = BytesIO(); Image.new('RGB', (48, 32), color).save(data, 'JPEG')
        return SimpleUploadedFile('sample.jpg', data.getvalue(), content_type='image/jpeg')

    def test_new_and_replaced_images_preserve_originals(self):
        product = Product.objects.create(title='example', user=self.user, image=self.jpeg())
        product.refresh_from_db()
        first = product.image.name
        self.assertTrue(product.image_webp.name.endswith('.webp'))
        self.assertEqual(product.image_webp_source, first)
        self.assertTrue(product.image.storage.exists(first))
        old_webp = product.image_webp.name
        product.image = self.jpeg('blue'); product.save(); product.refresh_from_db()
        self.assertNotEqual(product.image.name, first)
        self.assertNotEqual(product.image_webp.name, old_webp)
        self.assertTrue(product.image.storage.exists(first))
        self.assertTrue(product.image.storage.exists(old_webp))

    def test_missing_image_uses_default(self):
        with patch('core.product_webp.create_webp', return_value=False):
            product = Product.objects.create(title='missing', image='missing.jpg')
        self.assertTrue(product.display_image_url.endswith('product-image-pending.webp'))

    def test_existing_conversion_is_dry_run_until_apply(self):
        with patch('core.product_webp.create_webp', return_value=False):
            p = Product.objects.create(title='old', user=self.user, image=self.jpeg())
        call_command('convert_product_images_webp', stdout=BytesIOText())
        p.refresh_from_db(); self.assertFalse(p.image_webp)
        call_command('convert_product_images_webp', apply=True, stdout=BytesIOText())
        p.refresh_from_db(); self.assertTrue(p.image_webp)

class BytesIOText:
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False

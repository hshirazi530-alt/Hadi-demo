from unittest.mock import patch
from django.db import IntegrityError
from django.test import SimpleTestCase
from core.management.commands.seed_store_products import upsert_sample_product


class SeedSkuRetryTests(SimpleTestCase):
    @patch('core.management.commands.seed_store_products.Product.objects.update_or_create')
    def test_sku_collision_is_retried(self, upsert):
        upsert.side_effect = [IntegrityError('UNIQUE constraint failed: core_product.sku'), ('product', True)]
        self.assertEqual(upsert_sample_product(title='sample'), ('product', True))
        self.assertEqual(upsert.call_count, 2)

    @patch('core.management.commands.seed_store_products.Product.objects.update_or_create')
    def test_unrelated_database_error_is_not_retried(self, upsert):
        upsert.side_effect = IntegrityError('other constraint')
        with self.assertRaises(IntegrityError):
            upsert_sample_product(title='sample')
        self.assertEqual(upsert.call_count, 1)

    @patch('core.management.commands.seed_store_products.Product.objects.update_or_create')
    def test_retries_are_bounded(self, upsert):
        upsert.side_effect = IntegrityError('core_product.sku')
        with self.assertRaises(IntegrityError):
            upsert_sample_product(title='sample')
        self.assertEqual(upsert.call_count, 5)

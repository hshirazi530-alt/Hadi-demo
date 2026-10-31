from unittest.mock import patch
from django.utils.html import escape
from django.test import TestCase
from django.urls import reverse
from core.models import Category, SubCategory, Product
from core.research_proposals import GROUPS, PREVIEW_IMAGES
from django.conf import settings
from pathlib import Path

class ResearchProposalsTest(TestCase):
    def test_fifty_research_examples_do_not_create_products(self):
        self.assertEqual(sum(len(group['items']) for group in GROUPS.values()), 50)
        for (category_name, sub_name), group in GROUPS.items():
            sub = SubCategory.objects.get(category__title=category_name, title=sub_name)
            before = Product.objects.count()
            url = reverse('core:subcategory-product-list', args=[sub.scid])
            with patch.dict('os.environ', {'HAZHIR_RESEARCH_PREVIEW': '1'}):
                response = self.client.get(url)
                self.assertContains(response, escape(group['items'][0]))
                self.assertContains(response, 'قیمت و موجودی در انتظار تأیید', count=10)
            with patch.dict('os.environ', {'HAZHIR_RESEARCH_PREVIEW': '0'}):
                self.assertNotContains(self.client.get(url), escape(group['items'][0]))
            self.assertEqual(Product.objects.count(), before)

    def test_all_fifty_preview_images_exist(self):
        titles = [title for group in GROUPS.values() for title in group['items']]
        self.assertEqual(len(titles), 50)
        for title in titles:
            self.assertIn(title, PREVIEW_IMAGES, title)
            path, source = PREVIEW_IMAGES[title]
            self.assertTrue((Path(settings.BASE_DIR) / 'static' / path).is_file(), title)
            self.assertTrue(source.startswith('https://'), title)

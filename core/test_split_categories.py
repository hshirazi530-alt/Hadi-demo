from django.test import TestCase
from django.urls import reverse
from core.models import Category
from core.navigation import invalidate_nav_cache


class SplitCategoryTests(TestCase):
    def setUp(self):
        invalidate_nav_cache()

    def test_categories_have_distinct_pages_and_navigation(self):
        parts = Category.objects.get(title='قطعات')
        accessories = Category.objects.get(title='لوازم جانبی')
        self.assertNotEqual(parts.pk, accessories.pk)
        response = self.client.get(reverse('core:category-list'))
        self.assertContains(response, reverse('core:category-product-list', args=[parts.cid]))
        self.assertContains(response, reverse('core:category-product-list', args=[accessories.cid]))
        for category in (parts, accessories):
            response = self.client.get(reverse('core:category-product-list', args=[category.cid]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, category.title)
            self.assertContains(response, 'محصولات دستهٔ قدیمی هنوز جابه‌جا نشده‌اند')

    def test_original_category_and_products_remain_untouched(self):
        original = Category.objects.get(title='قطعات و لوازم دیجیتال')
        self.assertEqual(self.client.get(reverse('core:category-product-list', args=[original.cid])).status_code, 200)

    def test_header_shows_new_categories_not_combined_category(self):
        from core.navigation import get_nav_categories
        titles = [category.title for category in get_nav_categories()]
        self.assertIn('قطعات', titles)
        self.assertIn('لوازم جانبی', titles)
        self.assertNotIn('قطعات و لوازم دیجیتال', titles)

    def test_category_children_and_their_pages(self):
        for name, children in (
            ('قطعات', ('ریش‌تراش', 'سشوار')),
            ('لوازم جانبی', ('موبایل', 'لپ‌تاپ', 'تبلت')),
        ):
            category = Category.objects.get(title=name)
            for name in children:
                child = category.subcategories.get(title=name, is_active=True)
                response = self.client.get(reverse('core:subcategory-product-list', args=[child.scid]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, name)

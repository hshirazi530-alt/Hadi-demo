from datetime import timedelta
from decimal import Decimal
import re

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AmazingOffersSettings, Product, ProductBundle


class HomepageSectionRefreshTests(TestCase):
    def setUp(self):
        self.sample = Product.objects.create(
            title="پیشنهاد ساختگی (نمونه)", product_status="published", status=True,
            featured=True, in_stock=False, is_sale=True, price=Decimal("900000"),
            sale_price=Decimal("600000"), image="demo.jpg",
        )
        self.real = Product.objects.create(
            title="کالای واقعی تست", product_status="published", status=True,
            featured=True, in_stock=True, is_sale=False, price=Decimal("1234567"),
            image="actual.jpg",
        )
        self.sample_bundle = ProductBundle.objects.create(
            title="پک مراقبت روزانه", slug="daily-grooming-set", is_active=True,
            description="ترکیبی نمایشی؛ قیمت واقعی صرفاً نمونه است.", price=Decimal("6811500"),
        )
        self.sample_bundle.products.add(self.sample)

    def section(self, response, selector):
        html=response.content.decode("utf-8")
        match=re.search(selector+r'.*?</section>',html,re.S)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_selection_hides_sample_without_mutating_it_and_keeps_real_buyable(self):
        response=self.client.get(reverse("core:index"))
        section=self.section(response, r'<section[^>]*id="amazing-offers"')
        self.assertNotIn(self.sample.title,section)
        self.assertIn(self.real.title,section)
        self.assertIn('data-product-price="1234567"',section)
        self.assertIn('product-cart-btn',section)
        self.assertIn('گزیده‌های هژیر مارکت',section)
        self.assertNotIn('data-amazing-timer',section)
        self.assertEqual(section.count('class="swiper-slide hm-amazing-card hm-offer-inquiry"'),5)
        self.assertIn('15839.webp',section)
        self.assertIn('8460.webp',section)
        self.assertIn('۵ در خروجی، ۶ در تصویر',section)
        cards=re.findall(r'<article class="swiper-slide hm-amazing-card hm-offer-inquiry">.*?</article>',section,re.S)
        self.assertEqual(len(cards),5)
        for card in cards:
            self.assertNotIn('data-product-id',card)
            self.assertNotIn('product-cart-btn',card)
            self.assertNotIn('hm-amazing-card__off',card)
            self.assertNotIn('تومان',card)
        self.sample.refresh_from_db();self.real.refresh_from_db()
        self.assertTrue(self.sample.is_sale)
        self.assertEqual(self.real.price,Decimal("1234567"))
        self.assertEqual(Product.objects.count(),2)

    def test_demo_bundle_is_replaced_by_labeled_concept_without_sample_price(self):
        response=self.client.get(reverse("core:index"))
        section=self.section(response,r'<section class="beauty-section bundle-section"')
        self.assertNotIn(self.sample_bundle.title,section)
        self.assertNotIn('6811500',section)
        self.assertNotIn('class="bundle-card__price"',section)
        self.assertIn('تصویر مفهومی',section)
        self.assertIn('اقلام و قیمت پک باید تأیید شود',section)
        self.assertIn('bundle-concept.webp',section)
        self.assertTrue(ProductBundle.objects.filter(pk=self.sample_bundle.pk).exists())

    def test_real_bundle_is_retained_including_user_image_and_price(self):
        bundle=ProductBundle.objects.create(title="بسته واقعی تست",slug="real-pack",is_active=True,
            description="بسته ثبت‌شده",image="custom/real-pack.jpg",price=Decimal("2500000"))
        bundle.products.add(self.real)
        response=self.client.get(reverse("core:index"))
        section=self.section(response,r'<section class="beauty-section bundle-section"')
        self.assertIn(bundle.title,section)
        self.assertIn('custom/real-pack.jpg',section)
        self.assertNotIn(self.sample_bundle.title,section)
        bundle.refresh_from_db();self.assertEqual(bundle.image.name,'custom/real-pack.jpg')
        self.assertEqual(bundle.price,Decimal("2500000"))

    def test_actual_sale_section_keeps_discount_timer_when_all_cards_are_real_sale_items(self):
        for n in range(6):
            Product.objects.create(title=f"کالای تخفیف‌دار واقعی {n}",product_status="published",status=True,
                featured=True,in_stock=True,is_sale=True,price=Decimal("9000"),sale_price=Decimal("7000"),image="actual.jpg")
        AmazingOffersSettings.objects.update_or_create(pk=1,defaults={"deadline":timezone.now()+timedelta(days=1)})
        response=self.client.get(reverse("core:index"))
        section=self.section(response,r'<section[^>]*id="amazing-offers"')
        self.assertIn('شگفت‌انگیزهای هژیر مارکت',section)
        self.assertIn('data-amazing-timer',section)
        self.assertIn('hm-amazing-card__off',section)
        self.assertNotIn('hm-offer-inquiry',section)
        self.assertNotIn(self.sample.title,section)

"""بارگذاری داده‌های نمایشی فروشگاه از فایل snapshot.

این دستور داده‌های موجود در demo-data.json را در دیتابیس وارد می‌کند.
اگر محصولی با همان pid وجود داشته باشد، به‌روزرسانی می‌شود و داده‌های تکراری
ایجاد نمی‌شوند. این دستور برای محیط نمایشی Render طراحی شده است.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import (
    FAQ,
    HeroBanner,
    Product,
    ProductBundle,
    ProductImages,
    StoreTrustFeature,
    SubCategory,
    Category,
    DigitalBanner,
)


class Command(BaseCommand):
    help = "بارگذاری داده‌های نمایشی فروشگاه از فایل snapshot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(Path(settings.BASE_DIR) / "demo-data.json"),
            help="مسیر فایل snapshot",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="حذف داده‌های موجود پیش از بارگذاری",
        )

    def handle(self, *args, **options):
        snapshot_path = Path(options["path"])
        if not snapshot_path.is_file():
            raise CommandError(f"فایل snapshot پیدا نشد: {snapshot_path}")

        with open(snapshot_path, encoding="utf-8") as f:
            data = json.load(f)

        with transaction.atomic():
            if options["replace"]:
                self.stdout.write("حذف داده‌های موجود...")
                ProductImages.objects.all().delete()
                Product.objects.all().delete()
                SubCategory.objects.all().delete()
                Category.objects.all().delete()
                HeroBanner.objects.all().delete()
                DigitalBanner.objects.all().delete()
                FAQ.objects.all().delete()
                StoreTrustFeature.objects.all().delete()
                ProductBundle.objects.all().delete()

            stats = {}

            categories = {}
            for item in data.get("categories", []):
                category, _ = Category.objects.get_or_create(
                    title=item["title"],
                    defaults={"cid": item.get("cid")},
                )
                if item.get("image"):
                    category.image.name = item["image"]
                if item.get("icon"):
                    category.icon.name = item["icon"]
                category.save()
                categories[category.title] = category
            stats["categories"] = len(categories)

            subcategories = {}
            for item in data.get("subcategories", []):
                category = categories.get(item.get("category_title"))
                if not category:
                    continue
                subcategory, _ = SubCategory.objects.get_or_create(
                    category=category,
                    title=item["title"],
                    defaults={"scid": item.get("scid")},
                )
                if item.get("image"):
                    subcategory.image.name = item["image"]
                subcategory.order = item.get("order") or 0
                subcategory.is_active = True
                subcategory.save()
                subcategories[(category.title, subcategory.title)] = subcategory
            stats["subcategories"] = len(subcategories)

            products = {}
            for item in data.get("products", []):
                category = categories.get(item.get("category_title"))
                if not category:
                    continue
                subcategory = subcategories.get(
                    (category.title, item.get("subcategory_title"))
                )
                product, created = Product.objects.get_or_create(
                    pid=item["pid"],
                    defaults={"title": item["title"], "category": category},
                )
                product.title = item["title"]
                product.category = category
                product.subcategory = subcategory
                product.image = item.get("image") or ""
                product.description = item.get("description") or ""
                product.specifications = item.get("specifications") or ""
                product.price = item.get("price") or 0
                product.sale_price = item.get("sale_price") or 0
                product.is_sale = bool(item.get("is_sale"))
                product.type = item.get("type") or ""
                product.stock_count = item.get("stock_count") or "0"
                product.life = item.get("life") or ""
                product.product_status = item.get("product_status") or "draft"
                product.status = bool(item.get("status"))
                product.in_stock = bool(item.get("in_stock"))
                product.featured = bool(item.get("featured"))
                product.digital = bool(item.get("digital"))
                product.sku = item.get("sku") or ""
                product.price_pending_confirmation = bool(
                    item.get("price_pending_confirmation")
                )
                product.has_warranty = bool(item.get("has_warranty"))
                product.warranty_6_price = item.get("warranty_6_price") or 0
                product.warranty_12_price = item.get("warranty_12_price") or 0
                product.warranty_24_price = item.get("warranty_24_price") or 0
                product.authenticity_original = bool(item.get("authenticity_original"))
                product.authenticity_high_copy = bool(item.get("authenticity_high_copy"))
                product.authenticity_copy = bool(item.get("authenticity_copy"))
                product.save()
                products[product.pid] = product
            stats["products"] = len(products)

            image_count = 0
            for item in data.get("product_images", []):
                product = products.get(item.get("product_pid"))
                if not product:
                    continue
                _, created = ProductImages.objects.get_or_create(
                    product=product,
                    images=item["images"],
                )
                if created:
                    image_count += 1
            stats["product_images"] = image_count

            # پیوند دادن تصاویر یتیم به محصولات بر اساس مسیر تصویر اصلی
            for item in data.get("products", []):
                product = products.get(item["pid"])
                if not product or not item.get("image"):
                    continue
                ProductImages.objects.get_or_create(
                    product=product,
                    images=item["image"],
                )

            banner_count = 0
            for item in data.get("banners", []):
                banner, created = HeroBanner.objects.get_or_create(
                    title=item["title"],
                    defaults={"image": item.get("image") or ""},
                )
                banner.eyebrow = item.get("eyebrow") or ""
                banner.description = item.get("description") or ""
                banner.image_alt = item.get("image_alt") or ""
                banner.button_label = item.get("button_label") or ""
                banner.button_url = item.get("button_url") or "/products/"
                banner.is_active = bool(item.get("is_active"))
                banner.sort_order = item.get("sort_order") or 0
                if item.get("image"):
                    banner.image = item["image"]
                banner.save()
                if created:
                    banner_count += 1
            stats["banners"] = banner_count

            digital_count = 0
            for item in data.get("digital_banners", []):
                banner, created = DigitalBanner.objects.get_or_create(
                    title=item["title"],
                    defaults={"image": item.get("image") or ""},
                )
                banner.eyebrow = item.get("eyebrow") or ""
                banner.description = item.get("description") or ""
                banner.image_alt = item.get("image_alt") or ""
                banner.button_label = item.get("button_label") or ""
                banner.button_url = item.get("button_url") or "/products/"
                banner.is_active = bool(item.get("is_active"))
                banner.sort_order = item.get("sort_order") or 0
                if item.get("image"):
                    banner.image = item["image"]
                banner.save()
                if created:
                    digital_count += 1
            stats["digital_banners"] = digital_count

            faq_count = 0
            for item in data.get("faqs", []):
                _, created = FAQ.objects.get_or_create(
                    question=item["question"],
                    defaults={
                        "answer": item.get("answer") or "",
                        "is_active": True,
                    },
                )
                if created:
                    faq_count += 1
            stats["faqs"] = faq_count

            trust_count = 0
            for item in data.get("trust_features", []):
                _, created = StoreTrustFeature.objects.get_or_create(
                    title=item["title"],
                    defaults={
                        "description": item.get("description") or "",
                        "icon": item.get("icon") or "check",
                        "is_active": True,
                        "sort_order": item.get("sort_order") or 0,
                    },
                )
                if created:
                    trust_count += 1
            stats["trust_features"] = trust_count

            bundle_count = 0
            for item in data.get("bundles", []):
                bundle, created = ProductBundle.objects.get_or_create(
                    slug=item.get("slug") or "demo-bundle",
                    defaults={"title": item.get("title") or "پک نمایشی"},
                )
                bundle.description = item.get("description") or ""
                bundle.price = item.get("price") or 0
                bundle.is_active = bool(item.get("is_active"))
                bundle.sort_order = item.get("sort_order") or 0
                bundle.save()
                if created:
                    bundle_count += 1
            stats["bundles"] = bundle_count

        self.stdout.write(
            self.style.SUCCESS(
                "Snapshot loaded: "
                + ", ".join(f"{key}={value}" for key, value in stats.items())
            )
        )

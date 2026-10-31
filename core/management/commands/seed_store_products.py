import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from core.models import Category, Product, ProductImages, SubCategory, Vendor
from core.storefront import HOME_CATEGORIES, SAMPLE_STORE_PRODUCTS, STORE_SUBCATEGORIES
from userauths.models import User


def upsert_sample_product(**kwargs):
    """Retry SKU collisions only; do not hide other database errors."""
    for attempt in range(5):
        try:
            return Product.objects.update_or_create(**kwargs)
        except IntegrityError as exc:
            if 'sku' not in str(exc).lower() or attempt == 4:
                raise


class Command(BaseCommand):
    help = "افزودن یا به‌روزرسانی کالاهای نمونهٔ فروشگاه مراقبت شخصی"

    def handle(self, *args, **options):
        source_directory = (
            Path(settings.BASE_DIR)
            / "static"
            / "assets"
            / "imgs"
            / "beauty"
        )
        media_directory = Path(settings.MEDIA_ROOT) / "store-samples"
        media_directory.mkdir(parents=True, exist_ok=True)

        category_images = {
            item["product_category"]: item["image"].replace(
                "assets/imgs/beauty/",
                "",
                1,
            )
            for item in HOME_CATEGORIES
        }
        image_names = {item["image"] for item in SAMPLE_STORE_PRODUCTS}
        image_names.update(category_images.values())
        for subcategory_items in STORE_SUBCATEGORIES.values():
            for subcategory_item in subcategory_items:
                image_names.add(subcategory_item["image"])
        for image_name in image_names:
            source = source_directory / image_name
            if not source.is_file():
                raise CommandError(f"تصویر نمونه پیدا نشد: {source}")
            destination = media_directory / image_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        spin_sequences = {}
        for item in SAMPLE_STORE_PRODUCTS:
            sequence_name = item.get("spin_sequence")
            if not sequence_name:
                continue
            sequence_source = source_directory / "360" / sequence_name
            frame_sources = sorted(sequence_source.glob("frame-*.webp"))
            if len(frame_sources) != 24:
                raise CommandError(
                    f"توالی چرخش {sequence_name} باید دقیقاً ۲۴ فریم داشته باشد."
                )
            sequence_media = media_directory / "360" / sequence_name
            sequence_media.mkdir(parents=True, exist_ok=True)
            for frame_source in frame_sources:
                shutil.copyfile(frame_source, sequence_media / frame_source.name)
            spin_sequences[item["title"]] = [
                f"store-samples/360/{sequence_name}/{frame.name}"
                for frame in frame_sources
            ]

        sample_user = User.objects.order_by("id").first()
        vendor = Vendor.objects.order_by("id").first()
        if vendor and sample_user and vendor.user_id != sample_user.id:
            vendor = Vendor.objects.filter(user=sample_user).first() or vendor

        categories = {}
        for category_item in HOME_CATEGORIES:
            category_name = category_item["product_category"]
            category, _ = Category.objects.get_or_create(title=category_name)
            category.image.name = f"store-samples/{category_images[category_name]}"
            category.save(update_fields=["image"])
            categories[category_name] = category

        for category_name, subcategory_items in STORE_SUBCATEGORIES.items():
            if category_name not in categories:
                category, _ = Category.objects.get_or_create(title=category_name)
                categories[category_name] = category
            for index, subcategory_item in enumerate(subcategory_items, start=1):
                subcategory, _ = SubCategory.objects.get_or_create(
                    category=categories[category_name],
                    title=subcategory_item["title"],
                )
                subcategory.image.name = f"store-samples/{subcategory_item['image']}"
                subcategory.order = index
                subcategory.is_active = True
                subcategory.save(update_fields=["image", "order", "is_active"])

        sample_image_note = (
            " عکس این کالا برای پیش‌نمایش فروشگاه است و لزوماً مدل دقیق نام‌برده را "
            "نمایش نمی‌دهد."
        )
        for item in SAMPLE_STORE_PRODUCTS:
            category_name = item["category"]
            if category_name not in categories:
                category, _ = Category.objects.get_or_create(title=category_name)
                category_image = category_images[category_name]
                category.image.name = f"store-samples/{category_image}"
                category.save(update_fields=["image"])
                categories[category_name] = category

            product, _ = upsert_sample_product(
                title=item["title"],
                category=categories[category_name],
                defaults={
                    "user": sample_user,
                    "vendor": vendor,
                    "subcategory": (
                        SubCategory.objects.filter(
                            category=categories[category_name],
                            title=item["subcategory"],
                        ).first()
                        if item.get("subcategory")
                        else None
                    ),
                    "image": f"store-samples/{item['image']}",
                    "description": item["description"] + sample_image_note,
                    "specifications": item["specifications"],
                    "price": item["price"],
                    "sale_price": item["sale_price"],
                    "is_sale": item["is_sale"],
                    "type": item["type"],
                    "stock_count": "0",
                    "life": "نمونهٔ نمایشی",
                    "product_status": "published",
                    "status": True,
                    "in_stock": False,
                    "featured": True,
                    "digital": False,
                },
            )
            product.p_images.filter(
                images__startswith="store-samples/360/"
            ).delete()
            for frame_name in spin_sequences.get(item["title"], []):
                ProductImages.objects.get_or_create(
                    product=product,
                    images=frame_name,
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Sample products ready: {len(SAMPLE_STORE_PRODUCTS)}. "
                "Product details and inventory are demonstrative."
            )
        )

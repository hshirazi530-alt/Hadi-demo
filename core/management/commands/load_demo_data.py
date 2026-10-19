from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import shutil

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.core.management.base import CommandError

from core.models import FAQ, HeroBanner, Product, ProductBundle, StoreTrustFeature


DEFAULT_FAQS = (
    (
        "چطور محصول مناسب خودم را انتخاب کنم؟",
        "مشخصات و توضیحات هر محصول را بررسی کنید. اگر بین چند مدل مردد هستید، از فرم مشاورهٔ خرید استفاده کنید تا راهنمایی‌تان کنیم.",
    ),
    (
        "آیا امکان ثبت سفارش اینترنتی وجود دارد؟",
        "بله. محصولات را به سبد خرید اضافه کنید، اطلاعات تحویل را وارد کنید و سفارش را ثبت کنید. پرداخت فقط زمانی فعال می‌شود که شناسهٔ پذیرندهٔ زرین‌پال در تنظیمات فروشگاه قرار گرفته باشد.",
    ),
    (
        "چطور سفارش خود را پیگیری کنم؟",
        "پس از ورود به حساب کاربری، از بخش سفارش‌ها می‌توانید سفارش‌های ثبت‌شده و آخرین وضعیت آن‌ها را ببینید.",
    ),
    (
        "محصولات نمونه قابل خرید واقعی هستند؟",
        "خیر. کالاهایی که با برچسب «نمونه» مشخص شده‌اند صرفاً برای نمایش روند فروشگاه هستند و قیمت و موجودی واقعی ندارند.",
    ),
)

DEFAULT_FEATURES = (
    ("انتخاب شفاف", "مشخصات کالا و شرایط سفارش را پیش از خرید بررسی کنید.", "check"),
    ("پشتیبانی انسانی", "برای انتخاب محصول یا پیگیری سفارش با ما در تماس باشید.", "support"),
    ("پرداخت امن", "پرداخت آنلاین پس از پیکربندی رسمی درگاه زرین‌پال فعال می‌شود.", "lock"),
)

DEFAULT_BANNER = {
    "eyebrow": "",
    "description": "ابزارهای مراقبت شخصی مردانه را ببینید و مشخصات هر کالا را بررسی کنید.",
    "image_alt": "تصویر نمایشی ابزارهای مراقبت شخصی",
    "image": "storefront/banners/barber-hero.jpg",
    "button_label": "دیدن محصولات",
    "button_url": "/products/",
    "is_active": True,
    "sort_order": 0,
}

BANNER_TITLE = "ابزارهای مراقبت شخصی مردانه"
LEGACY_BANNER_TITLE = "مراقبت روزانه، با انتخاب دقیق"


class Command(BaseCommand):
    help = "بارگذاری داده‌های نمایشی محصولات و محتوای فروشگاه"

    def handle(self, *args, **options):
        call_command("seed_store_products", verbosity=0)

        banner_source = (
            Path(settings.BASE_DIR)
            / "static"
            / "assets"
            / "imgs"
            / "beauty"
            / "barber-hero.jpg"
        )
        banner_destination = Path(settings.MEDIA_ROOT) / DEFAULT_BANNER["image"]
        if not banner_source.is_file():
            raise CommandError(f"تصویر نمونهٔ بنر پیدا نشد: {banner_source}")
        banner_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(banner_source, banner_destination)

        for question, answer in DEFAULT_FAQS:
            FAQ.objects.get_or_create(
                question=question,
                defaults={"answer": answer, "is_active": True},
            )

        for order, (title, description, icon) in enumerate(DEFAULT_FEATURES):
            StoreTrustFeature.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "icon": icon,
                    "is_active": True,
                    "sort_order": order,
                },
            )

        banner = HeroBanner.objects.filter(title=LEGACY_BANNER_TITLE).first()
        if banner:
            banner.title = BANNER_TITLE
            banner.eyebrow = ""
            banner.save(update_fields=["title", "eyebrow", "updated_at"])
            created = False
        else:
            banner, created = HeroBanner.objects.get_or_create(
                title=BANNER_TITLE,
                defaults=DEFAULT_BANNER,
            )
        if not created:
            if not banner.image:
                banner.image = DEFAULT_BANNER["image"]
                banner.save(update_fields=["image", "updated_at"])

        product_sets = (
            ("ریش‌تراش", ("ریش‌تراش", "ریش تراش", "ماشین اصلاح")),
            ("سشوار", ("سشوار",)),
            ("اتو مو", ("اتو مو", "حالت‌دهندهٔ مو", "حالت‌دهنده مو")),
        )
        selected_products = []
        for label, terms in product_sets:
            products = Product.objects.filter(
                product_status="published",
                status=True,
                title__contains="(نمونه)",
            )
            matching = None
            for term in terms:
                matching = products.filter(title__icontains=term).order_by("id").first()
                if matching:
                    break
            if matching:
                selected_products.append((label, matching))

        if len(selected_products) == 3:
            products = [product for _, product in selected_products]
            bundle_total = sum(
                (
                    product.sale_price
                    if product.is_sale and product.sale_price > 0
                    else product.price
                )
                for product in products
            )
            bundle_price = (bundle_total * Decimal("0.95")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
            bundle, created = ProductBundle.objects.get_or_create(
                slug="daily-grooming-set",
                defaults={
                    "title": "پک مراقبت روزانه",
                    "description": "ترکیبی نمایشی از ریش‌تراش، سشوار و اتوی مو برای نمایش چیدمان پک‌های فروشگاه. مبلغ این پک تا زمان تأیید قیمت واقعی صرفاً نمونه است.",
                    "price": bundle_price,
                    "is_active": True,
                    "sort_order": 0,
                },
            )
            if created:
                bundle.products.set(products)

        self.stdout.write(self.style.SUCCESS(
            "Demo storefront products and content loaded."
        ))

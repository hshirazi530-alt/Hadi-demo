"""Add the "قطعات و لوازم دیجیتال" storefront category.

The header menu is data-driven (it renders ``categories`` from the
context processor), so the new menu entry must exist as a real
Category row instead of being hard-coded in the template. Using a data
migration also means the entry exists on every environment after
``migrate``, including the Render deployment.
"""

from django.db import migrations

CATEGORY_TITLE = "قطعات و لوازم دیجیتال"
CATEGORY_IMAGE = "category/digital-category.jpg"

SUBCATEGORY_TITLES = (
    "لوازم جانبی موبایل",
    "کابل و شارژر",
    "هندزفری و هدفون",
    "پاوربانک",
    "هولدر و پایه موبایل",
)


def add_digital_category(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    SubCategory = apps.get_model("core", "SubCategory")

    category, _created = Category.objects.get_or_create(
        title=CATEGORY_TITLE,
        defaults={"image": CATEGORY_IMAGE},
    )

    for order, title in enumerate(SUBCATEGORY_TITLES):
        SubCategory.objects.get_or_create(
            category=category,
            title=title,
            defaults={"order": order, "is_active": True},
        )


def remove_digital_category(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    Category.objects.filter(title=CATEGORY_TITLE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_price_pending_confirmation"),
    ]

    operations = [
        migrations.RunPython(add_digital_category, remove_digital_category),
    ]

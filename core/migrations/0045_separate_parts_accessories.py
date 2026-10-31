from django.db import migrations


def create_separate_categories(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    for title in ("قطعات", "لوازم جانبی"):
        if not Category.objects.filter(title=title).exists():
            Category.objects.create(title=title, image="category/digital-category.jpg")


class Migration(migrations.Migration):
    dependencies = [("core", "0044_order_warranty_snapshot")]
    operations = [migrations.RunPython(create_separate_categories, migrations.RunPython.noop)]

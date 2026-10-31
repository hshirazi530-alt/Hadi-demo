from django.db import migrations


def setup_categories(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    SubCategory = apps.get_model('core', 'SubCategory')
    db = schema_editor.connection.alias
    for old, new, children in (
        ('قطعات ریش‌تراش و سشوار', 'قطعات', ('ریش‌تراش', 'سشوار')),
        ('لوازم جانبی موبایل', 'لوازم جانبی', ('موبایل', 'لپ‌تاپ', 'تبلت')),
    ):
        originals = Category.objects.using(db).filter(title=old)
        existing = Category.objects.using(db).filter(title=new)
        if originals.count() != 1 or existing.exists():
            # Never merge, rename ambiguous rows, or change product assignments.
            continue
        category = originals.first()
        category.title = new
        category.save(using=db, update_fields=['title'])
        for order, title in enumerate(children):
            SubCategory.objects.using(db).get_or_create(
                category=category, title=title,
                defaults={'order': order, 'is_active': True, 'image': category.image.name},
            )


class Migration(migrations.Migration):
    dependencies = [('core', '0046_clarify_parts_and_mobile_accessories')]
    operations = [migrations.RunPython(setup_categories, migrations.RunPython.noop)]

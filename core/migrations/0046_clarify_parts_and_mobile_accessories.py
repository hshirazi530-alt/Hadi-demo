from django.db import migrations


def clarify_categories(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    Product = apps.get_model('core', 'Product')
    SubCategory = apps.get_model('core', 'SubCategory')
    for old, new in (('قطعات', 'قطعات ریش‌تراش و سشوار'), ('لوازم جانبی', 'لوازم جانبی موبایل')):
        if Category.objects.filter(title=new).exists():
            continue
        candidates = Category.objects.filter(title=old)
        candidate = candidates.first() if candidates.count() == 1 else None
        if candidate and not Product.objects.filter(category_id=candidate.pk).exists() and not SubCategory.objects.filter(category_id=candidate.pk).exists():
            candidate.title = new
            if new == 'قطعات ریش‌تراش و سشوار':
                candidate.image = 'store-samples/products/rotary-shaver.jpg'
            candidate.save(update_fields=['title', 'image'])
        else:
            Category.objects.create(title=new, image=('store-samples/products/rotary-shaver.jpg' if new == 'قطعات ریش‌تراش و سشوار' else 'category/digital-category.jpg'))


class Migration(migrations.Migration):
    dependencies = [('core', '0045_separate_parts_accessories')]
    operations = [migrations.RunPython(clarify_categories, migrations.RunPython.noop)]

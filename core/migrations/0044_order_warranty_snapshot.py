from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0043_product_authenticity_copy_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartorder',
            name='price',
            field=models.DecimalField(decimal_places=3, default='0.000', max_digits=20, verbose_name='قیمت'),
        ),
        migrations.AlterField(
            model_name='cartorder',
            name='saved',
            field=models.DecimalField(decimal_places=3, default='0.000', max_digits=20, verbose_name='تخفیف'),
        ),
        migrations.AlterField(
            model_name='cartorderproducts',
            name='price',
            field=models.DecimalField(decimal_places=3, default='0.000', max_digits=20, verbose_name='قیمت'),
        ),
        migrations.AlterField(
            model_name='cartorderproducts',
            name='total',
            field=models.DecimalField(decimal_places=3, default='0.000', max_digits=20, verbose_name='قیمت کل'),
        ),
        migrations.AddField(
            model_name='cartorderproducts',
            name='warranty_months',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='مدت گارانتی (ماه)'),
        ),
        migrations.AddField(
            model_name='cartorderproducts',
            name='warranty_price',
            field=models.DecimalField(decimal_places=0, default='0', max_digits=12, verbose_name='هزینهٔ گارانتی هر واحد'),
        ),
    ]

from django.core.management.base import BaseCommand
from core.models import Product
from core.product_webp import create_webp

class Command(BaseCommand):
    help = 'Preview conversion of existing product images; pass --apply to create WebP copies.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Create derivatives; originals are not removed.')
        parser.add_argument('--limit', type=int, default=0, help='Maximum number of products to process (0 = all).')

    def handle(self, *args, **options):
        products = Product.objects.all().order_by('pk')
        if options['limit'] < 0:
            raise ValueError('--limit must be >= 0')
        scanned = converted = failed = 0
        for product in products.iterator(chunk_size=100):
            if not product.image or not product.image.name or product.image.name.lower().endswith('.webp'):
                continue
            if product.image_webp and product.image_webp_source == product.image.name:
                continue
            if options['limit'] and scanned >= options['limit']:
                break
            scanned += 1
            self.stdout.write(f'{product.pk}: {product.image.name}')
            if options['apply']:
                if create_webp(product): converted += 1
                else: failed += 1
        self.stdout.write(f"{'APPLY' if options['apply'] else 'DRY RUN'}: candidates={scanned}, converted={converted}, failed={failed}")
        if failed:
            from django.core.management.base import CommandError
            raise CommandError('Some images could not be converted; originals were not deleted.')

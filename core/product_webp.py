"""Non-destructive product image derivatives; works with Django storage backends."""
import logging
import uuid
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger(__name__)


def create_webp(product):
    """Create a WebP from the stored original and persist its name; never delete originals."""
    if not product.image or not product.image.name:
        return False
    source = product.image.name
    try:
        with product.image.storage.open(source, 'rb') as f:
            with Image.open(f) as image:
                image.seek(0)  # animated uploads: a static first frame
                image = ImageOps.exif_transpose(image)
                image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
                data = BytesIO()
                image.save(data, 'WEBP', quality=85, method=6)
        filename = f'{uuid.uuid4().hex}.webp'
        product.image_webp.save(filename, ContentFile(data.getvalue()), save=False)
        product.image_webp_source = source
        # Avoid recursion and preserve unrelated fields; leave old files untouched.
        type(product).objects.filter(pk=product.pk, image=source).update(
            image_webp=product.image_webp.name, image_webp_source=source,
        )
        return True
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        log.warning('Unable to convert product image %s (product %s)', source, product.pk, exc_info=True)
        return False

"""Temporary public visibility rule; never deletes or updates product data."""
from django.conf import settings
from django.db.models import Q


def hiding_enabled():
    return getattr(settings, 'HIDE_PRODUCTS_WITHOUT_PHOTO', True)


def has_product_photo(product):
    if not hiding_enabled():
        return True
    image = product.image
    name = image.name if image else ''
    fields = []
    if name and name != 'product.jpg' and product.image_webp and product.image_webp_source == name:
        fields.append(product.image_webp)
    # The model's generic default is not a product photo.
    if name and name != 'product.jpg':
        fields.append(image)
    for field in fields:
        try:
            if field.storage.exists(field.name):
                return True
        except (OSError, ValueError):
            continue
    return False


def with_product_photo(queryset):
    if not hiding_enabled():
        return queryset
    candidates = queryset.filter(~Q(image='') | ~Q(image_webp='')).only('pk', 'image', 'image_webp', 'image_webp_source')
    ids = [product.pk for product in candidates.iterator() if has_product_photo(product)]
    return queryset.filter(pk__in=ids)

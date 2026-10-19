from django import forms
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from core.product_images import (
    MAX_PRODUCT_IMAGE_SIZE,
    ProductImageUploadError,
    convert_product_image,
    convert_product_images,
)


class ProductImageFormField(forms.ImageField):
    def to_python(self, data):
        if data and hasattr(data, "size") and data.size > MAX_PRODUCT_IMAGE_SIZE:
            raise ValidationError("حجم هر تصویر باید حداکثر ۱۰ مگابایت باشد.")
        return super().to_python(data)

    def clean(self, data, initial=None):
        if not data and initial:
            return initial
        try:
            uploaded_file = super().clean(data, initial)
        except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError) as error:
            raise ValidationError("فایل تصویر معتبر یا قابل پردازش نیست.") from error
        if not uploaded_file or isinstance(uploaded_file, str):
            return uploaded_file
        if getattr(uploaded_file, "_hjm_webp_processed", False):
            return uploaded_file
        try:
            return convert_product_image(uploaded_file)
        except ProductImageUploadError as error:
            raise ValidationError(error.errors) from error


class ProductDirectoryInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProductGalleryFormField(forms.FileField):
    widget = ProductDirectoryInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        try:
            return convert_product_images(data)
        except ProductImageUploadError as error:
            raise ValidationError(error.errors) from error

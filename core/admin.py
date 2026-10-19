from django.contrib import admin
from django import forms
from django.db import transaction
import logging
from core.models import (
    Address,
    CartOrder,
    CartOrderProducts,
    Category,
    Coupon,
    FAQ,
    HeroBanner,
    PaymentAttempt,
    Product,
    ProductBundle,
    ProductImages,
    ProductReview,
    StoreTrustFeature,
    SubCategory,
    Vendor,
    wishlist_model,
)
from core.product_images import (
    MAX_PRODUCT_IMAGE_COUNT,
    MAX_PRODUCT_IMAGE_TOTAL_SIZE,
)
from core.upload_forms import ProductGalleryFormField, ProductImageFormField


logger = logging.getLogger(__name__)


class ProductImagesAdminForm(forms.ModelForm):
    images = ProductImageFormField(required=False, label="تصویر")

    class Meta:
        model = ProductImages
        fields = "__all__"


class ProductAdminForm(forms.ModelForm):
    image = ProductImageFormField(label="عکس محصول")
    gallery_images = ProductGalleryFormField(
        required=False,
        label="تصاویر گالری محصول",
        help_text="انتخاب پوشه یا چند تصویر؛ JPEG، PNG و WebP، حداکثر ۱۹ تصویر اضافه.",
        widget=ProductGalleryFormField.widget(
            attrs={
                "accept": ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp",
                "multiple": True,
                "webkitdirectory": True,
                "directory": True,
            }
        ),
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            for field_name in ("description", "stock_count", "category", "tags"):
                self.fields[field_name].required = True
            self.fields["price"].initial = None
            self.fields["stock_count"].initial = ""

    def clean(self):
        cleaned_data = super().clean()
        gallery_images = cleaned_data.get("gallery_images", [])
        cover_image = cleaned_data.get("image")
        title = cleaned_data.get("title", "").strip()
        price = cleaned_data.get("price")
        description = cleaned_data.get("description")

        if title:
            duplicates = Product.objects.filter(title__iexact=title)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "title",
                    "محصولی با این عنوان از قبل ثبت شده است؛ عنوان یا مشخصات محصول را دقیق‌تر کنید.",
                )
        if price is not None and price < 0:
            self.add_error("price", "قیمت نمی‌تواند منفی باشد.")
        elif price == 0 and not self.instance.pk:
            self.add_error("price", "برای ثبت محصول، قیمت واقعی و مثبت لازم است.")
        if not description and not self.instance.pk:
            self.add_error("description", "توضیحات محصول بر پایهٔ اطلاعات تأییدشده لازم است.")

        if cover_image and len(gallery_images) + 1 > MAX_PRODUCT_IMAGE_COUNT:
            self.add_error(
                "gallery_images",
                f"تصویر اصلی و گالری در مجموع حداکثر {MAX_PRODUCT_IMAGE_COUNT} تصویر باشند.",
            )

        image_sizes = [
            getattr(image, "_hjm_source_size", image.size)
            for image in ([cover_image] if cover_image else []) + gallery_images
        ]
        if sum(image_sizes) > MAX_PRODUCT_IMAGE_TOTAL_SIZE:
            self.add_error("gallery_images", "حجم مجموع تصاویر باید حداکثر ۶۰ مگابایت باشد.")
        return cleaned_data


class ProductImagesAdmin(admin.TabularInline):
    model = ProductImages
    form = ProductImagesAdminForm
    extra = 1
    max_num = 20
    validate_max = True

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    inlines = [ProductImagesAdmin]
    list_editable = ['title', 'price', 'featured', 'product_status']
    list_display = ['user', 'title', 'product_image', 'price', 'category', 'subcategory', 'vendor', 'featured', 'product_status', 'pid']
    search_fields = ["title", "pid", "sku"]

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        gallery_images = form.cleaned_data.get("gallery_images", [])
        image_field = ProductImages._meta.get_field("images")
        storage = image_field.storage
        saved_names = []
        try:
            with transaction.atomic():
                super().save_related(request, form, formsets, change)
                for image in gallery_images:
                    name = image_field.generate_filename(
                        ProductImages(product=form.instance),
                        image.name,
                    )
                    saved_names.append(storage.save(name, image))
                ProductImages.objects.bulk_create(
                    [
                        ProductImages(product=form.instance, images=name)
                        for name in saved_names
                    ]
                )
        except Exception:
            for name in saved_names:
                try:
                    storage.delete(name)
                except OSError:
                    logger.exception("Could not remove an incomplete gallery image: %s", name)
            raise

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'category_image']

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'subcategory_image', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title']


class VendorAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor_image']


class CartOrderAdmin(admin.ModelAdmin):
    list_editable = ['paid_status', 'product_status', 'sku']
    list_display = ['user',  'price', 'paid_status', 'order_date','product_status', 'sku']


class CartOrderProductsAdmin(admin.ModelAdmin):
    list_display = ['order', 'invoice_no', 'item', 'image','qty', 'price', 'total']


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'is_approved', 'date']
    list_filter = ['is_approved', 'rating', 'date']
    list_editable = ['is_approved']
    search_fields = ['review', 'product__title', 'user__username']


class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ["order", "authority", "amount_rial", "ref_id", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["authority", "ref_id", "order__oid"]
    readonly_fields = ["order", "authority", "amount_rial", "ref_id", "status", "created_at", "updated_at"]


class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "sort_order", "updated_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["title", "eyebrow", "description"]


class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "is_active", "sort_order", "updated_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["question", "answer"]


class ProductBundleAdmin(admin.ModelAdmin):
    list_display = ["title", "price", "is_active", "sort_order"]
    list_filter = ["is_active"]
    list_editable = ["price", "is_active", "sort_order"]
    search_fields = ["title", "description"]
    filter_horizontal = ["products"]


class StoreTrustFeatureAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "sort_order"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["title", "description"]


class wishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'date']


class AddressAdmin(admin.ModelAdmin):
    list_editable = ['address', 'status']
    list_display = ['user', 'address', 'status']


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(CartOrder, CartOrderAdmin)
admin.site.register(CartOrderProducts, CartOrderProductsAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(PaymentAttempt, PaymentAttemptAdmin)
admin.site.register(HeroBanner, HeroBannerAdmin)
admin.site.register(FAQ, FAQAdmin)
admin.site.register(ProductBundle, ProductBundleAdmin)
admin.site.register(StoreTrustFeature, StoreTrustFeatureAdmin)
admin.site.register(wishlist_model, wishlistAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Coupon)

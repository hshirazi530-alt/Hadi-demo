from django.contrib import admin
from django import forms
from django.db import transaction
from django.db.models import Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from decimal import Decimal
import logging
from core.models import (
    Address,
    AmazingOffersSettings,
    Banner,
    CartOrder,
    CartOrderProducts,
    Category,
    Coupon,
    DigitalBanner,
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
    authenticity_level = forms.ChoiceField(
        label="اصالت کالا", required=False,
        choices=(("", "نامشخص — بدون نشان"), ("original", "اورجینال"),
                 ("high_copy", "های‌کپی"), ("copy", "کپی")),
        widget=forms.RadioSelect,
        help_text="فقط یک گزینه و فقط بر اساس اطلاعات تأییدشده انتخاب کنید.",
    )
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
        self.fields["price"].required = False
        if self.instance.pk:
            levels = [key for key in ("original", "high_copy", "copy")
                      if getattr(self.instance, "authenticity_" + key)]
            if len(levels) == 1:
                self.initial["authenticity_level"] = levels[0]
            elif len(levels) > 1:
                self.initial["authenticity_level"] = "__needs_review__"
                self.fields["authenticity_level"].help_text = (
                    "مقادیر متناقض قبلی وجود دارد؛ گزینهٔ درست را پس از بررسی انتخاب کنید."
                )
        if not self.instance.pk:
            for field_name in ("description", "stock_count", "category", "tags"):
                self.fields[field_name].required = True
            self.fields["price"].initial = None
            self.fields["stock_count"].initial = ""
        # گروه‌بندی فیلدهای گارانتی برای نمایش بهتر در ادمین
        for field_name in ("warranty_6_price", "warranty_12_price", "warranty_24_price"):
            if field_name in self.fields:
                self.fields[field_name].required = False
                self.fields[field_name].localize = True
                self.fields[field_name].help_text = "هزینهٔ اضافه برای هر عدد، به تومان؛ صفر یا خالی یعنی این مدت ارائه نمی‌شود."
        if "has_warranty" in self.fields:
            self.fields["has_warranty"].help_text = "برای ارائهٔ گارانتی اختیاری فعال کنید؛ حداقل یکی از مدت‌ها باید قیمت مثبت داشته باشد."

    def clean(self):
        cleaned_data = super().clean()
        if (self.instance.pk and "authenticity_original" not in self.fields
                and "authenticity_level" not in self.data
                and sum(bool(getattr(self.instance, "authenticity_" + key))
                        for key in ("original", "high_copy", "copy")) > 1):
            self.add_error("authenticity_level", "مقادیر قبلی متناقض‌اند؛ گزینهٔ درست یا نامشخص را انتخاب کنید.")
        authenticity_fields = ("authenticity_original", "authenticity_high_copy", "authenticity_copy")
        if sum(bool(cleaned_data.get(field)) for field in authenticity_fields) > 1:
            self.add_error(None, "فقط یکی از وضعیت‌های اورجینال، های‌کپی یا کپی را انتخاب کنید.")
        gallery_images = cleaned_data.get("gallery_images", [])
        cover_image = cleaned_data.get("image")
        title = cleaned_data.get("title", "").strip()
        price = cleaned_data.get("price")
        price_pending_confirmation = cleaned_data.get("price_pending_confirmation")
        product_status = cleaned_data.get("product_status")
        description = cleaned_data.get("description")

        warranty_fields = ("warranty_6_price", "warranty_12_price", "warranty_24_price")
        for field_name in warranty_fields:
            if field_name in self.errors:
                continue
            amount = cleaned_data.get(field_name)
            if amount is None:
                cleaned_data[field_name] = Decimal("0")
            elif amount < 0:
                self.add_error(field_name, "هزینهٔ گارانتی نمی‌تواند منفی باشد.")
        if cleaned_data.get("has_warranty") and not any(
            field in self.errors for field in warranty_fields
        ) and not any(cleaned_data.get(field, 0) > 0 for field in warranty_fields):
            self.add_error("has_warranty", "برای فعال‌کردن گارانتی، هزینهٔ حداقل یک مدت را مثبت وارد کنید.")

        if title:
            duplicates = Product.objects.filter(title__iexact=title)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "title",
                    "محصولی با این عنوان از قبل ثبت شده است؛ عنوان یا مشخصات محصول را دقیق‌تر کنید.",
                )
        if price is None or price == 0:
            if not price_pending_confirmation:
                self.add_error(
                    "price",
                    "قیمت واقعی و مثبت لازم است؛ برای محصول بدون قیمت، تأیید قیمت را فعال کنید.",
                )
            elif product_status != "draft":
                self.add_error(
                    "product_status",
                    "تا زمان تأیید قیمت، وضعیت محصول باید پیش‌نویس باشد.",
                )
            else:
                cleaned_data["price"] = 0
            if cleaned_data.get("is_sale"):
                self.add_error(
                    "is_sale",
                    "برای محصولی که قیمت آن تأیید نشده، تخفیف ثبت نکنید.",
                )
        elif price < 0:
            self.add_error("price", "قیمت نمی‌تواند منفی باشد.")
        else:
            cleaned_data["price_pending_confirmation"] = False
        if not description and not self.instance.pk:
            self.add_error("description", "توضیحات محصول بر پایهٔ اطلاعات تأییدشده لازم است.")

        if cover_image and len(gallery_images) + 1 > MAX_PRODUCT_IMAGE_COUNT:
            self.add_error(
                "gallery_images",
                f"تصویر اصلی و گالری در مجموع حداکثر {MAX_PRODUCT_IMAGE_COUNT} تصویر باشند.",
            )

        # Count only files uploaded in this request. The existing cover can be
        # stored remotely or temporarily missing; merely editing authenticity
        # must not read its size or turn that into a server error.
        new_images = list(gallery_images)
        if self.files.get(self.add_prefix("image")) and cover_image:
            new_images.insert(0, cover_image)
        image_sizes = [
            image._hjm_source_size if hasattr(image, "_hjm_source_size") else image.size
            for image in new_images
        ]
        if sum(image_sizes) > MAX_PRODUCT_IMAGE_TOTAL_SIZE:
            self.add_error("gallery_images", "حجم مجموع تصاویر باید حداکثر ۶۰ مگابایت باشد.")
        return cleaned_data


    def save(self, commit=True):
        product = super().save(commit=False)
        # An older client without the new field never resets existing values.
        if "authenticity_level" in self.data:
            chosen = self.cleaned_data.get("authenticity_level", "")
            for key in ("original", "high_copy", "copy"):
                setattr(product, "authenticity_" + key, chosen == key)
        if commit:
            product.save()
            self.save_m2m()
        return product


class ProductImagesAdmin(admin.TabularInline):
    model = ProductImages
    form = ProductImagesAdminForm
    extra = 1
    max_num = 20
    validate_max = True

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    # The single field above is the only visible editing control. Existing
    # database columns are retained for backwards compatibility.
    exclude = ("authenticity_original", "authenticity_high_copy", "authenticity_copy")
    inlines = [ProductImagesAdmin]
    list_display = (
        "product_image_preview",
        "title",
        "product_code",
        "category",
        "price",
        "inventory_count",
        "product_status_badge",
        "in_stock",
    )
    list_display_links = ("title",)
    list_filter = ("category", "product_status", "in_stock", "featured")
    search_fields = ["title", "pid", "sku"]
    list_per_page = 20
    ordering = ("title",)

    @admin.display(description="شناسهٔ محصول", ordering="pid")
    def product_code(self, obj):
        return obj.pid

    @admin.display(description="موجودی", ordering="stock_count")
    def inventory_count(self, obj):
        return obj.stock_count or "۰"

    @admin.display(description="تصویر")
    def product_image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img class="admin-product-thumbnail" src="{}" alt="تصویر محصول {}">',
            obj.image.url,
            obj.title,
        )

    @admin.display(description="وضعیت انتشار", ordering="product_status")
    def product_status_badge(self, obj):
        status_classes = {
            "published": "published",
            "draft": "draft",
            "disabled": "disabled",
            "rejected": "rejected",
            "in_review": "review",
        }
        status_class = status_classes.get(obj.product_status, "review")
        return format_html(
            '<span class="admin-status-badge admin-status-badge--{}">{}</span>',
            status_class,
            obj.get_product_status_display(),
        )

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
    list_display = ['image_preview', 'title', 'icon_preview', 'product_count']
    list_display_links = ['title']
    search_fields = ['title']
    fieldsets = [
        (None, {
            "fields": ("title", "cid"),
        }),
        ("تصاویر", {
            "fields": ("image", "icon"),
            "description": "«آیکون منو» در منوی کشویی هدر نمایش داده می‌شود (اختیاری).",
        }),
    ]
    readonly_fields = ["cid"]

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        return obj.category_image() if obj.image else "—"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(admin_product_count=Count("category"))

    @admin.display(description="آیکون")
    def icon_preview(self, obj):
        return obj.category_icon()

    @admin.display(description="تعداد محصولات", ordering="admin_product_count")
    def product_count(self, obj):
        return obj.admin_product_count


class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'title', 'category', 'order', 'is_active']
    list_display_links = ['title']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title']

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        return obj.subcategory_image() if obj.image else "—"


class VendorAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'title', 'user', 'date']
    list_display_links = ['title']
    search_fields = ['title']

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        return obj.vendor_image() if obj.image else "—"


class CartOrderAdmin(admin.ModelAdmin):
    list_editable = ['paid_status', 'product_status', 'sku']
    list_display = ['user', 'price', 'paid_status', 'order_date', 'product_status', 'sku']
    list_display_links = ['user']
    list_filter = ['paid_status', 'product_status']
    search_fields = ['user__username', 'sku', 'oid']


class CartOrderProductsAdmin(admin.ModelAdmin):
    list_display = ['order_img', 'order', 'invoice_no', 'item', 'qty', 'price', 'warranty_months', 'warranty_price', 'total']
    list_display_links = ['order']
    readonly_fields = ('warranty_months', 'warranty_price')
    search_fields = ['invoice_no', 'item']

    @admin.display(description="تصویر")
    def order_img(self, obj):
        img_path = (obj.image or "").lstrip("/")
        if img_path.startswith("media/"):
            img_path = img_path[len("media/"):]
        if not img_path:
            return "—"
        return mark_safe('<img src="/media/{}" width="50" height="50" />'.format(img_path))


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
    list_display = ["image_preview", "title", "is_active", "sort_order", "updated_at"]
    list_display_links = ["title"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["title", "eyebrow", "description"]

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img class="admin-product-thumbnail" src="{}" alt="تصویر {}">',
            obj.image.url,
            obj.title,
        )


class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "is_active", "sort_order", "updated_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["question", "answer"]


class ProductBundleAdmin(admin.ModelAdmin):
    list_display = ["image_preview", "title", "price", "is_active", "sort_order"]
    list_display_links = ["title"]
    list_filter = ["is_active"]
    list_editable = ["price", "is_active", "sort_order"]
    search_fields = ["title", "description"]
    filter_horizontal = ["products"]

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img class="admin-product-thumbnail" src="{}" alt="تصویر {}">',
            obj.image.url,
            obj.title,
        )


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


class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount', 'active']
    list_editable = ['discount', 'active']
    search_fields = ['code']


class BannerAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'title', 'placement', 'is_active', 'sort_order', 'updated_at']
    list_display_links = ['title']
    list_editable = ['is_active', 'sort_order']
    list_filter = ['placement', 'is_active']
    search_fields = ['title', 'subtitle']
    ordering = ['sort_order', 'id']

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img class="admin-product-thumbnail" src="{}" alt="تصویر {}">',
            obj.image.url,
            obj.title,
        )


class DigitalBannerAdmin(admin.ModelAdmin):
    list_display = ["image_preview", "title", "is_active", "sort_order", "updated_at"]
    list_display_links = ["title"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["title", "eyebrow", "description"]
    ordering = ["sort_order", "id"]

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img class="admin-product-thumbnail" src="{}" alt="تصویر {}">',
            obj.image.url,
            obj.title,
        )


@admin.register(AmazingOffersSettings)
class AmazingOffersSettingsAdmin(admin.ModelAdmin):
    list_display = ['is_active', 'deadline', 'updated_at']
    list_editable = ['is_active', 'deadline']
    list_display_links = None
    fieldsets = [
        ("بخش شگفت‌انگیز", {
            "fields": ("is_active", "deadline"),
            "description": "این تنظیمات تنها یک ردیف دارد. مهلت گذشته باعث نمایش وضعیت «به پایان رسید» می‌شود.",
        }),
    ]

    def has_add_permission(self, request):
        return not AmazingOffersSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Banner, BannerAdmin)
admin.site.register(DigitalBanner, DigitalBannerAdmin)
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
admin.site.register(Coupon, CouponAdmin)

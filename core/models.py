from django.db import models
from shortuuid.django_fields import ShortUUIDField
from django.utils.html import mark_safe
from userauths.models import User
from taggit.managers import TaggableManager
from django_ckeditor_5.fields import CKEditor5Field
from django.utils import timezone

STATUS_CHOICE = (
    ("processing", "پردازش"),
    ("shipped", "فرستادن"),
    ("delivered", "تحویل داده شد"),
)

STATUS = (
    ("draft", "پیش نویس"),
    ("disabled", "غیرفعال"),
    ("rejected", "رد شد"),
    ("in_review", "در حال بررسی"),
    ("published", "منتشر شده"),
)

RATING = (
    (1, "★☆☆☆☆"),
    (2, "★★☆☆☆"),
    (3, "★★★☆☆"),
    (4, "★★★★☆"),
    (5, "★★★★★"),
)


def user_directory_path(instance, filename):
    return 'user_{0}/{1}'.format(instance.user.id, filename)


class Category(models.Model):
    cid = ShortUUIDField(unique=True, length=10, max_length=20,
                         prefix="cat", alphabet="abcdefgh12345", verbose_name="کد دسته بندی")
    title = models.CharField(max_length=100, default="عنوان دسته بندی", verbose_name="عنوان")
    image = models.ImageField(upload_to="category", default="عکس دسته بندی.jpg", verbose_name="عکس")

    class Meta:
        verbose_name_plural = "دسته بندی ها"
        verbose_name = "دسته بندی"

    def category_image(self):
        return mark_safe('<img src="%s" width="50" height="50" />' % (self.image.url))

    def product_count(self):
        return Product.objects.filter(category=self).count()

    def __str__(self):
        return self.title


class SubCategory(models.Model):
    scid = ShortUUIDField(unique=True, length=10, max_length=20,
                         prefix="sub", alphabet="abcdefgh12345", verbose_name="کد زیرمجموعه")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories", verbose_name="دسته بندی")
    title = models.CharField(max_length=100, verbose_name="عنوان زیرمجموعه")
    image = models.ImageField(upload_to="subcategory", default="عکس زیرمجموعه.jpg", verbose_name="عکس")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name_plural = "زیرمجموعه ها"
        verbose_name = "زیرمجموعه"
        ordering = ["order", "title"]

    def __str__(self):
        return "{} - {}".format(self.category.title, self.title)

    def subcategory_image(self):
        return mark_safe('<img src="%s" width="50" height="50" />' % (self.image.url))


class Tags(models.Model):
    pass


class Vendor(models.Model):
    vid = ShortUUIDField(unique=True, length=10, max_length=20,
                         prefix="ven", alphabet="abcdefgh12345", verbose_name="کد فروشنده")

    title = models.CharField(max_length=100, default="عنوان فروشنده", verbose_name="عنوان")
    image = models.ImageField(
        upload_to=user_directory_path, default="vendor.jpg", verbose_name="عکس")
    cover_image = models.ImageField(
        upload_to=user_directory_path, default="vendor.jpg", verbose_name="پوشش عکس")
    # description = models.TextField(null=True, blank=True, default="I am am Amazing Vendor")
    description = CKEditor5Field(config_name='extends', null=True, blank=True, verbose_name="توضیحات")

    address = models.CharField(max_length=100, default="آدرس فروشنده", verbose_name="آدرس")
    contact = models.CharField(max_length=100, default="شماره تماس فروشنده", verbose_name="شماره تماس")
    chat_resp_time = models.CharField(max_length=100, default="100", verbose_name="زمان چت")
    shipping_on_time = models.CharField(max_length=100, default="100", verbose_name="ارسال_به_موقع")
    authentic_rating = models.CharField(max_length=100, default="100", verbose_name="امتیازدهی معتبر")
    days_return = models.CharField(max_length=100, default="100", verbose_name="روزها_بازگشت کالا")
    warranty_period = models.CharField(max_length=100, default="100", verbose_name="دوره گارانتی")

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    # date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="تاریخ")
    date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="تاریخ")

    class Meta:
        verbose_name_plural = "فروشنده ها"
        verbose_name = "فروشنده"

    def vendor_image(self):
        return mark_safe('<img src="%s" width="50" height="50" />' % (self.image.url))

    def __str__(self):
        return self.title


class Product(models.Model):
    pid = ShortUUIDField(unique=True, length=10,
                         max_length=20, alphabet="abcdefgh12345", verbose_name="کد محصول")

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="category", verbose_name="دسته بندی")
    subcategory = models.ForeignKey(
        "core.SubCategory", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products", verbose_name="زیرمجموعه")
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, related_name="product", verbose_name="فروشنده")

    title = models.CharField(max_length=100, default="عنوان محصول", verbose_name="عنوان")
    image = models.ImageField(
        upload_to=user_directory_path, default="product.jpg", verbose_name="عکس محصول")
    # description = models.TextField(null=True, blank=True, default="This is the product")
    description = CKEditor5Field(config_name='extends', null=True, blank=True, verbose_name= "توضیحات" )

    price = models.DecimalField(
        max_digits=12, decimal_places=0, default="0", verbose_name="قیمت")
    # old_price = models.DecimalField(
    #     max_digits=12, decimal_places=0, default="2")

    is_sale = models.BooleanField(default=False, verbose_name="تخفیف دارد")
    sale_price = models.DecimalField(
        max_digits=12, decimal_places=0, default="0", verbose_name="قیمت تخفیف")

    specifications = CKEditor5Field(config_name='extends', null=True, blank=True, verbose_name="مشخصات")
    # specifications = models.TextField(null=True, blank=True)
    type = models.CharField(
        max_length=100, default="نوع محصول", null=True, blank=True, verbose_name="نوع محصول")
    stock_count = models.CharField(
        max_length=100, default="10", null=True, blank=True, verbose_name="تعداد_سهام")
    life = models.CharField(
        max_length=100, default="100 روز", null=True, blank=True, verbose_name="عمر محصول")
    mfd = models.DateTimeField(auto_now_add=False, null=True, blank=True, verbose_name="روز/ماه/سال")

    tags = TaggableManager(blank=True, verbose_name="برچسب")

    # tags = models.ForeignKey(Tags, on_delete=models.SET_NULL, null=True)

    product_status = models.CharField(
        choices=STATUS, max_length=10, default="in_review", verbose_name="وضعیت_محصول")

    status = models.BooleanField(default=True, verbose_name="وضعیت")
    in_stock = models.BooleanField(default=True, verbose_name="موجودی در انبار")
    featured = models.BooleanField(default=False, verbose_name="محصول ویژه")
    digital = models.BooleanField(default=False, verbose_name="دیجیتال")

    sku = ShortUUIDField(unique=True, length=4, max_length=10,
                         prefix="sku", alphabet="1234567890", verbose_name="کد پیگیری محصول")

    date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ")
    updated = models.DateTimeField(null=True, blank=True, verbose_name="به‌روزرسانی‌شده")

    class Meta:
        verbose_name_plural = "محصولات"
        verbose_name = "محصول"

    def product_image(self):
        return mark_safe('<img src="%s" width="50" height="50" />' % (self.image.url))

    def __str__(self):
        return self.title

    def get_precentage(self):
        new_price = (self.price / self.sale_price) * 100
        return new_price


class ProductImages(models.Model):
    images = models.ImageField(
        upload_to="product-images", default="product.jpg")
    product = models.ForeignKey(
        Product, related_name="p_images", on_delete=models.SET_NULL, null=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "تصاویر محصول"


############################################## Cart, Order, OrderITems and Address ##################################
############################################## Cart, Order, OrderITems and Address ##################################
############################################## Cart, Order, OrderITems and Address ##################################
############################################## Cart, Order, OrderITems and Address ##################################


class CartOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="کاربر")
    full_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="نام و نام خوانوادگی")
    email = models.CharField(max_length=100, null=True, blank=True, verbose_name="ایمیل")
    phone = models.CharField(max_length=100, null=True, blank=True, verbose_name="موبایل")

    address = models.CharField(max_length=100, null=True, blank=True, verbose_name="آدرس")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="شهر")
    state = models.CharField(max_length=100, null=True, blank=True, verbose_name="فعال")
    country = models.CharField(max_length=100, null=True, blank=True, verbose_name="کشور")

    price = models.DecimalField(max_digits=12, decimal_places=3, default="0.000", verbose_name="قیمت")
    saved = models.DecimalField(max_digits=12, decimal_places=3, default="0.000", verbose_name="تخفیف")
    coupons = models.ManyToManyField("core.Coupon", blank=True, verbose_name="کد تخفیف")

    shipping_method = models.CharField(max_length=100, null=True, blank=True, verbose_name="روش حمل و نقل")
    tracking_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="پیگیری")
    tracking_website_address = models.CharField(max_length=100, null=True, blank=True, verbose_name="پیگیری آدرس سایت")

    paid_status = models.BooleanField(default=False, verbose_name="وضعیت_پرداخت ‌شده")
    order_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="تاریخ_سفارش")
    product_status = models.CharField(choices=STATUS_CHOICE, max_length=30, default="processing",
                                      verbose_name="وضعیت_محصول")
    sku = ShortUUIDField(null=True, blank=True, length=5, prefix="SKU", max_length=20, alphabet="1234567890",
                         verbose_name="کد پیگیری محصول")
    oid = ShortUUIDField(null=True, blank=True, length=8, max_length=20, alphabet="1234567890",
                         verbose_name="شناسه محصول")
    stripe_payment_intent = models.CharField(max_length=1000, null=True, blank=True, verbose_name="پرداخت آنلاین ")
    date = models.DateTimeField(default=timezone.now, null=True, blank=True, verbose_name="تاریخ")

    class Meta:
        verbose_name_plural = "سفارشات سبد خرید"
        verbose_name = "سفارش سبد خرید"


class PaymentAttempt(models.Model):
    STATUS_CHOICES = (
        ("pending", "در انتظار پرداخت"),
        ("paid", "پرداخت‌شده"),
        ("failed", "ناموفق"),
    )

    order = models.ForeignKey(
        CartOrder,
        on_delete=models.CASCADE,
        related_name="payment_attempts",
        verbose_name="سفارش",
    )
    authority = models.CharField(max_length=64, unique=True, verbose_name="شناسهٔ درگاه")
    amount_rial = models.PositiveBigIntegerField(verbose_name="مبلغ به ریال")
    ref_id = models.CharField(max_length=64, blank=True, verbose_name="کد پیگیری درگاه")
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="وضعیت",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "تلاش پرداخت"
        verbose_name_plural = "تلاش‌های پرداخت"

    def __str__(self):
        return f"{self.order_id} · {self.authority}"


class CartOrderProducts(models.Model):
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE, verbose_name="سفارش")
    invoice_no = models.CharField(max_length=200, verbose_name="فاکتور_شماره")
    product_status = models.CharField(max_length=200, verbose_name="وضعیت_محصول")
    item = models.CharField(max_length=200, verbose_name="آیتم_محصول")
    image = models.CharField(max_length=200, verbose_name="عکس")
    qty = models.IntegerField(default=0, verbose_name="تعداد")
    price = models.DecimalField(max_digits=12, decimal_places=3, default="0.000", verbose_name="قیمت")
    total = models.DecimalField(max_digits=12, decimal_places=3, default="0.000", verbose_name="قیمت کل")

    class Meta:
        verbose_name_plural = "تعداد سفارش سبد خرید"
        verbose_name = "تعداد سفارش سبد خرید"

    def order_img(self):
        return mark_safe('<img src="/media/%s" width="50" height="50" />' % (self.image))


############################################## Product Revew, wishlists, Address ##################################
############################################## Product Revew, wishlists, Address ##################################
############################################## Product Revew, wishlists, Address ##################################
############################################## Product Revew, wishlists, Address ##################################


class ProductReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name="نظرات",
                                verbose_name="محصول")
    review = models.TextField(verbose_name="نظر کاربران")
    rating = models.IntegerField(choices=RATING, default=None, verbose_name="امتیازدهی")
    is_approved = models.BooleanField(default=False, verbose_name="تأیید شده")
    date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ")

    class Meta:
        verbose_name_plural = "نقد و بررسی محصول"
        verbose_name = "نقد و بررسی محصولات"

    def __str__(self):
        if self.product:
            return self.product.title
        else:
            return f"review - {self.pk}"

    def get_rating(self):
        return self.rating


class wishlist_model(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="محصول")
    date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ")

    class Meta:
        verbose_name_plural = "لیست‌های علاقه‌مندی ها"
        verbose_name = "لیست‌های علاقه‌مندی"

    def __str__(self):
        return self.product.title


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    mobile = models.CharField(max_length=300, null=True, verbose_name="موبایل")
    address = models.CharField(max_length=100, null=True, verbose_name="آدرس")
    status = models.BooleanField(default=False, verbose_name="فعال")

    class Meta:
        verbose_name_plural = "آدرس "
        verbose_name = "آدرس"


class Coupon(models.Model):
    code = models.CharField(max_length=1000, verbose_name="کد")
    discount = models.IntegerField(default=1, verbose_name="تخفیف")
    active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name_plural = "بن تخفیفات"
        verbose_name = "بن تخفیف"

    def __str__(self):
        return f"{self.code}"


class HeroBanner(models.Model):
    eyebrow = models.CharField(max_length=80, blank=True, verbose_name="عنوان کوتاه")
    title = models.CharField(max_length=160, verbose_name="عنوان")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image = models.ImageField(upload_to="storefront/banners/", blank=True, verbose_name="تصویر")
    image_alt = models.CharField(max_length=180, blank=True, verbose_name="متن جایگزین تصویر")
    button_label = models.CharField(max_length=60, default="مشاهده محصولات", verbose_name="متن دکمه")
    button_url = models.CharField(max_length=300, default="/products/", verbose_name="پیوند دکمه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "بنر اصلی"
        verbose_name_plural = "بنرهای اصلی"

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=240, verbose_name="پرسش")
    answer = models.TextField(verbose_name="پاسخ")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"

    def __str__(self):
        return self.question


class ProductBundle(models.Model):
    title = models.CharField(max_length=160, verbose_name="عنوان پک")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="شناسهٔ پیوند")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image = models.ImageField(upload_to="storefront/bundles/", blank=True, verbose_name="تصویر")
    products = models.ManyToManyField(Product, related_name="bundles", verbose_name="محصولات")
    price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="قیمت پک")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "پک پیشنهادی"
        verbose_name_plural = "پک‌های پیشنهادی"

    def __str__(self):
        return self.title


class StoreTrustFeature(models.Model):
    title = models.CharField(max_length=100, verbose_name="عنوان")
    description = models.CharField(max_length=240, blank=True, verbose_name="توضیحات")
    icon = models.CharField(max_length=40, blank=True, verbose_name="نماد")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "مزیت فروشگاه"
        verbose_name_plural = "مزیت‌های فروشگاه"

    def __str__(self):
        return self.title

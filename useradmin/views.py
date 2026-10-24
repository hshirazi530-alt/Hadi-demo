from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum, Case, When, Value, IntegerField
from django.db.models.functions import Cast
from django.db import DatabaseError, transaction
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
import logging
import mimetypes
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import check_password
from django.core.files.storage import default_storage
from PIL import Image, UnidentifiedImageError


from core.models import (
    CartOrder,
    CartOrderProducts,
    Category,
    Product,
    ProductImages,
    ProductReview,
)
from core.product_images import (
    MAX_PRODUCT_IMAGE_COUNT,
    MAX_PRODUCT_IMAGE_SIZE,
    MAX_PRODUCT_IMAGE_TOTAL_SIZE,
    ProductImageUploadError,
    SUPPORTED_IMAGE_FORMATS,
    convert_selected_product_images,
    get_product_image_source_directory,
    get_source_product_image,
    list_source_product_images,
)
from userauths.models import Profile, User
from useradmin.forms import AddProductForm
from useradmin.decorators import admin_required

import datetime


logger = logging.getLogger(__name__)


def _save_product_with_images(product, form, converted_images):
    product_image_field = Product._meta.get_field("image")
    gallery_image_field = ProductImages._meta.get_field("images")
    stored_files = []

    try:
        cover_name = product_image_field.storage.save(
            product_image_field.generate_filename(product, converted_images[0].name),
            converted_images[0],
        )
        stored_files.append((product_image_field.storage, cover_name))
        product.image = cover_name

        gallery_names = []
        for image in converted_images[1:]:
            image_name = gallery_image_field.storage.save(
                gallery_image_field.generate_filename(
                    ProductImages(product=product), image.name
                ),
                image,
            )
            stored_files.append((gallery_image_field.storage, image_name))
            gallery_names.append(image_name)

        with transaction.atomic():
            product.save()
            form.save_m2m()
            ProductImages.objects.bulk_create(
                [
                    ProductImages(product=product, images=image_name)
                    for image_name in gallery_names
                ]
            )
    except (DatabaseError, OSError, ValidationError):
        for storage, name in stored_files:
            try:
                storage.delete(name)
            except OSError:
                logger.exception("Could not remove an incomplete product image: %s", name)
        raise



@admin_required
def dashboard(request):
    paid_orders = CartOrder.objects.filter(paid_status=True)
    now = timezone.localtime()
    month_names = [
        "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
        "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر",
    ]
    monthly_sales = []
    for offset in reversed(range(6)):
        month = now.month - offset
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        month_start = now.replace(
            year=year,
            month=month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        if month == 12:
            next_month = month_start.replace(year=year + 1, month=1)
        else:
            next_month = month_start.replace(month=month + 1)
        amount = paid_orders.filter(
            order_date__gte=month_start,
            order_date__lt=next_month,
        ).aggregate(total=Sum("price"))["total"] or 0
        monthly_sales.append(
            {
                "label": month_names[month - 1],
                "amount": amount,
            }
        )
    highest_month = max((item["amount"] for item in monthly_sales), default=0) or 1
    for item in monthly_sales:
        item["width"] = round(
            float(Decimal(item["amount"]) * Decimal("100") / Decimal(highest_month))
        )

    revenue = paid_orders.aggregate(price=Sum("price"))
    total_orders_count = CartOrder.objects.count()
    product_count = Product.objects.count()
    customer_count = User.objects.filter(is_superuser=False, is_staff=False).count()
    latest_orders = CartOrder.objects.order_by("-order_date")[:7]
    pending_products_count = Product.objects.filter(product_status="in_review").count()
    context = {
        "revenue": revenue,
        "orders_count": total_orders_count,
        "product_count": product_count,
        "customer_count": customer_count,
        "paid_orders_count": paid_orders.count(),
        "unpaid_orders_count": total_orders_count - paid_orders.count(),
        "pending_products_count": pending_products_count,
        "monthly_sales": monthly_sales,
        "latest_orders": latest_orders,
    }
    return render(request, "useradmin/dashboard.html", context)


@admin_required
def products(request):
    products_list = Product.objects.select_related("category").all()
    query = (request.GET.get("q") or "").strip()[:100]
    status_filter = (request.GET.get("status") or "").strip()
    category_filter = (request.GET.get("category") or "").strip()
    sort = (request.GET.get("sort") or "-date").strip()
    sort_fields = {
        "title": "title",
        "-title": "-title",
        "price": "price",
        "-price": "-price",
        "date": "date",
        "-date": "-date",
        "stock": "dashboard_stock",
        "-stock": "-dashboard_stock",
    }
    if query:
        products_list = products_list.filter(
            Q(title__icontains=query)
            | Q(pid__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__title__icontains=query)
        )
    if status_filter in dict(Product._meta.get_field("product_status").choices):
        products_list = products_list.filter(product_status=status_filter)
    else:
        status_filter = ""
    if category_filter.isdecimal():
        products_list = products_list.filter(category_id=category_filter)
    else:
        category_filter = ""
    products_list = products_list.annotate(
        dashboard_stock=Case(
            When(
                stock_count__regex=r"^\d+$",
                then=Cast("stock_count", IntegerField()),
            ),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by(sort_fields.get(sort, "-date"), "pid")

    paginator = Paginator(products_list, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "categories": Category.objects.order_by("title"),
        "status_choices": Product._meta.get_field("product_status").choices,
        "query": query,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "sort": sort if sort in sort_fields else "-date",
        "total_products": paginator.count,
        "pending_products_count": Product.objects.filter(product_status="in_review").count(),
    }
    return render(request, "useradmin/products.html", context)


@admin_required
def source_product_image(request, name):
    source_file = None
    try:
        source_path = get_source_product_image(name)
        source_file = source_path.open("rb")
        with Image.open(source_file) as image:
            if image.format != SUPPORTED_IMAGE_FORMATS[source_path.suffix.lower()]:
                raise ProductImageUploadError(["محتوای تصویر با پسوند فایل هم‌خوانی ندارد."])
            image.verify()
        source_file.seek(0)
    except (
        ProductImageUploadError,
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        if source_file:
            source_file.close()
        raise Http404("تصویر در دسترس نیست.") from error

    response = FileResponse(
        source_file,
        content_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@admin_required
def add_product(request):
    image_errors = []
    source_image_errors = ""
    if request.method == "POST":
        uploads = request.FILES.getlist("product_images")
        source_names = request.POST.getlist("source_product_images")
        source_cover_name = request.POST.get("source_cover_image", "").strip()
        local_cover_index = request.POST.get("local_cover_index", "")
        converted_images = []
        if uploads and source_names:
            image_errors.append("برای جلوگیری از ابهام، تصاویر را فقط از یک روش انتخاب کنید.")
        elif source_names and not source_cover_name:
            image_errors.append("برای تصاویر پوشه، تصویر اصلی را نیز مشخص کنید.")
        elif source_cover_name and source_cover_name not in source_names:
            image_errors.append("تصویر اصلی باید از میان تصاویر انتخاب‌شده باشد.")
        elif source_cover_name:
            source_names = [source_cover_name] + [
                name for name in source_names if name != source_cover_name
            ]
        elif uploads:
            try:
                cover_index = int(local_cover_index)
            except (TypeError, ValueError):
                image_errors.append("تصویر اصلی را از میان تصاویر بارگذاری‌شده مشخص کنید.")
            else:
                if not 0 <= cover_index < len(uploads):
                    image_errors.append("تصویر اصلیِ انتخاب‌شده معتبر نیست.")
                else:
                    uploads = (
                        [uploads[cover_index]]
                        + uploads[:cover_index]
                        + uploads[cover_index + 1 :]
                    )

        if not image_errors:
            try:
                converted_images = convert_selected_product_images(uploads, source_names)
            except ProductImageUploadError as error:
                image_errors = error.errors

        form_files = request.FILES.copy()
        if converted_images:
            form_files.setlist("image", [converted_images[0]])
        form = AddProductForm(request.POST, form_files)
        if form.is_valid() and not image_errors:
            product = form.save(commit=False)
            product.user = request.user
            try:
                _save_product_with_images(product, form, converted_images)
            except (DatabaseError, OSError, ValidationError):
                logger.exception("Could not save product or its images.")
                form.add_error(None, "ذخیره محصول یا تصاویر انجام نشد؛ دوباره تلاش کنید.")
            else:
                messages.success(request, "محصول و تصاویر آن با موفقیت ثبت شدند.")
                return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm()

    source_images = []
    try:
        source_images = list_source_product_images()
        selected_source_names = set(request.POST.getlist("source_product_images"))
        selected_cover_name = request.POST.get("source_cover_image", "")
        for image in source_images:
            image["preview_url"] = reverse(
                "useradmin:source-product-image",
                kwargs={"name": image["name"]},
            )
            image["selected"] = image["name"] in selected_source_names
            image["is_cover"] = image["name"] == selected_cover_name
            image["size_kb"] = max(1, (image["size"] + 1023) // 1024)
    except ProductImageUploadError as error:
        source_image_errors = " ".join(error.errors)
        selected_source_names = set()
        selected_cover_name = ""

    context = {
        "form": form,
        "image_errors": image_errors,
        "source_image_errors": source_image_errors,
        "source_images": source_images,
        "source_image_directory": str(get_product_image_source_directory()),
        "selected_cover_name": selected_cover_name,
        "image_limits": {
            "count": MAX_PRODUCT_IMAGE_COUNT,
            "file_mb": MAX_PRODUCT_IMAGE_SIZE // (1024 * 1024),
            "file_bytes": MAX_PRODUCT_IMAGE_SIZE,
            "total_mb": MAX_PRODUCT_IMAGE_TOTAL_SIZE // (1024 * 1024),
            "total_bytes": MAX_PRODUCT_IMAGE_TOTAL_SIZE,
        },
    }
    return render(request, "useradmin/add-products.html", context)

@admin_required
def edit_product(request, pid):
    product = Product.objects.get(pid=pid)

    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.save()
            form.save_m2m()
            return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm(instance=product)
    context = {
        'form':form,
        'product':product,
    }
    return render(request, "useradmin/edit-products.html", context)

@admin_required
@require_POST
def delete_product(request, pid):
    product = get_object_or_404(Product, pid=pid)
    product.delete()
    messages.success(request, "محصول با موفقیت حذف شد.")
    return redirect("useradmin:dashboard-products")


@admin_required
@require_POST
def bulk_delete_products(request):
    selected_pids = list(dict.fromkeys(request.POST.getlist("selected_products")))
    selected_pids = [pid for pid in selected_pids if pid and len(pid) <= 20][:100]
    if not selected_pids:
        messages.warning(request, "برای حذف گروهی، دست‌کم یک محصول انتخاب کنید.")
        return redirect("useradmin:dashboard-products")

    products_to_delete = Product.objects.filter(pid__in=selected_pids)
    found_count = products_to_delete.count()
    if found_count != len(selected_pids):
        messages.warning(request, "برخی محصولات انتخاب‌شده پیدا نشدند؛ موارد موجود پردازش شدند.")
    if found_count:
        products_to_delete.delete()
        messages.success(request, f"{found_count} محصول حذف شد.")
    return redirect("useradmin:dashboard-products")

@admin_required
def orders(request):
    orders = CartOrder.objects.all()
    context = {
        'orders':orders,
    }
    return render(request, "useradmin/orders.html", context)

@admin_required
def order_detail(request, id):
    order = CartOrder.objects.get(id=id)
    order_items = CartOrderProducts.objects.filter(order=order)
    context = {
        'order':order,
        'order_items':order_items
    }
    return render(request, "useradmin/order_detail.html", context)

@admin_required
@csrf_exempt
def change_order_status(request, oid):
    order = CartOrder.objects.get(oid=oid)
    if request.method == "POST":
        status = request.POST.get("status")
        print("status =======", status)
        messages.success(request, f"Order status changed to {status}")
        order.product_status = status
        order.save()
    
    return redirect("useradmin:order_detail", order.id)

@admin_required
def shop_page(request):
    products = Product.objects.filter(user=request.user)
    revenue = CartOrder.objects.filter(paid_status=True).aggregate(price=Sum("price"))
    total_sales = CartOrderProducts.objects.filter(order__paid_status=True).aggregate(qty=Sum("qty"))

    context = {
        'products':products,
        'revenue':revenue,
        'total_sales':total_sales,
    }
    return render(request, "useradmin/shop_page.html", context)

@admin_required
def reviews(request):
    reviews = ProductReview.objects.all()
    context = {
        'reviews':reviews,
    }
    return render(request, "useradmin/reviews.html", context)

@admin_required
def settings(request):
    profile = Profile.objects.get(user=request.user)

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        bio = request.POST.get("bio")
        address = request.POST.get("address")
        country = request.POST.get("country")

        if image is not None:
            profile.image = image
        profile.full_name = full_name
        profile.phone = phone
        profile.bio = bio
        profile.address = address
        profile.country = country

        profile.save()
        messages.success(request, "پروفایل مدیر با موفقیت ذخیره شد.")
        return redirect("useradmin:settings")
    
    context = {
        'profile':profile,
    }
    return render(request, "useradmin/settings.html", context)

@admin_required
def change_password(request):
    user = request.user

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Confirm Password and New Password Does Not Match")
            return redirect("useradmin:change_password")
        
        if check_password(old_password, user.password):
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password Changed Successfully")
            return redirect("useradmin:change_password")
        else:
            messages.error(request, "Old password is not correct")
            return redirect("useradmin:change_password")
    
    return render(request, "useradmin/change_password.html")

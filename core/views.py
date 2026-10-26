
import json

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from taggit.models import Tag
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
from core.storefront import SAMPLE_STORE_PRODUCTS
from core.payments import ZarinpalError, create_payment, verify_payment
from userauths.models import ContactUs, Profile
from core.forms import AccountDetailsForm, AddressForm, ProductReviewForm
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from django.urls import reverse
from django.db import transaction
from paypal.standard.forms import PayPalPaymentsForm
from django.contrib.auth.decorators import login_required

from decimal import Decimal
from django.db.models import Count, Avg, Q
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from core.storefront import HOME_CATEGORIES, HOME_PRODUCT_TERMS, STORE_PROFILE
from django.views.decorators.http import require_POST
from userauths.forms import ProfileForm
from django.contrib.auth import login


def _personal_care_product_filter():
    product_filter = Q()
    for term in HOME_PRODUCT_TERMS:
        product_filter |= Q(title__icontains=term) | Q(category__title__icontains=term)
    return product_filter


def _personal_care_category_filter():
    category_filter = Q(title__in=[item["name"] for item in HOME_CATEGORIES])
    for term in HOME_PRODUCT_TERMS:
        category_filter |= Q(title__icontains=term)
    return category_filter


def _amazing_offers_products():
    """Discounted products; falls back to featured when none are on sale."""
    on_sale = (
        Product.objects.filter(
            product_status="published",
            status=True,
            is_sale=True,
            sale_price__gt=0,
        )
        .annotate(
            review_count=Count("نظرات", filter=Q(نظرات__is_approved=True)),
            average_rating=Avg("نظرات__rating", filter=Q(نظرات__is_approved=True)),
        )
        .order_by("-date")[:10]
    )
    if on_sale.exists():
        return list(on_sale), True

    featured = (
        Product.objects.filter(
            product_status="published",
            status=True,
            featured=True,
        )
        .annotate(
            review_count=Count("نظرات", filter=Q(نظرات__is_approved=True)),
            average_rating=Avg("نظرات__rating", filter=Q(نظرات__is_approved=True)),
        )
        .order_by("-date")[:10]
    )
    return list(featured), False


def index(request):
    products = (
        Product.objects.filter(product_status="published", status=True)
        .annotate(
            review_count=Count("نظرات", filter=Q(نظرات__is_approved=True)),
            average_rating=Avg("نظرات__rating", filter=Q(نظرات__is_approved=True)),
        )
        .order_by("-featured", "-date")[:12]
    )
    categories = Category.objects.filter(_personal_care_category_filter()).distinct()
    comparison_products = []
    for home_category in HOME_CATEGORIES:
        matching_product = (
            Product.objects.filter(product_status="published", status=True)
            .filter(
                Q(title__icontains=home_category["query"])
                | Q(category__title__icontains=home_category["name"])
            )
            .order_by("-featured", "-date")
            .first()
        )
        if matching_product:
            comparison_products.append(matching_product)

    amazing_products, amazing_is_sale = _amazing_offers_products()
    amazing_settings = AmazingOffersSettings.get_settings()
    amazing_banners = list(
        Banner.objects.filter(is_active=True, placement="amazing_offers").order_by("sort_order", "id")
    )
    digital_banners = list(
        DigitalBanner.objects.filter(is_active=True).order_by("sort_order", "id")[:5]
    )

    context = {
        "products": products,
        "categories": categories,
        "home_categories": HOME_CATEGORIES,
        "store_profile": STORE_PROFILE,
        "hero_banners": HeroBanner.objects.filter(is_active=True)[:3],
        "digital_banners": digital_banners,
        "trust_features": StoreTrustFeature.objects.filter(is_active=True)[:4],
        "bundles": ProductBundle.objects.filter(is_active=True).prefetch_related("products")[:3],
        "faqs": FAQ.objects.filter(is_active=True)[:8],
        "comparison_products": comparison_products,
        "amazing_products": amazing_products,
        "amazing_is_sale": amazing_is_sale,
        "amazing_settings": amazing_settings,
        "amazing_banners": amazing_banners,
        "customer_reviews": ProductReview.objects.filter(
            is_approved=True,
            product__isnull=False,
        ).select_related("user", "product").order_by("-date")[:4],
        "has_sample_products": Product.objects.filter(
            product_status="published",
            status=True,
            title__contains="(نمونه)",
        ).exists(),
    }

    return render(request, 'core/index.html', context)


@require_GET
def service_worker(request):
    worker_path = settings.BASE_DIR / "static" / "js" / "service-worker.js"
    response = HttpResponse(
        worker_path.read_bytes(),
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def product_list_view(request):
    products = Product.objects.filter(
        product_status="published",
        status=True,
    ).filter(_personal_care_product_filter()).order_by("-featured", "-date")
    tags = Tag.objects.all().order_by("-id")[:6]

    context = {
        "products":products,
        "tags":tags,
    }

    return render(request, "core/store-product-list.html", context)


def category_list_view(request):
    categories = Category.objects.filter(_personal_care_category_filter()).distinct()

    context = {
        "categories":categories
    }
    return render(request, 'core/store-category-list.html', context)


def category_product_list__view(request, cid):

    category = get_object_or_404(Category, cid=cid)
    products = Product.objects.filter(
        product_status="published",
        status=True,
        category=category,
    )

    context = {
        "category":category,
        "products":products,
    }
    return render(request, "core/store-category-products.html", context)


def subcategory_product_list__view(request, scid):

    subcategory = get_object_or_404(SubCategory, scid=scid)
    products = Product.objects.filter(
        product_status="published",
        status=True,
        subcategory=subcategory,
    )

    context = {
        "category": subcategory.category,
        "subcategory": subcategory,
        "products": products,
    }
    return render(request, "core/store-category-products.html", context)


def vendor_list_view(request):
    vendors = Vendor.objects.all()
    context = {
        "vendors": vendors,
    }
    return render(request, "core/vendor-list.html", context)


def vendor_detail_view(request, vid):
    vendor = Vendor.objects.get(vid=vid)
    products = Product.objects.filter(vendor=vendor, product_status="published").order_by("-id")

    context = {
        "vendor": vendor,
        "products": products,
    }
    return render(request, "core/vendor-detail.html", context)


def product_detail_view(request, pid):
    product_lookup = {"pid": pid}
    if not request.user.is_superuser:
        product_lookup.update(product_status="published", status=True)
    product = get_object_or_404(Product, **product_lookup)
    products = Product.objects.filter(category=product.category).exclude(pid=pid)

    # Getting all reviews related to a product
    reviews = ProductReview.objects.filter(
        product=product,
        is_approved=True,
    ).order_by("-date")

    # Getting average review
    average_rating = ProductReview.objects.filter(
        product=product,
        is_approved=True,
    ).aggregate(rating=Avg('rating'))

    # Product Review form
    review_form = ProductReviewForm()


    make_review = True 

    if request.user.is_authenticated:
        user_review_count = ProductReview.objects.filter(user=request.user, product=product).count()

        if user_review_count > 0:
            make_review = False
    
    p_image = product.p_images.all()
    spin_sequence = next(
        (
            item.get("spin_sequence")
            for item in SAMPLE_STORE_PRODUCTS
            if item["title"] == product.title
        ),
        None,
    )
    spin_frames = []
    if spin_sequence:
        frame_prefix = f"store-samples/360/{spin_sequence}/frame-"
        spin_frames = [
            image.images.url
            for image in p_image.filter(images__startswith=frame_prefix).order_by(
                "images"
            )
        ]

    product_description = strip_tags(product.description or "").strip()
    product_schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.title,
        "description": product_description[:500],
        "image": request.build_absolute_uri(product.image.url) if product.image else "",
        "brand": {"@type": "Brand", "name": "Hazhirmarket"},
    }
    if "(نمونه)" not in product.title:
        product_price = _product_price(product)
        if product_price > 0:
            product_schema["offers"] = {
                "@type": "Offer",
                "url": request.build_absolute_uri(
                    reverse("core:product-detail", args=[product.pid])
                ),
                "priceCurrency": "IRR",
                "price": str(int(product_price * Decimal("10"))),
                "availability": (
                    "https://schema.org/InStock"
                    if product.in_stock
                    else "https://schema.org/OutOfStock"
                ),
            }
    product_schema_json = json.dumps(
        product_schema,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    product_schema_json = (
        product_schema_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )

    context = {
        "p": product,
        "make_review": make_review,
        "review_form": review_form,
        "p_image": p_image,
        "spin_frames": spin_frames,
        "average_rating": average_rating,
        "reviews": reviews,
        "products": products,
        "faqs": FAQ.objects.filter(is_active=True),
        "meta_product_description": product_description[:200],
        "product_schema_json": mark_safe(product_schema_json),
        "warranty_options": product.warranty_options(),
        "authenticity_badges": product.authenticity_badges(),
    }

    return render(request, "core/store-product-detail.html", context)

def tag_list(request, tag_slug=None):

    products = Product.objects.filter(product_status="published").order_by("-id")

    tag = None 
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        products = products.filter(tags__in=[tag])

    context = {
        "products": products,
        "tag": tag
    }

    return render(request, "core/tag.html", context)


def ajax_add_review(request, pid):
    product = Product.objects.get(pk=pid)
    user = request.user 

    review = ProductReview.objects.create(
        user=user,
        product=product,
        review = request.POST['review'],
        rating = request.POST['rating'],
    )

    context = {
        'user': user.username,
        'review': request.POST['review'],
        'rating': request.POST['rating'],
        'message': 'دیدگاه شما پس از بررسی مدیر فروشگاه منتشر می‌شود.',
    }

    average_reviews = ProductReview.objects.filter(product=product).aggregate(rating=Avg("rating"))

    return JsonResponse(
       {
         'bool': True,
        'context': context,
        'average_reviews': average_reviews
       }
    )


def search_view(request):
    query = (request.GET.get("q") or "").strip()
    products = Product.objects.filter(
        product_status="published",
        status=True,
    ).filter(_personal_care_product_filter()).order_by("-date")

    if query:
        query_variants = {query, query.replace(" ", "‌"), query.replace("‌", " ")}
        if "اتومو" in query.replace("‌", "").replace(" ", ""):
            query_variants.add("حالت‌دهندهٔ مو")
        search_filter = Q()
        for variant in query_variants:
            search_filter |= Q(title__icontains=variant) | Q(category__title__icontains=variant)
        products = products.filter(search_filter).distinct()

    context = {
        "products": products,
        "query": query,
    }
    return render(request, "core/store-search.html", context)


def filter_product(request):
    categories = request.GET.getlist("category[]")
    vendors = request.GET.getlist("vendor[]")


    min_price = request.GET['min_price']
    max_price = request.GET['max_price']

    products = Product.objects.filter(product_status="published").order_by("-id").distinct()

    products = products.filter(price__gte=min_price)
    products = products.filter(price__lte=max_price)


    if len(categories) > 0:
        products = products.filter(category__id__in=categories).distinct() 
    else:
        products = Product.objects.filter(product_status="published").order_by("-id").distinct()
    if len(vendors) > 0:
        products = products.filter(vendor__id__in=vendors).distinct() 
    else:
        products = Product.objects.filter(product_status="published").order_by("-id").distinct()    
    
       

    
    data = render_to_string("core/async/product-list.html", {"products": products})
    return JsonResponse({"data": data})


def _cart_product(product_id):
    try:
        product = Product.objects.get(
            pk=product_id,
            product_status="published",
            status=True,
        )
    except (Product.DoesNotExist, ValueError, TypeError):
        return None
    if not product.in_stock and "(نمونه)" not in product.title:
        return None
    return product


def _product_price(product):
    return product.sale_price if product.is_sale and product.sale_price > 0 else product.price


def _cart_item(product, quantity, warranty_months=0, warranty_price=0):
    price = _product_price(product)
    unit_price = price + warranty_price
    return {
        "title": product.title,
        "qty": quantity,
        "price": str(unit_price),
        "base_price": str(price),
        "warranty_months": warranty_months,
        "warranty_price": str(warranty_price),
        "image": product.image.url if product.image else "",
        "pid": product.pid,
        "is_demo_sample": "(نمونه)" in product.title,
    }


def _warranty_price_for(product, months):
    """قیمت گارانتی برای تعداد ماه مشخص؛ اگر محصول گارانتی فعال ندارد، صفر برمی‌گرداند."""
    if not product.has_warranty:
        return 0
    mapping = {
        6: product.warranty_6_price,
        12: product.warranty_12_price,
        24: product.warranty_24_price,
    }
    price = mapping.get(months, 0)
    return int(price or 0)


def _cart_item_count(cart_data):
    count = 0
    for item in cart_data.values():
        if not isinstance(item, dict):
            continue
        try:
            count += max(0, int(item.get("qty", 0)))
        except (TypeError, ValueError):
            continue
    return count


def _refresh_cart(request):
    cart_data = request.session.get("cart_data_obj", {})
    if not isinstance(cart_data, dict):
        cart_data = {}
    refreshed = {}
    for product_id, item in cart_data.items():
        try:
            quantity = int(item["qty"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 1 <= quantity <= 99:
            continue
        product = _cart_product(product_id)
        if product:
            warranty_months = 0
            warranty_price = 0
            if product.has_warranty:
                try:
                    warranty_months = int(item.get("warranty_months", 0) or 0)
                except (TypeError, ValueError):
                    warranty_months = 0
                warranty_price = _warranty_price_for(product, warranty_months)
            refreshed[str(product.id)] = _cart_item(
                product, quantity, warranty_months, warranty_price
            )
    request.session["cart_data_obj"] = refreshed
    return refreshed


@require_POST
def add_to_cart(request):
    product = _cart_product(request.POST.get("id"))
    if product is None:
        return JsonResponse(
            {"data": False, "message": "این کالا در حال حاضر برای خرید در دسترس نیست."},
            status=404,
        )
    try:
        quantity = int(request.POST.get("qty", "1"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"data": False, "message": "تعداد واردشده معتبر نیست."},
            status=400,
        )
    if quantity < 1 or quantity > 99:
        return JsonResponse(
            {"data": False, "message": "تعداد باید بین ۱ تا ۹۹ باشد."},
            status=400,
        )

    cart_data = _refresh_cart(request)
    product_id = str(product.id)
    if product_id in cart_data:
        try:
            quantity += int(cart_data[product_id]["qty"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse(
                {"data": False, "message": "اطلاعات سبد خرید نامعتبر است؛ صفحه را دوباره بارگذاری کنید."},
                status=400,
            )
    if quantity > 99:
        return JsonResponse(
            {"data": False, "message": "حداکثر تعداد هر کالا در سبد ۹۹ عدد است."},
            status=400,
        )

    # گارانتی انتخابی کاربر (فقط اگر محصول گارانتی فعال داشته باشد)
    warranty_months = 0
    warranty_price = 0
    if product.has_warranty:
        try:
            warranty_months = int(request.POST.get("warranty_months", "0") or "0")
        except (TypeError, ValueError):
            warranty_months = 0
        if warranty_months not in (0, 6, 12, 24):
            warranty_months = 0
        warranty_price = _warranty_price_for(product, warranty_months)

    cart_data[product_id] = _cart_item(
        product, quantity, warranty_months, warranty_price
    )
    request.session["cart_data_obj"] = cart_data
    return JsonResponse({
        "data": cart_data,
        "totalcartitems": _cart_item_count(cart_data),
    })



def cart_view(request):
    cart_total_amount = 0
    cart_data = {
        product_id: dict(item)
        for product_id, item in _refresh_cart(request).items()
    }
    for item in cart_data.values():
        item["line_total"] = Decimal(str(item["price"])) * int(item["qty"])
        item["line_total_display"] = f"{item['line_total']:,.0f}"
        cart_total_amount += item["line_total"]
    return render(request, "core/store-cart.html", {
        "cart_data": cart_data,
        "totalcartitems": _cart_item_count(cart_data),
        "cart_line_count": len(cart_data),
        "cart_total_amount": cart_total_amount,
        "cart_total_display": f"{cart_total_amount:,.0f}",
        "has_demo_items": any(
            item.get("is_demo_sample", False) for item in cart_data.values()
        ),
    })


@require_POST
def delete_item_from_cart(request):
    product_id = request.POST.get("id", "")
    cart_data = request.session.get("cart_data_obj", {})
    if not isinstance(cart_data, dict) or product_id not in cart_data:
        return JsonResponse(
            {"data": False, "message": "این کالا در سبد خرید پیدا نشد."},
            status=404,
        )
    del cart_data[product_id]
    request.session["cart_data_obj"] = cart_data
    return JsonResponse({"data": True, "totalcartitems": _cart_item_count(cart_data)})


@require_POST
def update_cart(request):
    product_id = request.POST.get("id", "")
    cart_data = request.session.get("cart_data_obj", {})
    if not isinstance(cart_data, dict) or product_id not in cart_data:
        return JsonResponse(
            {"data": False, "message": "این کالا در سبد خرید پیدا نشد."},
            status=404,
        )
    try:
        quantity = int(request.POST.get("qty", ""))
    except (TypeError, ValueError):
        return JsonResponse(
            {"data": False, "message": "تعداد واردشده معتبر نیست."},
            status=400,
        )
    if not 1 <= quantity <= 99:
        return JsonResponse(
            {"data": False, "message": "تعداد باید بین ۱ تا ۹۹ باشد."},
            status=400,
        )
    product = _cart_product(product_id)
    if product is None:
        return JsonResponse(
            {"data": False, "message": "این کالا دیگر برای خرید در دسترس نیست؛ سبد را تازه‌سازی کنید."},
            status=409,
        )
    # حفظ گارانتی انتخابی هنگام تغییر تعداد
    existing = cart_data[product_id] if isinstance(cart_data[product_id], dict) else {}
    warranty_months = 0
    warranty_price = 0
    if product.has_warranty:
        try:
            warranty_months = int(existing.get("warranty_months", 0) or 0)
        except (TypeError, ValueError):
            warranty_months = 0
        warranty_price = _warranty_price_for(product, warranty_months)
    cart_data[product_id] = _cart_item(
        product, quantity, warranty_months, warranty_price
    )
    request.session["cart_data_obj"] = cart_data
    return JsonResponse({"data": True, "totalcartitems": _cart_item_count(cart_data)})


@login_required
def save_checkout_info(request):
    if request.method != "POST":
        return redirect("core:cart")

    cart_data = request.session.get("cart_data_obj", {})
    if not isinstance(cart_data, dict) or not cart_data:
        messages.error(request, "سبد خرید خالی است.")
        return redirect("core:cart")

    customer = {
        "full_name": (request.POST.get("full_name") or "").strip(),
        "email": (request.POST.get("email") or "").strip(),
        "phone": (request.POST.get("mobile") or "").strip(),
        "address": (request.POST.get("address") or "").strip(),
        "city": (request.POST.get("city") or "").strip(),
        "state": (request.POST.get("state") or "").strip(),
        "country": (request.POST.get("country") or "").strip(),
    }
    if not all(customer.values()):
        messages.error(request, "لطفاً همهٔ اطلاعات تماس و نشانی را کامل کنید.")
        return redirect("core:cart")

    try:
        validate_email(customer["email"])
    except ValidationError:
        messages.error(request, "نشانی ایمیل واردشده معتبر نیست.")
        return redirect("core:cart")

    try:
        order_items = []
        total_amount = Decimal("0")
        product_ids = []
        for product_id, item in cart_data.items():
            quantity = int(item["qty"])
            if quantity < 1 or quantity > 99:
                raise ValueError
            product_ids.append(int(product_id))
        with transaction.atomic():
            products_by_id = {
                product.id: product
                for product in Product.objects.select_for_update().filter(
                    id__in=product_ids,
                    product_status="published",
                    status=True,
                )
            }
            for product_id, item in cart_data.items():
                quantity = int(item["qty"])
                product = products_by_id.get(int(product_id))
                if product is None or (
                    not product.in_stock and "(نمونه)" not in product.title
                ):
                    raise ValueError
                price = _product_price(product)
                line_total = price * quantity
                total_amount += line_total
                order_items.append((product, quantity, price, line_total))

            order = CartOrder.objects.create(
                user=request.user,
                price=total_amount,
                **customer,
            )
            for product, quantity, price, line_total in order_items:
                CartOrderProducts.objects.create(
                    order=order,
                    invoice_no=f"INVOICE_NO-{order.id}",
                    product_status="processing",
                    item=product.title,
                    image=product.image.url if product.image else "",
                    qty=quantity,
                    price=price,
                    total=line_total,
                )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        messages.error(request, "قیمت یا موجودی یکی از کالاها تغییر کرده است؛ سبد خرید را بررسی کنید.")
        return redirect("core:cart")

    request.session["cart_data_obj"] = {}
    return redirect("core:checkout", order.oid)



@login_required
def checkout(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)
    order_items = CartOrderProducts.objects.filter(order=order)

    if request.method == "POST":
        if request.POST.get("action") == "pay":
            if order.paid_status:
                messages.info(request, "پرداخت این سفارش قبلاً تأیید شده است.")
                return redirect("core:checkout", order.oid)
            if order_items.filter(item__contains="(نمونه)").exists():
                messages.error(request, "برای کالاهای نمونه امکان پرداخت واقعی وجود ندارد.")
                return redirect("core:checkout", order.oid)
            if not settings.ZARINPAL_MERCHANT_ID:
                messages.error(
                    request,
                    "درگاه زرین‌پال آمادهٔ اتصال است؛ شناسهٔ پذیرنده هنوز تنظیم نشده است.",
                )
                return redirect("core:checkout", order.oid)

            amount_rial = int((order.price * Decimal("10")).to_integral_value())
            if amount_rial <= 0:
                messages.error(request, "مبلغ سفارش برای پرداخت معتبر نیست.")
                return redirect("core:checkout", order.oid)

            pending_attempt = order.payment_attempts.filter(status="pending").first()
            if pending_attempt:
                if pending_attempt.amount_rial != amount_rial:
                    messages.error(
                        request,
                        "برای این سفارش یک پرداخت ناتمام با مبلغ دیگری وجود دارد؛ پیش از تلاش دوباره با پشتیبانی تماس بگیرید.",
                    )
                    return redirect("core:checkout", order.oid)
                sandbox_host = (
                    "https://sandbox.zarinpal.com"
                    if settings.ZARINPAL_SANDBOX
                    else "https://payment.zarinpal.com"
                )
                return redirect(f"{sandbox_host}/pg/StartPay/{pending_attempt.authority}")

            callback_url = request.build_absolute_uri(
                reverse("core:zarinpal-callback", args=[order.oid])
            )
            try:
                payment = create_payment(
                    merchant_id=settings.ZARINPAL_MERCHANT_ID,
                    amount_rial=amount_rial,
                    callback_url=callback_url,
                    description=f"پرداخت سفارش Hazhirmarket {order.oid}",
                    email=order.email or "",
                    mobile=order.phone or "",
                    sandbox=settings.ZARINPAL_SANDBOX,
                )
            except ZarinpalError as exc:
                messages.error(request, str(exc))
                return redirect("core:checkout", order.oid)

            PaymentAttempt.objects.create(
                order=order,
                authority=payment["authority"],
                amount_rial=amount_rial,
            )
            return redirect(payment["payment_url"])

        code = request.POST.get("code")
        coupon = Coupon.objects.filter(code=code, active=True).first()
        if coupon:
            if order.payment_attempts.filter(status="pending").exists():
                messages.error(
                    request,
                    "تا تعیین تکلیف پرداخت درحال‌انتظار، امکان تغییر مبلغ سفارش وجود ندارد.",
                )
                return redirect("core:checkout", order.oid)
            if coupon in order.coupons.all():
                messages.warning(request, "این کد تخفیف پیش‌تر برای سفارش اعمال شده است.")
                return redirect("core:checkout", order.oid)
            else:
                discount = order.price * coupon.discount / 100 

                order.coupons.add(coupon)
                order.price -= discount
                order.saved += discount
                order.save()

                messages.success(request, "کد تخفیف با موفقیت اعمال شد.")
                return redirect("core:checkout", order.oid)
        else:
            messages.error(request, "کد تخفیف معتبر یا فعال نیست.")

    context = {
        "order": order,
        "order_items": order_items,
        "has_demo_items": order_items.filter(item__contains="(نمونه)").exists(),
        "zarinpal_configured": bool(settings.ZARINPAL_MERCHANT_ID),
    }
    return render(request, "core/store-checkout.html", context)


@require_GET
def zarinpal_callback(request, oid):
    authority = (request.GET.get("Authority") or "").strip()
    gateway_status = (request.GET.get("Status") or "").strip().upper()
    if not authority:
        return HttpResponseBadRequest("شناسهٔ پرداخت در درخواست درگاه موجود نیست.")

    attempt = get_object_or_404(
        PaymentAttempt.objects.select_related("order"),
        order__oid=oid,
        authority=authority,
    )
    order = attempt.order
    if attempt.status == "paid" or order.paid_status:
        return redirect("core:payment-completed", oid=order.oid)

    if gateway_status != "OK":
        if attempt.status == "pending":
            attempt.status = "failed"
            attempt.save(update_fields=["status", "updated_at"])
        return render(request, "core/payment-failed.html", {
            "order": order,
            "payment_message": "پرداخت از سوی شما لغو شد یا درگاه آن را ناموفق اعلام کرد.",
        })

    if not settings.ZARINPAL_MERCHANT_ID:
        return render(request, "core/payment-failed.html", {
            "order": order,
            "payment_message": "شناسهٔ پذیرندهٔ زرین‌پال در تنظیمات سرور موجود نیست؛ وضعیت پرداخت تغییر نکرده است.",
        }, status=503)

    expected_amount = int((order.price * Decimal("10")).to_integral_value())
    if expected_amount != attempt.amount_rial:
        return render(request, "core/payment-failed.html", {
            "order": order,
            "payment_message": "مبلغ سفارش پس از شروع پرداخت تغییر کرده است؛ برای بررسی با پشتیبانی تماس بگیرید.",
        }, status=409)

    try:
        verification = verify_payment(
            merchant_id=settings.ZARINPAL_MERCHANT_ID,
            amount_rial=attempt.amount_rial,
            authority=attempt.authority,
            sandbox=settings.ZARINPAL_SANDBOX,
        )
    except ZarinpalError as exc:
        return render(request, "core/payment-failed.html", {
            "order": order,
            "payment_message": str(exc),
        }, status=502)

    with transaction.atomic():
        locked_attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        locked_order = CartOrder.objects.select_for_update().get(pk=order.pk)
        if not locked_order.paid_status:
            locked_attempt.status = "paid"
            locked_attempt.ref_id = verification["ref_id"]
            locked_attempt.save(update_fields=["status", "ref_id", "updated_at"])
            locked_order.paid_status = True
            locked_order.save(update_fields=["paid_status"])

    return redirect("core:payment-completed", oid=order.oid)


@login_required
def payment_demo_view(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)
    has_demo_items = CartOrderProducts.objects.filter(
        order=order,
        item__contains="(نمونه)",
    ).exists()
    return render(request, "core/store-payment-demo.html", {
        "order": order,
        "demo_confirmed": request.method == "POST",
        "has_demo_items": has_demo_items,
    })


@login_required
def payment_completed_view(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)
    if not order.paid_status:
        messages.error(
            request,
            "وضعیت پرداخت از سمت درگاه تأیید نشده است؛ این سفارش پرداخت‌شده ثبت نشده است.",
        )
        return redirect("core:checkout", order.oid)

    context = {
        "order": order,
    }
    return render(request, 'core/payment-completed.html',  context)

@login_required
def payment_failed_view(request):
    return render(request, 'core/payment-failed.html')


@login_required
def customer_dashboard(request):
    orders_list = CartOrder.objects.filter(user=request.user).order_by("-id")
    addresses = Address.objects.filter(user=request.user).order_by("-status", "-id")
    user_profile, _ = Profile.objects.get_or_create(user=request.user)
    address_form = AddressForm()
    account_form = AccountDetailsForm(user=request.user)
    profile_form = ProfileForm(instance=user_profile)
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "address":
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                new_address = address_form.save(commit=False)
                new_address.user = request.user
                new_address.status = not addresses.filter(status=True).exists()
                new_address.save()
                messages.success(request, "نشانی با موفقیت ثبت شد.")
                return redirect(f"{reverse('core:dashboard')}#address")
        elif form_type == "account":
            account_form = AccountDetailsForm(
                request.POST,
                user=request.user,
            )
            if account_form.is_valid():
                account_form.save()
                messages.success(request, "اطلاعات حساب با موفقیت به‌روزرسانی شد.")
                return redirect(f"{reverse('core:dashboard')}#account-detail")
        elif form_type == "password":
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "گذرواژه با موفقیت تغییر کرد.")
                return redirect(f"{reverse('core:dashboard')}#account-detail")
        elif form_type == "profile":
            profile_form = ProfileForm(
                request.POST,
                request.FILES,
                instance=user_profile,
            )
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "نمایهٔ شما با موفقیت به‌روزرسانی شد.")
                return redirect(f"{reverse('core:dashboard')}#account-detail")
        else:
            return HttpResponseBadRequest("درخواست حساب نامعتبر است.")

    context = {
        "user_profile": user_profile,
        "orders_list": orders_list,
        "addresses": addresses,
        "address_form": address_form,
        "account_form": account_form,
        "profile_form": profile_form,
        "password_form": password_form,
        "total_orders": orders_list.count(),
        "unpaid_orders": orders_list.filter(paid_status=False).count(),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def order_detail(request, id):
    order = get_object_or_404(CartOrder, user=request.user, id=id)
    order_items = CartOrderProducts.objects.filter(order=order)

    
    context = {
        "order_items": order_items,
    }
    return render(request, 'core/order-detail.html', context)


@login_required
@require_POST
def make_address_default(request):
    address = get_object_or_404(Address, user=request.user, id=request.POST.get("id"))
    with transaction.atomic():
        Address.objects.filter(user=request.user).update(status=False)
        address.status = True
        address.save(update_fields=("status",))
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"boolean": True})
    messages.success(request, "نشانی پیش‌فرض با موفقیت تغییر کرد.")
    return redirect(f"{reverse('core:dashboard')}#address")

@login_required
def wishlist_view(request):
    wishlist = wishlist_model.objects.all()
    context = {
        "w":wishlist
    }
    return render(request, "core/wishlist.html", context)


    # w

def add_to_wishlist(request):
    product_id = request.GET['id']
    product = Product.objects.get(id=product_id)
    print("product id isssssssssssss:" + product_id)

    context = {}

    wishlist_count = wishlist_model.objects.filter(product=product, user=request.user).count()
    print(wishlist_count)

    if wishlist_count > 0:
        context = {
            "bool": True
        }
    else:
        new_wishlist = wishlist_model.objects.create(
            user=request.user,
            product=product,
        )
        context = {
            "bool": True
        }

    return JsonResponse(context)


# def remove_wishlist(request):
#     pid = request.GET['id']
#     wishlist = wishlist_model.objects.filter(user=request.user).values()

#     product = wishlist_model.objects.get(id=pid)
#     h = product.delete()

#     context = {
#         "bool": True,
#         "wishlist":wishlist
#     }
#     t = render_to_string("core/async/wishlist-list.html", context)
#     return JsonResponse({"data": t, "w":wishlist})

def remove_wishlist(request):
    pid = request.GET['id']
    wishlist = wishlist_model.objects.filter(user=request.user)
    wishlist_d = wishlist_model.objects.get(id=pid)
    delete_product = wishlist_d.delete()
    
    context = {
        "bool":True,
        "w":wishlist
    }
    wishlist_json = serializers.serialize('json', wishlist)
    t = render_to_string('core/async/wishlist-list.html', context)
    return JsonResponse({'data':t,'w':wishlist_json})





# Other Pages 
def contact(request):
    return render(request, "core/contact.html")


def ajax_contact_form(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "روش درخواست پشتیبانی نمی‌شود."},
            status=405,
        )

    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    subject = request.POST.get('subject', '').strip()
    message = request.POST.get('message', '').strip()

    if not all([full_name, phone, message]):
        return JsonResponse(
            {"status": "error", "message": "لطفاً نام، شمارهٔ تماس و پیام را کامل کنید."},
            status=400,
        )

    if not subject:
        subject = "درخواست مشاوره خرید"

    normalized_phone = ''.join(character for character in phone if character.isdigit())
    if not 8 <= len(normalized_phone) <= 15:
        return JsonResponse(
            {"status": "error", "message": "شمارهٔ تماس واردشده معتبر نیست."},
            status=400,
        )

    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse(
                {"status": "error", "message": "نشانی ایمیل واردشده معتبر نیست."},
                status=400,
            )

    ContactUs.objects.create(
        full_name=full_name,
        email=email,
        phone=normalized_phone,
        subject=subject,
        message=message,
    )

    return JsonResponse(
        {"status": "success", "message": "درخواست شما ثبت شد؛ به‌زودی با شما تماس می‌گیریم."}
    )


def about_us(request):
    return render(request, "core/about_us.html")


def purchase_guide(request):
    return render(request, "core/purchase_guide.html")

def privacy_policy(request):
    return render(request, "core/privacy_policy.html")

def terms_of_service(request):
    return render(request, "core/terms_of_service.html")


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    return HttpResponse(
        f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n",
        content_type="text/plain; charset=utf-8",
    )


def auto_login(request):
    """Temporary view for auto-login to admin panel"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(username='admin')
        login(request, user)
        return redirect('/admin/')
    except User.DoesNotExist:
        return HttpResponse("Admin user not found. Please create a superuser first.")

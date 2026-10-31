from ast import Add
import re
from django.conf import settings
from core.models import Product, Category, Vendor, CartOrder, ProductImages, ProductReview, wishlist_model, Address
from django.db.models import Min, Max, Q
from django.contrib import messages
from core.storefront import HOME_CATEGORIES, HOME_PRODUCT_TERMS, STORE_PROFILE
from core.navigation import build_category_filter, get_nav_categories

def default(request):
    cart_data = request.session.get("cart_data_obj", {})
    cart_item_count = 0
    if isinstance(cart_data, dict):
        for item in cart_data.values():
            if isinstance(item, dict):
                try:
                    quantity = int(item.get("qty", 0))
                except (TypeError, ValueError):
                    continue
                if quantity > 0:
                    cart_item_count += quantity

    # ``categories`` is kept as a queryset for the existing templates that
    # walk ``c.subcategories``; the header uses the cached ``nav_categories``
    # payload instead so it does not pay for this query on every request.
    category_filter = build_category_filter()
    categories = Category.objects.filter(category_filter).prefetch_related("subcategories").distinct()
    vendors = Vendor.objects.all()

    min_max_price = Product.objects.aggregate(Min("price"), Max("price"))

    if request.user.is_authenticated:
        try:
            wishlist = wishlist_model.objects.filter(user=request.user)
        except:
            messages.warning(request, "You need to login before accessing your wishlist.")
            wishlist = 0
    else:
        wishlist = 0

    
    
    try:
        address = Address.objects.get(user=request.user)
    except:
        address = None

    widget_id = str(getattr(settings, 'GOFTINO_WIDGET_ID', '') or '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{6,64}', widget_id):
        widget_id = ''

    return {
        'categories':categories,
        'nav_categories': get_nav_categories(),
        'wishlist':wishlist,
        'address':address,
        'vendors':vendors,
        'min_max_price':min_max_price,
        'store_profile': STORE_PROFILE,
        'cart_item_count': cart_item_count,
        'goftino_widget_id': widget_id,
        'preview_tab_enabled': getattr(settings, 'PREVIEW_TAB_ENABLED', False),
    }
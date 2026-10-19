from ast import Add
from core.models import Product, Category, Vendor, CartOrder, ProductImages, ProductReview, wishlist_model, Address
from django.db.models import Min, Max, Q
from django.contrib import messages
from core.storefront import HOME_CATEGORIES, HOME_PRODUCT_TERMS, STORE_PROFILE

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

    category_filter = Q(title__in=[item["name"] for item in HOME_CATEGORIES])
    for term in HOME_PRODUCT_TERMS:
        category_filter |= Q(title__icontains=term)
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

    return {
        'categories':categories,
        'wishlist':wishlist,
        'address':address,
        'vendors':vendors,
        'min_max_price':min_max_price,
        'store_profile': STORE_PROFILE,
        'cart_item_count': cart_item_count,
    }
"""Cached navigation payload for the storefront header.

The header is rendered on every page, and the category menu used to run a
``Category.objects.filter(...).prefetch_related(...)`` query on each
request. This module builds the menu once, converts it to plain frozen
dataclasses (no lazy QuerySets, so it can be pickled by any cache backend)
and caches it for a short window.

Admin edits still show up quickly: the TTL is deliberately short, and
``invalidate_nav_cache()`` is exported for callers that want to drop the
entry immediately (e.g. a ``Category`` post_save signal).
"""

from dataclasses import dataclass

from django.core.cache import cache
from django.db.models import Q

from core.storefront import HOME_CATEGORIES, HOME_PRODUCT_TERMS

CACHE_KEY = "hm:navigation:categories:v4"
CACHE_TTL = 180  # seconds

# Match the storefront category strip without changing the order or content
# of categories in the database. Unknown categories retain their original
# order after the familiar storefront categories.
_NAV_CATEGORY_ORDER = {
    item["name"]: position for position, item in enumerate(HOME_CATEGORIES)
}
_NAV_FALLBACK_ICONS = {
    "لوازم شخصی": "assets/imgs/theme/icons/header-reference/personal-care.svg",
    "سلامت": "assets/imgs/theme/icons/header-reference/health.svg",
    "عطر و ادکلن": "assets/imgs/theme/icons/header-reference/perfume.svg",
    "لوازم خانگی": "assets/imgs/theme/icons/header-reference/home.svg",
    "قطعات و لوازم دیجیتال": "assets/imgs/theme/icons/header-reference/digital.svg",
    "قطعات": "assets/imgs/theme/icons/header-reference/shaver-parts.svg",
    "لوازم جانبی": "assets/imgs/theme/icons/header-reference/digital.svg",
}


@dataclass(frozen=True)
class NavSubcategory:
    scid: str
    title: str


@dataclass(frozen=True)
class NavCategory:
    cid: str
    title: str
    subcategories: tuple
    icon: str = ""
    fallback_icon: str = ""

    @property
    def has_children(self):
        return bool(self.subcategories)


def build_category_filter():
    """The Q object that limits the storefront to its visible categories."""
    category_filter = Q(title__in=[item["name"] for item in HOME_CATEGORIES])
    for term in HOME_PRODUCT_TERMS:
        category_filter |= Q(title__icontains=term)
    return category_filter


def _build_nav_categories():
    # Imported lazily so this module stays importable from settings-time code.
    from core.models import Category

    rows = (
        Category.objects.filter(build_category_filter())
        .exclude(title="قطعات و لوازم دیجیتال")
        .prefetch_related("subcategories")
        .order_by("id")
        .distinct()
    )

    payload = []
    for category in rows:
        subs = tuple(
            NavSubcategory(scid=sub.scid, title=sub.title)
            for sub in category.subcategories.all()
            if sub.is_active
        )
        payload.append(
            NavCategory(
                cid=category.cid,
                title=category.title,
                subcategories=subs,
                icon=category.icon.name if category.icon else "",
                fallback_icon=_NAV_FALLBACK_ICONS.get(category.title, "") if not category.icon else "",
            )
        )
    payload.sort(key=lambda item: _NAV_CATEGORY_ORDER.get(item.title, len(_NAV_CATEGORY_ORDER)))
    return tuple(payload)


def get_nav_categories():
    """Return the cached header categories, building them on a miss."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    payload = _build_nav_categories()
    cache.set(CACHE_KEY, payload, CACHE_TTL)
    return payload


def invalidate_nav_cache():
    cache.delete(CACHE_KEY)

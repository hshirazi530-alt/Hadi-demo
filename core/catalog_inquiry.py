"""Read-only, non-purchasable catalog awaiting verification.

This is a static snapshot of names from the shop owner's approved export.  It
never reads or writes Product rows, creates orders, or exposes snapshot prices
or stock.  Source IDs are namespaced in these routes and are not Django IDs.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "catalog_inquiry.json"
CATEGORY_LABELS = {
    "personal": "لوازم شخصی",
    "home": "لوازم خانگی",
    "health": "سلامت",
    "digital": "قطعات و لوازم دیجیتال",
    "perfume": "عطر و ادکلن",
    "other": "سایر محصولات",
}
FEATURED_IDS = (15839, 8460, 15857, 15849, 15807, 15320, 15356, 15340,
                15365, 15350, 15378, 15370)


@lru_cache(maxsize=1)
def catalog_items():
    # Only the minimal public snapshot is shipped with this update. In
    # particular, it contains no price, inventory, source URLs, descriptions,
    # customer data, or authentication material.
    with CATALOG_PATH.open(encoding="utf-8") as source:
        data = json.load(source)
    rows = data["items"]
    if data.get("format") != 1 or len(rows) != 689:
        raise RuntimeError("Unexpected inquiry catalog data")
    allowed = {"id", "title", "category", "category_label", "tone", "image", "image_alt", "note"}
    ids = set()
    for item in rows:
        if set(item) != allowed or item["category"] not in CATEGORY_LABELS:
            raise RuntimeError("Invalid inquiry catalog record")
        if item["category_label"] != CATEGORY_LABELS[item["category"]] or item["tone"] not in range(1, 7):
            raise RuntimeError("Invalid inquiry catalog category or style")
        if item["image"] and item["image"] not in (
            "assets/imgs/hazhir-catalog-inquiry/8460.webp",
            "assets/imgs/hazhir-catalog-inquiry/15839.webp",
        ):
            raise RuntimeError("Unreviewed catalog image")
        if not isinstance(item["id"], int) or item["id"] in ids:
            raise RuntimeError("Duplicate or invalid inquiry catalog ID")
        ids.add(item["id"])
    return tuple(rows)


@lru_cache(maxsize=1)
def catalog_by_id():
    return {item["id"]: item for item in catalog_items()}


def featured_items(limit=12):
    limit = max(0, min(int(limit), 12))
    by_id = catalog_by_id()
    featured = [by_id[pid] for pid in FEATURED_IDS if pid in by_id]
    seen = {item["id"] for item in featured}
    featured.extend(item for item in catalog_items() if item["id"] not in seen)
    return featured[:limit]


def noindex(response):
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@require_safe
def catalog_list(request):
    query = (request.GET.get("q") or "").strip()[:100]
    category = (request.GET.get("category") or "").strip()
    if category not in CATEGORY_LABELS:
        category = ""
    matches = catalog_items()
    if category:
        matches = [item for item in matches if item["category"] == category]
    if query:
        needle = query.casefold().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        matches = [item for item in matches if needle in item["title"].casefold().translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")) or needle in str(item["id"])]
    page = Paginator(matches, 24).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    # Restrict pagination URLs to known, bounded inputs.
    params.clear()
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    return noindex(render(request, "core/catalog_inquiry_list.html", {
        "page_obj": page,
        "items": page.object_list,
        "query": query,
        "category": category,
        "category_labels": tuple(CATEGORY_LABELS.items()),
        "total_count": page.paginator.count,
        "query_prefix": params.urlencode(),
    }))


@require_safe
def catalog_detail(request, source_id):
    item = catalog_by_id().get(source_id)
    if item is None:
        raise Http404("کالا در کاتالوگ بررسی پیدا نشد.")
    return noindex(render(request, "core/catalog_inquiry_detail.html", {"item": item}))

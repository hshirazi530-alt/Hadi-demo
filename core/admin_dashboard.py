from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import reverse
from django.utils import formats, timezone

from core.models import CartOrder, CartOrderProducts, Category, Product


ORDER_STATUS_LABELS = {
    "processing": "در حال پردازش",
    "shipped": "ارسال‌شده",
    "delivered": "تحویل‌شده",
}
DATE_RANGES = {
    "7": ("۷ روز گذشته", 7),
    "30": ("۳۰ روز گذشته", 30),
    "90": ("۹۰ روز گذشته", 90),
    "365": ("۱۲ ماه گذشته", 365),
}
ORDER_SORTS = {
    "date": "date",
    "amount": "price",
    "order": "oid",
    "status": "product_status",
}


def _period_bounds(today, period_days):
    start_date = today - timedelta(days=period_days - 1)
    end_date = today + timedelta(days=1)
    start = timezone.make_aware(datetime.combine(start_date, time.min))
    end = timezone.make_aware(datetime.combine(end_date, time.min))
    return start_date, start, end


def _trend(current, previous):
    if not previous:
        if not current:
            return {"direction": "steady", "label": "بدون تغییر"}
        return {"direction": "up", "label": "جدید"}

    change = (Decimal(current - previous) / Decimal(previous) * 100).quantize(
        Decimal("1")
    )
    if not change:
        direction = "steady"
    else:
        direction = "up" if change > 0 else "down"
    sign = "+" if change > 0 else ""
    return {
        "direction": direction,
        "label": f"{sign}{formats.number_format(change, decimal_pos=0)}٪",
    }


def _month_starts(start_date, today):
    current = date(start_date.year, start_date.month, 1)
    last = date(today.year, today.month, 1)
    starts = []
    while current <= last:
        starts.append(current)
        year = current.year + (current.month == 12)
        month = current.month % 12 + 1
        current = date(year, month, 1)
    return starts


def _chart_points(order_queryset, start_date, today, period_days):
    daily_rows = order_queryset.annotate(day=TruncDate("date")).values("day").annotate(
        orders=Count("pk"),
        revenue=Sum("price", filter=Q(paid_status=True)),
    )
    by_day = {row["day"]: row for row in daily_rows}

    if period_days == 365:
        points = []
        for month_start in _month_starts(start_date, today):
            next_month = date(
                month_start.year + (month_start.month == 12),
                month_start.month % 12 + 1,
                1,
            )
            month_rows = [
                row
                for day, row in by_day.items()
                if month_start <= day < next_month
            ]
            points.append(
                {
                    "label": formats.date_format(month_start, "b"),
                    "orders": sum(row["orders"] for row in month_rows),
                    "revenue": float(
                        sum(
                            (row["revenue"] or Decimal("0") for row in month_rows),
                            Decimal("0"),
                        )
                    ),
                }
            )
        return points

    if period_days == 90:
        points = []
        for offset in range(0, period_days, 7):
            week_start = start_date + timedelta(days=offset)
            week_end = week_start + timedelta(days=7)
            week_rows = [
                row
                for day, row in by_day.items()
                if week_start <= day < week_end
            ]
            points.append(
                {
                    "label": formats.date_format(week_start, "j M"),
                    "orders": sum(row["orders"] for row in week_rows),
                    "revenue": float(
                        sum(
                            (row["revenue"] or Decimal("0") for row in week_rows),
                            Decimal("0"),
                        )
                    ),
                }
            )
        return points

    return [
        {
            "label": formats.date_format(day, "j M"),
            "orders": by_day.get(day, {}).get("orders", 0),
            "revenue": float(by_day.get(day, {}).get("revenue") or Decimal("0")),
        }
        for day_offset in range(period_days)
        for day in [start_date + timedelta(days=day_offset)]
    ]


def _dashboard_url(request, **updates):
    query = request.GET.copy()
    for key, value in updates.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"{reverse('admin-dashboard')}?{encoded}" if encoded else reverse("admin-dashboard")


def dashboard_view(request):
    today = timezone.localdate()
    selected_period = request.GET.get("period", "30")
    if selected_period not in DATE_RANGES:
        selected_period = "30"
    period_label, period_days = DATE_RANGES[selected_period]
    start_date, period_start, period_end = _period_bounds(today, period_days)
    previous_start = period_start - timedelta(days=period_days)

    orders = CartOrder.objects.all()
    period_orders = orders.filter(date__gte=period_start, date__lt=period_end)
    previous_orders = orders.filter(date__gte=previous_start, date__lt=period_start)
    paid_orders = period_orders.filter(paid_status=True)
    previous_paid_orders = previous_orders.filter(paid_status=True)
    total_orders = period_orders.count()
    previous_order_count = previous_orders.count()
    paid_revenue = paid_orders.aggregate(total=Sum("price"))["total"] or Decimal("0")
    previous_revenue = (
        previous_paid_orders.aggregate(total=Sum("price"))["total"] or Decimal("0")
    )
    paid_order_count = paid_orders.count()
    previous_paid_order_count = previous_paid_orders.count()
    average_order_value = (
        paid_revenue / paid_order_count if paid_order_count else Decimal("0")
    )
    previous_average_order_value = (
        previous_revenue / previous_paid_order_count
        if previous_paid_order_count
        else Decimal("0")
    )

    customer_model = get_user_model()
    customers = customer_model.objects.filter(is_staff=False, is_superuser=False)
    new_customers = customers.filter(
        date_joined__gte=period_start,
        date_joined__lt=period_end,
    ).count()
    previous_new_customers = customers.filter(
        date_joined__gte=previous_start,
        date_joined__lt=period_start,
    ).count()

    chart = _chart_points(period_orders, start_date, today, period_days)
    all_category_rows = list(
        Product.objects.filter(category__isnull=False)
        .values("category__title")
        .annotate(product_count=Count("pk"))
        .order_by("-product_count", "category__title")
    )
    total_categorized_products = sum(
        row["product_count"] for row in all_category_rows
    )
    category_rows = all_category_rows[:5]
    for row in category_rows:
        row["title"] = row.pop("category__title")
        row["share"] = round(
            row["product_count"] / total_categorized_products * 100
        ) if total_categorized_products else 0

    top_products = list(
        CartOrderProducts.objects.filter(
            order__date__gte=period_start,
            order__date__lt=period_end,
            order__paid_status=True,
        )
        .values("item")
        .annotate(
            quantity=Sum("qty"),
            revenue=Sum("total"),
        )
        .order_by("-quantity", "-revenue", "item")[:5]
    )

    search_query = request.GET.get("q", "").strip()
    order_queryset = period_orders.select_related("user").prefetch_related(
        "cartorderproducts_set"
    )
    if search_query:
        order_queryset = order_queryset.filter(
            Q(oid__icontains=search_query)
            | Q(full_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(cartorderproducts__item__icontains=search_query)
        ).distinct()

    selected_sort = request.GET.get("sort", "date")
    if selected_sort not in ORDER_SORTS:
        selected_sort = "date"
    selected_direction = request.GET.get("direction", "desc")
    if selected_direction not in {"asc", "desc"}:
        selected_direction = "desc"
    sort_field = ORDER_SORTS[selected_sort]
    order_prefix = "" if selected_direction == "asc" else "-"
    order_queryset = order_queryset.order_by(
        f"{order_prefix}{sort_field}",
        f"{order_prefix}pk",
    )

    page_obj = Paginator(order_queryset, 8).get_page(request.GET.get("page", 1))
    order_rows = []
    for order in page_obj.object_list:
        items = list(order.cartorderproducts_set.all())
        order_rows.append(
            {
                "order": order,
                "customer_name": (
                    order.full_name
                    or order.user.get_full_name()
                    or order.user.username
                ),
                "item_name": items[0].item if items else "—",
                "item_count": sum(item.qty for item in items),
                "status_label": ORDER_STATUS_LABELS.get(
                    order.product_status, "در حال بررسی"
                ),
                "status_class": order.product_status,
            }
        )
    page_obj.object_list = order_rows

    sort_links = {}
    for sort_key in ORDER_SORTS:
        next_direction = (
            "asc"
            if selected_sort == sort_key and selected_direction == "desc"
            else "desc"
        )
        sort_links[sort_key] = _dashboard_url(
            request,
            sort=sort_key,
            direction=next_direction,
            page=None,
        )
    pagination_links = [
        {"number": number, "url": _dashboard_url(request, page=number)}
        for number in page_obj.paginator.page_range
    ]

    context = admin.site.each_context(request)
    context.update(
        {
            "today": today,
            "chart_data": chart,
            "period_choices": [
                {"value": value, "label": label}
                for value, (label, _) in DATE_RANGES.items()
            ],
            "selected_period": selected_period,
            "period_label": period_label,
            "total_orders": total_orders,
            "paid_order_count": paid_order_count,
            "paid_revenue": paid_revenue,
            "average_order_value": average_order_value,
            "total_products": Product.objects.count(),
            "total_customers": customers.count(),
            "new_customers": new_customers,
            "total_categories": Category.objects.count(),
            "recent_orders": page_obj,
            "filtered_order_count": page_obj.paginator.count,
            "processing_orders": period_orders.filter(
                product_status="processing"
            ).count(),
            "shipped_orders": period_orders.filter(product_status="shipped").count(),
            "delivered_orders": period_orders.filter(
                product_status="delivered"
            ).count(),
            "order_list_url": reverse("admin:core_cartorder_changelist"),
            "search_query": search_query,
            "selected_sort": selected_sort,
            "selected_direction": selected_direction,
            "sort_links": sort_links,
            "pagination_links": pagination_links,
            "first_page_url": _dashboard_url(request, page=1),
            "previous_page_url": _dashboard_url(
                request,
                page=page_obj.previous_page_number() if page_obj.has_previous() else 1,
            ),
            "next_page_url": _dashboard_url(
                request,
                page=page_obj.next_page_number()
                if page_obj.has_next()
                else page_obj.paginator.num_pages,
            ),
            "last_page_url": _dashboard_url(
                request,
                page=page_obj.paginator.num_pages,
            ),
            "clear_filters_url": reverse("admin-dashboard"),
            "range_start": start_date,
            "range_end": today,
            "trend_orders": _trend(total_orders, previous_order_count),
            "trend_revenue": _trend(paid_revenue, previous_revenue),
            "trend_customers": _trend(new_customers, previous_new_customers),
            "trend_average_order": _trend(
                average_order_value,
                previous_average_order_value,
            ),
            "category_breakdown": category_rows,
            "top_products": top_products,
            "pending_products_count": Product.objects.filter(
                product_status="in_review"
            ).count(),
            "unpaid_orders_count": orders.filter(paid_status=False).count(),
        },
    )
    return render(request, "admin/index.html", context)

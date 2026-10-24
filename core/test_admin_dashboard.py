from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CartOrder, CartOrderProducts, Category, Product


class ProductAdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="product-dashboard-admin",
            email="product-dashboard-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        cls.customer = user_model.objects.create_user(
            username="dashboard-customer",
            email="dashboard-customer@example.com",
        )
        cls.category = Category.objects.create(title="لوازم مراقبت")
        cls.product = Product.objects.create(
            user=cls.admin_user,
            category=cls.category,
            title="محصول آزمایشی پنل",
            product_status="published",
            stock_count="7",
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_admin_index_renders_persian_dashboard_and_database_counts(self):
        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="hjm-admin-loader"')
        self.assertContains(response, "داشبورد")
        self.assertContains(response, "عملکرد فروشگاه")
        self.assertContains(response, "سفارش‌های اخیر")
        self.assertContains(response, "بر اساس اطلاعات ثبت‌شده در سامانه")
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "larkon-admin admin-product-dashboard")
        self.assertContains(response, 'id="jazzy-sidebar"')
        self.assertContains(response, "/static/css/admin-sidebar.css")
        self.assertContains(response, 'id="jazzy-navbar"')
        self.assertContains(response, 'id="logout-form"')
        self.assertContains(response, "مدیریت فروشگاه")
        self.assertContains(response, "کاربران و مشتریان")
        self.assertContains(response, '<li class="nav-header">')
        self.assertNotContains(response, 'class="nav nav-treeview" style="display: none;"')
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'placeholder="جستجو محصولات...')
        for model_name in (
            "core_product",
            "core_cartorder",
            "core_category",
            "core_coupon",
            "userauths_user",
        ):
            self.assertContains(response, reverse(f"admin:{model_name}_changelist"))
        self.assertEqual(response.context["total_products"], Product.objects.count())
        self.assertEqual(response.context["total_customers"], 1)
        dashboard_content = response.content.decode()
        sidebar_content = dashboard_content.split('id="jazzy-sidebar"', 1)[1].split("</aside>", 1)[0]
        self.assertIn(
            f'<a href="{reverse("admin:core_product_changelist")}" class="nav-link">',
            sidebar_content,
        )
        menu_positions = [
            sidebar_content.index(reverse(f"admin:{model_name}_changelist"))
            for model_name in (
                "core_product",
                "core_cartorder",
                "core_category",
                "core_subcategory",
                "core_coupon",
                "core_vendor",
            )
        ]
        self.assertEqual(menu_positions, sorted(menu_positions))

    def test_admin_model_routes_remain_available(self):
        response = self.client.get(reverse("admin:core_product_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "larkon-admin")
        self.assertContains(response, "محصول")
        self.assertContains(response, "شناسهٔ محصول")
        self.assertContains(response, "موجودی")
        self.assertContains(response, "وضعیت انتشار")
        self.assertContains(response, "admin-product-thumbnail")
        self.assertContains(response, 'id="jazzy-sidebar"')
        self.assertContains(response, 'id="jazzy-navbar"')
        self.assertNotContains(response, "Product image")
        self.assertEqual(
            [field for field in response.context["cl"].list_display],
            [
                "action_checkbox",
                "product_image_preview",
                "title",
                "product_code",
                "category",
                "price",
                "inventory_count",
                "product_status_badge",
                "in_stock",
            ],
        )

    def test_admin_product_search_uses_registered_search_fields(self):
        response = self.client.get(
            reverse("admin:core_product_changelist"),
            {"q": self.product.title},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cl"].result_count, 1)
        self.assertContains(response, self.product.title)

    def test_customer_admin_labels_and_category_image_heading_are_persian(self):
        customer_list = self.client.get(reverse("admin:userauths_user_changelist"))
        self.assertEqual(customer_list.status_code, 200)
        self.assertContains(customer_list, "معرفی کوتاه")
        self.assertNotContains(customer_list, "Bio summary")

        customer_form = self.client.get(
            reverse("admin:userauths_user_change", args=(self.customer.pk,))
        )
        self.assertEqual(customer_form.status_code, 200)
        self.assertContains(customer_form, "معرفی کوتاه")

        category_list = self.client.get(reverse("admin:core_category_changelist"))
        self.assertEqual(category_list.status_code, 200)
        self.assertContains(category_list, "تصویر")
        self.assertNotContains(category_list, "Category image")

    def test_summary_chart_and_recent_orders_use_database_values(self):
        order = CartOrder.objects.create(
            user=self.customer,
            full_name="مشتری داشبورد",
            email=self.customer.email,
            price=Decimal("125000"),
            paid_status=True,
            product_status="processing",
            oid="ORD10001",
            date=timezone.now(),
        )
        CartOrderProducts.objects.create(
            order=order,
            invoice_no="INV10001",
            product_status="processing",
            item=self.product.title,
            image="product.jpg",
            qty=2,
            price=Decimal("62500"),
            total=Decimal("125000"),
        )

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_orders"], 1)
        self.assertEqual(response.context["processing_orders"], 1)
        self.assertEqual(response.context["paid_revenue"], Decimal("125000"))
        self.assertEqual(len(response.context["recent_orders"]), 1)
        self.assertEqual(response.context["recent_orders"][0]["item_name"], self.product.title)
        self.assertContains(response, "مشتری داشبورد")
        self.assertEqual(sum(point["orders"] for point in response.context["chart_data"]), 1)

    def test_empty_order_state_does_not_show_sample_orders(self):
        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_orders"], 0)
        self.assertContains(response, "هنوز سفارشی ثبت نشده است.")
        self.assertNotContains(response, "ORD10001")

    def test_date_range_updates_dashboard_metrics_and_chart_data(self):
        CartOrder.objects.create(
            user=self.customer,
            full_name="مشتری خارج بازه",
            price=Decimal("45000"),
            paid_status=True,
            oid="ORD20001",
            date=timezone.now() - timedelta(days=45),
        )

        short_range = self.client.get(reverse("admin-dashboard"), {"period": "7"})
        long_range = self.client.get(reverse("admin-dashboard"), {"period": "90"})

        self.assertEqual(short_range.status_code, 200)
        self.assertEqual(short_range.context["total_orders"], 0)
        self.assertEqual(len(short_range.context["chart_data"]), 7)
        self.assertEqual(long_range.context["total_orders"], 1)
        self.assertEqual(sum(point["orders"] for point in long_range.context["chart_data"]), 1)

    def test_order_search_sort_and_pagination_use_real_orders(self):
        base_time = timezone.now()
        created_orders = [
            CartOrder.objects.create(
                user=self.customer,
                full_name=f"مشتری مرتب‌سازی {index}",
                price=Decimal(str(index * 10000)),
                oid=f"ORD3000{index}",
                date=base_time - timedelta(minutes=index),
            )
            for index in range(1, 10)
        ]

        paginated = self.client.get(reverse("admin-dashboard"))
        sorted_orders = self.client.get(
            reverse("admin-dashboard"),
            {"sort": "amount", "direction": "asc"},
        )
        searched = self.client.get(
            reverse("admin-dashboard"),
            {"q": "مشتری مرتب‌سازی 4"},
        )

        self.assertEqual(paginated.context["recent_orders"].paginator.count, 9)
        self.assertTrue(paginated.context["recent_orders"].has_next())
        self.assertEqual(
            sorted_orders.context["recent_orders"][0]["order"].price,
            created_orders[0].price,
        )
        self.assertEqual(searched.context["filtered_order_count"], 1)
        self.assertEqual(
            searched.context["recent_orders"][0]["customer_name"],
            "مشتری مرتب‌سازی 4",
        )
